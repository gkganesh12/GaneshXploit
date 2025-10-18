"""
Database connection and session management for HackVeda Crawler.
Handles SQLAlchemy engine creation, session management, and database operations.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from .models import Base, CrawlSession, SearchResult, Domain, Contact, EmailCampaign, EmailLog, AuditLog
from ..config import get_config


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self._engine = None
        self._session_factory = None
        
    def _create_engine(self):
        """Create SQLAlchemy engine with proper configuration."""
        if self._engine is not None:
            return self._engine
        
        db_url = self.config.database.url
        
        # Engine configuration
        engine_kwargs = {
            'echo': self.config.database.echo,
            'pool_pre_ping': True,  # Verify connections before use
        }
        
        # SQLite specific configuration
        if db_url.startswith('sqlite'):
            engine_kwargs.update({
                'poolclass': StaticPool,
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 30
                }
            })
        else:
            # PostgreSQL/MySQL configuration
            engine_kwargs.update({
                'pool_size': self.config.database.pool_size,
                'max_overflow': self.config.database.max_overflow,
                'pool_recycle': 3600,  # Recycle connections every hour
            })
        
        try:
            self._engine = create_engine(db_url, **engine_kwargs)
            self.logger.info(f"Database engine created successfully: {db_url.split('://')[0]}://...")
            return self._engine
        except Exception as e:
            self.logger.error(f"Failed to create database engine: {e}")
            raise
    
    def get_session_factory(self):
        """Get SQLAlchemy session factory."""
        if self._session_factory is None:
            engine = self._create_engine()
            self._session_factory = sessionmaker(bind=engine)
        return self._session_factory
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup."""
        session_factory = self.get_session_factory()
        session = session_factory()
        
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def init_database(self):
        """Initialize database tables."""
        try:
            engine = self._create_engine()
            Base.metadata.create_all(engine)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def drop_database(self):
        """Drop all database tables (use with caution)."""
        try:
            engine = self._create_engine()
            Base.metadata.drop_all(engine)
            self.logger.warning("All database tables dropped")
        except Exception as e:
            self.logger.error(f"Failed to drop database: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        
        try:
            with self.get_session() as session:
                stats['crawl_sessions'] = session.query(CrawlSession).count()
                stats['search_results'] = session.query(SearchResult).count()
                stats['domains'] = session.query(Domain).count()
                stats['contacts'] = session.query(Contact).count()
                stats['email_campaigns'] = session.query(EmailCampaign).count()
                stats['email_logs'] = session.query(EmailLog).count()
                stats['audit_logs'] = session.query(AuditLog).count()
                
                # Recent activity
                recent_threshold = datetime.utcnow() - timedelta(days=7)
                stats['recent_crawl_sessions'] = session.query(CrawlSession).filter(
                    CrawlSession.start_time >= recent_threshold
                ).count()
                
                stats['recent_emails_sent'] = session.query(EmailLog).filter(
                    EmailLog.sent_at >= recent_threshold
                ).count()
                
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def cleanup_old_data(self, retention_days: int = None):
        """Clean up old data based on retention policy."""
        retention_days = retention_days or self.config.app.data_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        try:
            with self.get_session() as session:
                # Clean up old crawl sessions and their results
                old_sessions = session.query(CrawlSession).filter(
                    CrawlSession.start_time < cutoff_date
                ).all()
                
                deleted_sessions = 0
                deleted_results = 0
                
                for session_obj in old_sessions:
                    deleted_results += len(session_obj.search_results)
                    session.delete(session_obj)
                    deleted_sessions += 1
                
                # Clean up old audit logs (keep longer)
                audit_cutoff = datetime.utcnow() - timedelta(days=retention_days * 3)
                deleted_audit = session.query(AuditLog).filter(
                    AuditLog.timestamp < audit_cutoff
                ).delete()
                
                session.commit()
                
                self.logger.info(f"Cleaned up old data: {deleted_sessions} sessions, "
                               f"{deleted_results} results, {deleted_audit} audit logs")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            raise


# Global database manager instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session():
    """Get database session (for dependency injection)."""
    return get_db_manager().get_session()


# Repository classes for data access

class CrawlSessionRepository:
    """Repository for crawl session operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, session_name: str, keywords: List[str], config: Dict[str, Any] = None) -> CrawlSession:
        """Create a new crawl session."""
        crawl_session = CrawlSession(
            session_name=session_name,
            keywords=keywords,
            config=config or {}
        )
        self.session.add(crawl_session)
        self.session.flush()  # Get ID without committing
        return crawl_session
    
    def get_by_id(self, session_id: int) -> Optional[CrawlSession]:
        """Get crawl session by ID."""
        return self.session.query(CrawlSession).filter(
            CrawlSession.id == session_id
        ).first()
    
    def get_active_sessions(self) -> List[CrawlSession]:
        """Get all active crawl sessions."""
        return self.session.query(CrawlSession).filter(
            CrawlSession.status == 'running'
        ).all()
    
    def update_status(self, session_id: int, status: str, error_message: str = None):
        """Update crawl session status."""
        crawl_session = self.get_by_id(session_id)
        if crawl_session:
            crawl_session.status = status
            if error_message:
                crawl_session.error_message = error_message
            if status in ['completed', 'failed']:
                crawl_session.end_time = datetime.utcnow()


class SearchResultRepository:
    """Repository for search result operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, crawl_session_id: int, **kwargs) -> SearchResult:
        """Create a new search result."""
        search_result = SearchResult(
            crawl_session_id=crawl_session_id,
            **kwargs
        )
        self.session.add(search_result)
        return search_result
    
    def bulk_create(self, results: List[Dict[str, Any]]) -> List[SearchResult]:
        """Create multiple search results efficiently."""
        search_results = [SearchResult(**result_data) for result_data in results]
        self.session.add_all(search_results)
        return search_results
    
    def get_by_domain(self, domain: str) -> List[SearchResult]:
        """Get all results for a specific domain."""
        return self.session.query(SearchResult).filter(
            SearchResult.domain == domain
        ).all()
    
    def get_by_keyword(self, keyword: str) -> List[SearchResult]:
        """Get all results for a specific keyword."""
        return self.session.query(SearchResult).filter(
            SearchResult.source_keyword == keyword
        ).all()
    
    def get_high_quality_results(self, min_quality_score: float = 0.7) -> List[SearchResult]:
        """Get high-quality search results."""
        return self.session.query(SearchResult).filter(
            SearchResult.quality_score >= min_quality_score
        ).order_by(SearchResult.quality_score.desc()).all()


