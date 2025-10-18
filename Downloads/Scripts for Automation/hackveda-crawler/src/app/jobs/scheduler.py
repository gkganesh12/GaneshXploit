"""
Job scheduler for HackVeda Crawler.
Handles scheduling and execution of crawling, email sending, and maintenance tasks.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore

from ..config import get_config
from ..database.db import get_db_manager
from ..crawler.google_serp import GoogleSERPCrawler
from ..email.gmail_api import GmailService
from ..email.smtp_client import EmailServiceManager


class BaseJob(ABC):
    """Base class for all scheduled jobs."""
    
    def __init__(self, name: str, config=None):
        self.name = name
        self.config = config or get_config()
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.last_run = None
        self.last_result = None
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the job and return result."""
        pass
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Run the job with error handling and logging."""
        start_time = datetime.utcnow()
        self.logger.info(f"Starting job: {self.name}")
        
        try:
            result = self.execute(**kwargs)
            
            self.last_run = start_time
            self.last_result = result
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(f"Job {self.name} completed successfully in {duration:.2f}s")
            
            result.update({
                'success': True,
                'start_time': start_time.isoformat(),
                'duration': duration
            })
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Job {self.name} failed: {e}"
            self.logger.error(error_msg)
            
            result = {
                'success': False,
                'error': str(e),
                'start_time': start_time.isoformat(),
                'duration': duration
            }
            
            self.last_run = start_time
            self.last_result = result
            
            return result


class CrawlJob(BaseJob):
    """Job for crawling keywords and storing results."""
    
    def __init__(self, config=None):
        super().__init__("crawl_job", config)
        self.crawler = GoogleSERPCrawler(config)
        self.db_manager = get_db_manager()
    
    def execute(self, keywords: List[str] = None, session_name: str = None, 
                max_results: int = None, **kwargs) -> Dict[str, Any]:
        """Execute crawling job."""
        
        # Use default keywords if none provided
        if not keywords:
            keywords = ["productivity tools", "project management software"]
        
        session_name = session_name or f"scheduled_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        max_results = max_results or self.config.crawler.max_results
        
        # Create crawl session
        with self.db_manager.get_session() as session:
            from ..database.models import CrawlSession, SearchResult
            from ..database.db import CrawlSessionRepository, SearchResultRepository
            
            # Create session
            crawl_repo = CrawlSessionRepository(session)
            result_repo = SearchResultRepository(session)
            
            crawl_session = crawl_repo.create(
                session_name=session_name,
                keywords=keywords,
                config={
                    'max_results': max_results,
                    'mode': self.config.crawler.mode,
                    'scheduled': True
                }
            )
            
            try:
                # Crawl keywords
                all_results = self.crawler.crawl_keywords(keywords, max_results)
                
                # Store results
                stored_results = []
                for result in all_results:
                    search_result = result_repo.create(
                        crawl_session_id=crawl_session.id,
                        title=result.title,
                        url=result.url,
                        snippet=result.snippet,
                        rank=result.rank,
                        domain=result.domain,
                        crawl_timestamp=result.crawl_timestamp,
                        response_time=result.response_time,
                        source_keyword=result.result_metadata.get('keyword', ''),
                        result_metadata=result.result_metadata
                    )
                    stored_results.append(search_result)
                
                # Update session
                crawl_repo.update_status(crawl_session.id, 'completed')
                crawl_session.total_results = len(stored_results)
                
                session.commit()
                
                return {
                    'session_id': crawl_session.id,
                    'session_name': session_name,
                    'keywords': keywords,
                    'total_results': len(stored_results),
                    'results_by_keyword': {
                        keyword: len([r for r in all_results if r.result_metadata.get('keyword') == keyword])
                        for keyword in keywords
                    }
                }
                
            except Exception as e:
                crawl_repo.update_status(crawl_session.id, 'failed', str(e))
                session.commit()
                raise


class EmailJob(BaseJob):
    """Job for sending emails."""
    
    def __init__(self, config=None):
        super().__init__("email_job", config)
        self.email_service = EmailServiceManager(config)
        self.db_manager = get_db_manager()
    
    def execute(self, campaign_id: int = None, template_name: str = None,
                recipients: List[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Execute email sending job."""
        
        if campaign_id:
            return self._send_campaign_emails(campaign_id)
        elif template_name and recipients:
            return self._send_bulk_emails(template_name, recipients)
        else:
            raise ValueError("Either campaign_id or (template_name + recipients) must be provided")
    
    def _send_campaign_emails(self, campaign_id: int) -> Dict[str, Any]:
        """Send emails for a specific campaign."""
        with self.db_manager.get_session() as session:
            from ..database.models import EmailCampaign, Contact, EmailLog
            from ..database.db import EmailLogRepository
            
            # Get campaign
            campaign = session.query(EmailCampaign).filter(
                EmailCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise ValueError(f"Campaign not found: {campaign_id}")
            
            # Get recipients (contacts with 'new' status)
            contacts = session.query(Contact).filter(
                Contact.email_status == 'new'
            ).all()
            
            if campaign.target_domains:
                # Filter by target domains
                contacts = [c for c in contacts if any(
                    domain in c.domain_info.domain for domain in campaign.target_domains
                )]
            
            if campaign.exclude_domains:
                # Exclude domains
                contacts = [c for c in contacts if not any(
                    domain in c.domain_info.domain for domain in campaign.exclude_domains
                )]
            
            # Update campaign status
            campaign.status = 'running'
            campaign.started_at = datetime.utcnow()
            campaign.total_recipients = len(contacts)
            
            email_repo = EmailLogRepository(session)
            results = []
            
            for contact in contacts:
                try:
                    # Create email log entry
                    email_log = email_repo.create(
                        campaign_id=campaign.id,
                        contact_id=contact.id,
                        to_address=contact.email,
                        from_address=campaign.from_address,
                        subject="[To be rendered]",  # Will be updated after sending
                        status='queued'
                    )
                    
                    # Prepare context
                    context = {
                        'recipient_name': contact.name or '',
                        'company': contact.company or contact.domain_info.domain,
                        'contact_email': contact.email
                    }
                    
                    # Send email
                    result = self.email_service.send_email(
                        to_address=contact.email,
                        subject=campaign.subject_template,  # Should be rendered with context
                        body="Email body",  # Should use template
                        from_name=campaign.from_name
                    )
                    
                    # Update log
                    if result['success']:
                        email_repo.update_status(
                            email_log.id, 'sent',
                            message_id=result.get('message_id'),
                            sent_at=datetime.utcnow()
                        )
                        campaign.emails_sent += 1
                        
                        # Update contact status
                        contact.email_status = 'contacted'
                        contact.last_contacted = datetime.utcnow()
                    else:
                        email_repo.update_status(
                            email_log.id, 'failed',
                            error_message=result.get('error')
                        )
                        campaign.emails_failed += 1
                    
                    results.append({
                        'contact_id': contact.id,
                        'email': contact.email,
                        'success': result['success'],
                        'error': result.get('error')
                    })
                    
                    # Rate limiting delay
                    if campaign.send_rate_limit:
                        time.sleep(60 / campaign.send_rate_limit)
                    
                except Exception as e:
                    self.logger.error(f"Failed to send email to {contact.email}: {e}")
                    campaign.emails_failed += 1
                    results.append({
                        'contact_id': contact.id,
                        'email': contact.email,
                        'success': False,
                        'error': str(e)
                    })
            
            # Update campaign status
            campaign.status = 'completed'
            campaign.completed_at = datetime.utcnow()
            
            session.commit()
            
            return {
                'campaign_id': campaign_id,
                'campaign_name': campaign.name,
                'total_recipients': campaign.total_recipients,
                'emails_sent': campaign.emails_sent,
                'emails_failed': campaign.emails_failed,
                'results': results
            }
    
    def _send_bulk_emails(self, template_name: str, recipients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send bulk emails using template."""
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                result = self.email_service.send_email(
                    to_address=recipient['email'],
                    subject=recipient.get('subject', f"Message from {self.config.email.gmail.from_name}"),
                    body=recipient.get('body', 'Default message body'),
                    html_body=recipient.get('html_body'),
                    from_name=recipient.get('from_name')
                )
                
                results.append({
                    'index': i,
                    'email': recipient['email'],
                    'success': result['success'],
                    'error': result.get('error')
                })
                
                # Rate limiting
                if i < len(recipients) - 1:
                    time.sleep(5)  # 5 second delay between emails
                
            except Exception as e:
                results.append({
                    'index': i,
                    'email': recipient.get('email', 'unknown'),
                    'success': False,
                    'error': str(e)
                })
        
        successful = len([r for r in results if r['success']])
        failed = len(results) - successful
        
        return {
            'template_name': template_name,
            'total_recipients': len(recipients),
            'emails_sent': successful,
            'emails_failed': failed,
            'results': results
        }


class CleanupJob(BaseJob):
    """Job for cleaning up old data."""
    
    def __init__(self, config=None):
        super().__init__("cleanup_job", config)
        self.db_manager = get_db_manager()
    
    def execute(self, retention_days: int = None, **kwargs) -> Dict[str, Any]:
        """Execute cleanup job."""
        retention_days = retention_days or self.config.app.data_retention_days
        
        try:
            self.db_manager.cleanup_old_data(retention_days)
            
            # Get updated stats
            stats = self.db_manager.get_stats()
            
            return {
                'retention_days': retention_days,
                'cleanup_completed': True,
                'current_stats': stats
            }
            
        except Exception as e:
            self.logger.error(f"Cleanup job failed: {e}")
            raise


class JobScheduler:
    """Main job scheduler for HackVeda Crawler."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Initialize jobs
        self.jobs = {
            'crawl': CrawlJob(config),
            'email': EmailJob(config),
            'cleanup': CleanupJob(config)
        }
        
        self._running = False
    
    def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            self.logger.info("Job scheduler started")
            
            # Add default scheduled jobs if configured
            self._add_default_jobs()
    
    def stop(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            self.logger.info("Job scheduler stopped")
    
    def _add_default_jobs(self):
        """Add default scheduled jobs from configuration."""
        scheduler_config = getattr(self.config, 'scheduler', {})
        
        if scheduler_config.get('enabled', False):
            jobs_config = scheduler_config.get('jobs', [])
            
            for job_config in jobs_config:
                try:
                    self.add_scheduled_job(
                        job_name=job_config['name'],
                        schedule=job_config['schedule'],
                        job_type=job_config.get('action', 'crawl'),
                        **job_config
                    )
                except Exception as e:
                    self.logger.error(f"Failed to add scheduled job {job_config.get('name')}: {e}")
    
    def add_scheduled_job(self, job_name: str, schedule: str, job_type: str = 'crawl', **kwargs):
        """Add a scheduled job."""
        if job_type not in self.jobs:
            raise ValueError(f"Unknown job type: {job_type}")
        
        job = self.jobs[job_type]
        
        # Parse schedule (cron format)
        try:
            # Convert cron schedule to CronTrigger
            cron_parts = schedule.split()
            if len(cron_parts) == 5:
                minute, hour, day, month, day_of_week = cron_parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )
            else:
                raise ValueError("Invalid cron format")
            
            # Add job to scheduler
            self.scheduler.add_job(
                func=job.run,
                trigger=trigger,
                id=job_name,
                name=job_name,
                kwargs=kwargs,
                replace_existing=True
            )
            
            self.logger.info(f"Added scheduled job: {job_name} ({schedule})")
            
        except Exception as e:
            self.logger.error(f"Failed to add scheduled job {job_name}: {e}")
            raise
    
    def add_interval_job(self, job_name: str, interval_seconds: int, job_type: str = 'crawl', **kwargs):
        """Add an interval-based job."""
        if job_type not in self.jobs:
            raise ValueError(f"Unknown job type: {job_type}")
        
        job = self.jobs[job_type]
        
        trigger = IntervalTrigger(seconds=interval_seconds)
        
        self.scheduler.add_job(
            func=job.run,
            trigger=trigger,
            id=job_name,
            name=job_name,
            kwargs=kwargs,
            replace_existing=True
        )
        
        self.logger.info(f"Added interval job: {job_name} (every {interval_seconds}s)")
    
    def run_job_now(self, job_type: str, **kwargs) -> Dict[str, Any]:
        """Run a job immediately."""
        if job_type not in self.jobs:
            raise ValueError(f"Unknown job type: {job_type}")
        
        job = self.jobs[job_type]
        return job.run(**kwargs)
    
    def remove_job(self, job_name: str):
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_name)
            self.logger.info(f"Removed job: {job_name}")
        except Exception as e:
            self.logger.error(f"Failed to remove job {job_name}: {e}")
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all scheduled jobs."""
        jobs = []
        
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jobs
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get scheduler and job status."""
        return {
            'scheduler_running': self._running,
            'total_jobs': len(self.scheduler.get_jobs()),
            'jobs': self.list_jobs(),
            'last_results': {
                name: {
                    'last_run': job.last_run.isoformat() if job.last_run else None,
                    'last_result': job.last_result
                }
                for name, job in self.jobs.items()
            }
        }
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
