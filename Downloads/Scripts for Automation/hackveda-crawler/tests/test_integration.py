"""
Integration tests for HackVeda Crawler.
Tests end-to-end functionality and component integration.
"""

import pytest
import responses
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.crawler.google_serp import GoogleSERPCrawler
from app.enrichment.contact_extractor import ContactExtractor
from app.email.gmail_api import GmailService
from app.database.db import DatabaseManager
from app.jobs.scheduler import JobScheduler, CrawlJob, EmailJob


class TestCrawlerIntegration:
    """Test crawler integration with database and enrichment."""
    
    @responses.activate
    @patch('app.database.db.DatabaseManager')
    def test_crawl_and_store_workflow(self, mock_db_manager, test_config, mock_google_search_response):
        """Test complete crawl and store workflow."""
        # Mock Google search response
        responses.add(
            responses.GET,
            'https://www.google.com/search',
            html=mock_google_search_response,
            status=200
        )
        
        # Mock database operations
        mock_session = Mock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session
        
        # Initialize crawler
        crawler = GoogleSERPCrawler(test_config)
        
        # Crawl keywords
        keywords = ['test query']
        results = crawler.crawl_keywords(keywords, max_results=2)
        
        # Verify results
        assert len(results) == 2
        assert all(result.metadata.get('keyword') == 'test query' for result in results)
        
        # Simulate storing in database
        from app.database.db import CrawlSessionRepository, SearchResultRepository
        
        crawl_repo = CrawlSessionRepository(mock_session)
        result_repo = SearchResultRepository(mock_session)
        
        # Create crawl session
        crawl_session = crawl_repo.create(
            session_name='integration_test',
            keywords=keywords,
            config={'max_results': 2}
        )
        
        # Store results
        for result in results:
            search_result = result_repo.create(
                crawl_session_id=crawl_session.id,
                title=result.title,
                url=result.url,
                snippet=result.snippet,
                rank=result.rank,
                domain=result.domain,
                source_keyword=result.metadata.get('keyword', '')
            )
        
        # Verify database operations were called
        assert mock_session.add.call_count >= len(results) + 1  # results + session
    
    @responses.activate
    @patch('app.enrichment.contact_extractor.PageFetcher')
    def test_crawl_and_enrich_workflow(self, mock_page_fetcher_class, test_config, 
                                     mock_google_search_response, sample_html_content):
        """Test crawl and contact enrichment workflow."""
        # Mock Google search response
        responses.add(
            responses.GET,
            'https://www.google.com/search',
            html=mock_google_search_response,
            status=200
        )
        
        # Mock page fetcher for contact extraction
        mock_page_fetcher = Mock()
        from app.crawler.page_fetcher import PageContent
        mock_page_content = PageContent(
            url='https://example.com',
            title='Example Site',
            content='Contact us at info@example.com',
            html=sample_html_content,
            status_code=200,
            response_time=1.0,
            headers={'content-type': 'text/html'},
            fetch_timestamp=datetime.now()
        )
        mock_page_fetcher.fetch_page.return_value = mock_page_content
        mock_page_fetcher_class.return_value = mock_page_fetcher
        
        # Initialize components
        crawler = GoogleSERPCrawler(test_config)
        contact_extractor = ContactExtractor(test_config)
        
        # Crawl keywords
        results = crawler.crawl_keywords(['test query'], max_results=2)
        
        # Extract contacts from domains
        domains = list(set(result.domain for result in results))
        
        for domain in domains:
            contact_info = contact_extractor.extract_contacts_from_domain(domain, max_pages=1)
            
            # Verify contact extraction
            assert contact_info is not None
            assert contact_info.extraction_method == 'domain_crawl'
            
            # Should have found some contact information
            if domain == 'example.com':
                assert len(contact_info.emails) > 0 or len(contact_info.social_links) > 0