class DomainRepository:
    """Repository for domain operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_or_create(self, domain_name: str) -> Domain:
        """Get existing domain or create new one."""
        domain = self.session.query(Domain).filter(
            Domain.domain == domain_name
        ).first()
        
        if not domain:
            domain = Domain(domain=domain_name)
            self.session.add(domain)
            self.session.flush()
        else:
            # Update last crawled time
            domain.last_crawled = datetime.utcnow()
            domain.crawl_count += 1
        
        return domain
    
    def update_contact_info(self, domain_id: int, contact_emails: List[str] = None,
                          contact_pages: List[str] = None, social_links: List[str] = None):
        """Update domain contact information."""
        domain = self.session.query(Domain).filter(Domain.id == domain_id).first()
        if domain:
            if contact_emails:
                domain.contact_emails = contact_emails
                domain.has_contact_info = True
            if contact_pages:
                domain.contact_pages = contact_pages
            if social_links:
                domain.social_links = social_links


class ContactRepository:
    """Repository for contact operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, domain_id: int, email: str, **kwargs) -> Contact:
        """Create a new contact."""
        # Check if contact already exists
        existing = self.session.query(Contact).filter(
            Contact.domain_id == domain_id,
            Contact.email == email
        ).first()
        
        if existing:
            return existing
        
        contact = Contact(
            domain_id=domain_id,
            email=email,
            **kwargs
        )
        self.session.add(contact)
        return contact
    
    def get_by_status(self, status: str) -> List[Contact]:
        """Get contacts by email status."""
        return self.session.query(Contact).filter(
            Contact.email_status == status
        ).all()
    
    def update_status(self, contact_id: int, status: str):
        """Update contact email status."""
        contact = self.session.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            contact.email_status = status
            contact.updated_at = datetime.utcnow()
            if status == 'contacted':
                contact.last_contacted = datetime.utcnow()


class EmailLogRepository:
    """Repository for email log operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, **kwargs) -> EmailLog:
        """Create a new email log entry."""
        email_log = EmailLog(**kwargs)
        self.session.add(email_log)
        return email_log
    
    def update_status(self, log_id: int, status: str, **kwargs):
        """Update email log status."""
        email_log = self.session.query(EmailLog).filter(EmailLog.id == log_id).first()
        if email_log:
            email_log.status = status
            email_log.updated_at = datetime.utcnow()
            
            # Update timestamp fields based on status
            if status == 'sent' and 'sent_at' not in kwargs:
                kwargs['sent_at'] = datetime.utcnow()
            elif status == 'delivered' and 'delivered_at' not in kwargs:
                kwargs['delivered_at'] = datetime.utcnow()
            
            for key, value in kwargs.items():
                setattr(email_log, key, value)
    
    def get_campaign_stats(self, campaign_id: int) -> Dict[str, int]:
        """Get email statistics for a campaign."""
        logs = self.session.query(EmailLog).filter(
            EmailLog.campaign_id == campaign_id
        ).all()
        
        stats = {
            'total': len(logs),
            'queued': 0,
            'sent': 0,
            'delivered': 0,
            'failed': 0,
            'bounced': 0
        }
        
        for log in logs:
            stats[log.status] = stats.get(log.status, 0) + 1
        
        return stats
    
    def get_repository(self, repo_type: str):
        """Get repository instance for database operations."""
        from .repositories import (
            CrawlSessionRepository, SearchResultRepository, 
            DomainRepository, ContactRepository, 
            EmailCampaignRepository, EmailLogRepository
        )
        
        repo_map = {
            'crawl_session': CrawlSessionRepository,
            'search_result': SearchResultRepository,
            'domain': DomainRepository,
            'contact': ContactRepository,
            'email_campaign': EmailCampaignRepository,
            'email_log': EmailLogRepository
        }
        
        if repo_type not in repo_map:
            raise ValueError(f"Unknown repository type: {repo_type}")
        
        # Return repository class (will be instantiated with session)
        return repo_map[repo_type]