class TestEmailIntegration:
    """Test email integration with database and templates."""
    
    @patch('app.email.gmail_api.build')
    @patch('app.email.gmail_api.GmailAuthManager')
    @patch('app.database.db.DatabaseManager')
    def test_email_campaign_workflow(self, mock_db_manager, mock_auth_manager, mock_build, 
                                   test_config, sample_contacts):
        """Test complete email campaign workflow."""
        # Mock Gmail service
        mock_creds = Mock()
        mock_auth_manager.return_value.get_credentials.return_value = mock_creds
        
        mock_gmail_service = Mock()
        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'test_message_id',
            'threadId': 'test_thread_id'
        }
        mock_build.return_value = mock_gmail_service
        
        # Mock database operations
        mock_session = Mock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock campaign and contacts
        from app.database.models import EmailCampaign, Contact
        mock_campaign = EmailCampaign(
            id=1,
            name='Test Campaign',
            template_name='outreach',
            subject_template='Test Subject',
            from_address='test@example.com',
            status='running'
        )
        
        mock_contacts = [
            Contact(
                id=1,
                email='contact1@example.com',
                name='John Doe',
                company='Example Corp'
            ),
            Contact(
                id=2,
                email='contact2@testsite.org',
                name='Jane Smith',
                company='Test Site'
            )
        ]
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_campaign
        mock_session.query.return_value.filter.return_value.all.return_value = mock_contacts
        
        # Initialize email job
        email_job = EmailJob(test_config)
        
        # Execute email campaign
        result = email_job.execute(campaign_id=1)
        
        # Verify results
        assert result['campaign_id'] == 1
        assert result['total_recipients'] == len(mock_contacts)
        assert 'results' in result
        
        # Verify Gmail API was called for each contact
        assert mock_gmail_service.users().messages().send().execute.call_count == len(mock_contacts)
    
    @patch('app.email.templates.EmailTemplateManager')
    @patch('app.email.gmail_api.build')
    @patch('app.email.gmail_api.GmailAuthManager')
    def test_templated_email_workflow(self, mock_auth_manager, mock_build, 
                                    mock_template_manager, test_config):
        """Test templated email sending workflow."""
        # Mock Gmail service
        mock_creds = Mock()
        mock_auth_manager.return_value.get_credentials.return_value = mock_creds
        
        mock_gmail_service = Mock()
        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'test_message_id'
        }
        mock_build.return_value = mock_gmail_service
        
        # Mock template rendering
        mock_template_manager.return_value.render_template.return_value = {
            'subject': 'Hello John Doe!',
            'text_body': 'Hello John Doe! Welcome to our service.',
            'html_body': '<h1>Hello John Doe!</h1><p>Welcome to our service.</p>'
        }
        
        # Initialize Gmail service
        gmail_service = GmailService(test_config)
        
        # Send templated email
        result = gmail_service.send_templated_email(
            to_address='john@example.com',
            template_name='welcome',
            context={'recipient_name': 'John Doe'}
        )
        
        # Verify results
        assert result['success'] is True
        assert result['message_id'] == 'test_message_id'
        
        # Verify template was rendered
        mock_template_manager.return_value.render_template.assert_called_once_with(
            'welcome',
            {'recipient_name': 'John Doe'}
        )


class TestJobSchedulerIntegration:
    """Test job scheduler integration."""
    
    @responses.activate
    @patch('app.database.db.DatabaseManager')
    def test_scheduled_crawl_job(self, mock_db_manager, test_config, mock_google_search_response):
        """Test scheduled crawl job execution."""
        # Mock Google search response
        responses.add(
            responses.GET,
            'https://www.google.com/search',
            html=mock_google_search_response,
            status=200
        )
        
        # Mock database operations
        mock_session = Mock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session
        
        # Initialize job scheduler
        scheduler = JobScheduler(test_config)
        
        # Run crawl job immediately
        result = scheduler.run_job_now(
            job_type='crawl',
            keywords=['test query'],
            session_name='scheduled_test',
            max_results=2
        )
        
        # Verify job execution
        assert result['success'] is True
        assert 'session_id' in result
        assert result['keywords'] == ['test query']
        assert result['total_results'] >= 0
    
    @patch('app.email.gmail_api.build')
    @patch('app.email.gmail_api.GmailAuthManager')
    @patch('app.database.db.DatabaseManager')
    def test_scheduled_email_job(self, mock_db_manager, mock_auth_manager, mock_build, test_config):
        """Test scheduled email job execution."""
        # Mock Gmail service
        mock_creds = Mock()
        mock_auth_manager.return_value.get_credentials.return_value = mock_creds
        
        mock_gmail_service = Mock()
        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'test_message_id'
        }
        mock_build.return_value = mock_gmail_service
        
        # Mock database operations
        mock_session = Mock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session
        
        # Initialize job scheduler
        scheduler = JobScheduler(test_config)
        
        # Prepare test recipients
        recipients = [
            {
                'email': 'test1@example.com',
                'subject': 'Test Subject 1',
                'body': 'Test body 1'
            },
            {
                'email': 'test2@example.com',
                'subject': 'Test Subject 2',
                'body': 'Test body 2'
            }
        ]
        
        # Run email job immediately
        result = scheduler.run_job_now(
            job_type='email',
            template_name='test_template',
            recipients=recipients
        )
        
        # Verify job execution
        assert result['success'] is True
        assert result['total_recipients'] == len(recipients)
        assert result['emails_sent'] >= 0
    
    def test_job_scheduler_lifecycle(self, test_config):
        """Test job scheduler start/stop lifecycle."""
        scheduler = JobScheduler(test_config)
        
        # Initially not running
        assert scheduler.is_running() is False
        
        # Start scheduler
        scheduler.start()
        assert scheduler.is_running() is True
        
        # Add a test job
        scheduler.add_interval_job(
            job_name='test_job',
            interval_seconds=3600,  # 1 hour
            job_type='crawl',
            keywords=['test']
        )
        
        # Check job was added
        jobs = scheduler.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]['id'] == 'test_job'
        
        # Remove job
        scheduler.remove_job('test_job')
        jobs = scheduler.list_jobs()
        assert len(jobs) == 0
        
        # Stop scheduler
        scheduler.stop()
        assert scheduler.is_running() is False


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @responses.activate
    @patch('app.email.gmail_api.build')
    @patch('app.email.gmail_api.GmailAuthManager')
    @patch('app.enrichment.contact_extractor.PageFetcher')
    @patch('app.database.db.DatabaseManager')
    def test_complete_marketing_workflow(self, mock_db_manager, mock_page_fetcher_class,
                                       mock_auth_manager, mock_build, test_config,
                                       mock_google_search_response, sample_html_content):
        """Test complete marketing workflow: crawl -> enrich -> email."""
        
        # Mock Google search response
        responses.add(
            responses.GET,
            'https://www.google.com/search',
            html=mock_google_search_response,
            status=200
        )
        
        # Mock page fetcher for contact extraction
        mock_page_fetcher = Mock()
        from app.crawler.page_fetcher import PageContent
        mock_page_content = PageContent(
            url='https://example.com/contact',
            title='Contact Us - Example',
            content='Contact us at info@example.com or sales@example.com',
            html=sample_html_content,
            status_code=200,
            response_time=1.0,
            headers={'content-type': 'text/html'},
            fetch_timestamp=datetime.now()
        )
        mock_page_fetcher.fetch_page.return_value = mock_page_content
        mock_page_fetcher_class.return_value = mock_page_fetcher
        
        # Mock Gmail service
        mock_creds = Mock()
        mock_auth_manager.return_value.get_credentials.return_value = mock_creds
        
        mock_gmail_service = Mock()
        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'test_message_id'
        }
        mock_build.return_value = mock_gmail_service
        
        # Mock database operations
        mock_session = Mock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session
        
        # Step 1: Crawl for leads
        crawler = GoogleSERPCrawler(test_config)
        crawl_results = crawler.crawl_keywords(['productivity tools'], max_results=2)
        
        assert len(crawl_results) == 2
        
        # Step 2: Extract contacts from domains
        contact_extractor = ContactExtractor(test_config)
        all_contacts = []
        
        for result in crawl_results:
            contact_info = contact_extractor.extract_contacts_from_domain(
                result.domain, max_pages=1
            )
            
            if contact_info.emails:
                for email in contact_info.emails:
                    all_contacts.append({
                        'email': email,
                        'domain': result.domain,
                        'source_url': result.url,
                        'confidence': contact_info.confidence_score
                    })
        
        # Should have found some contacts
        assert len(all_contacts) > 0
        
        # Step 3: Send outreach emails
        gmail_service = GmailService(test_config)
        
        email_results = []
        for contact in all_contacts[:2]:  # Limit to 2 for testing
            result = gmail_service.send_email(
                to_address=contact['email'],
                subject=f"Partnership Opportunity with {contact['domain']}",
                body=f"Hello! I found your contact information on {contact['source_url']} and would like to discuss a partnership opportunity."
            )
            email_results.append(result)
        
        # Verify emails were sent
        assert len(email_results) == min(2, len(all_contacts))
        assert all(result['success'] for result in email_results)
        
        # Verify Gmail API was called
        assert mock_gmail_service.users().messages().send().execute.call_count == len(email_results)
    
    def test_error_handling_workflow(self, test_config):
        """Test error handling in integrated workflow."""
        # Test with invalid configuration
        invalid_config = test_config
        invalid_config.crawler.max_retries = 0
        invalid_config.crawler.timeout = 1  # Very short timeout
        
        crawler = GoogleSERPCrawler(invalid_config)
        
        # Should handle errors gracefully
        results = crawler.crawl_keywords(['test query'], max_results=1)
        
        # May return empty results due to errors, but should not crash
        assert isinstance(results, list)
    
    @patch('app.database.db.DatabaseManager')
    def test_database_integration_workflow(self, mock_db_manager, test_config):
        """Test database integration workflow."""
        # Mock database operations
        mock_session = Mock()
        mock_db_manager.return_value.get_session.return_value.__enter__.return_value = mock_session
        mock_db_manager.return_value.health_check.return_value = True
        mock_db_manager.return_value.get_stats.return_value = {
            'crawl_sessions': 5,
            'search_results': 50,
            'domains': 25,
            'contacts': 15
        }
        
        # Test database health check
        db_manager = mock_db_manager.return_value
        assert db_manager.health_check() is True
        
        # Test getting stats
        stats = db_manager.get_stats()
        assert stats['crawl_sessions'] == 5
        assert stats['search_results'] == 50
        
        # Test session management
        with db_manager.get_session() as session:
            assert session == mock_session
        
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
