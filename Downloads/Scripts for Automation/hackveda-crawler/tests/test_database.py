"""
Tests for database module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.database.models import (
    CrawlSession, SearchResult, Domain, Contact, EmailCampaign, EmailLog, AuditLog,
    create_crawl_session, create_search_result, create_email_campaign, log_audit_event
)
from app.database.db import (
    DatabaseManager, CrawlSessionRepository, SearchResultRepository,
    DomainRepository, ContactRepository, EmailLogRepository
)


class TestDatabaseModels:
    """Test database model functionality."""
    
    def test_crawl_session_creation(self):
        """Test CrawlSession model creation."""
        session = CrawlSession(
            session_name='test_session',
            keywords=['test', 'keyword'],
            status='running',
            config={'max_results': 10}
        )
        
        assert session.session_name == 'test_session'
        assert session.keywords == ['test', 'keyword']
        assert session.status == 'running'
        assert session.config == {'max_results': 10}
        assert session.total_results == 0  # default value
    
    def test_search_result_creation(self):
        """Test SearchResult model creation."""
        result = SearchResult(
            crawl_session_id=1,
            title='Test Result',
            url='https://example.com',
            snippet='Test snippet',
            rank=1,
            domain='example.com',
            source_keyword='test'
        )
        
        assert result.title == 'Test Result'
        assert result.url == 'https://example.com'
        assert result.rank == 1
        assert result.domain == 'example.com'
        assert result.relevance_score == 0.0  # default value
    
    def test_search_result_url_validation(self):
        """Test SearchResult URL validation."""
        # Valid URL
        result = SearchResult(
            crawl_session_id=1,
            title='Test',
            url='https://example.com',
            snippet='Test',
            rank=1,
            domain='example.com'
        )
        
        # This should not raise an exception
        validated_url = result.__class__.url.property.columns[0].type.python_type
        
        # Invalid URL should raise ValueError when validated
        with pytest.raises(ValueError):
            result = SearchResult(
                crawl_session_id=1,
                title='Test',
                url='invalid-url',
                snippet='Test',
                rank=1,
                domain='example.com'
            )
            # Trigger validation
            result.__class__.url.property.columns[0].type._validate_url('url', 'invalid-url')
    
    def test_domain_creation(self):
        """Test Domain model creation."""
        domain = Domain(
            domain='example.com',
            tld='com',
            is_subdomain=False,
            main_domain='example.com',
            quality_rating='medium'
        )
        
        assert domain.domain == 'example.com'
        assert domain.tld == 'com'
        assert domain.is_subdomain is False
        assert domain.quality_rating == 'medium'
        assert domain.crawl_count == 1  # default value
    
    def test_contact_creation(self):
        """Test Contact model creation."""
        contact = Contact(
            domain_id=1,
            email='test@example.com',
            name='John Doe',
            company='Example Corp',
            email_status='new'
        )
        
        assert contact.email == 'test@example.com'
        assert contact.name == 'John Doe'
        assert contact.company == 'Example Corp'
        assert contact.email_status == 'new'
        assert contact.confidence_score == 0.0  # default value
    
    def test_contact_email_validation(self):
        """Test Contact email validation."""
        # Valid email
        contact = Contact(
            domain_id=1,
            email='valid@example.com'
        )
        
        # Invalid email should raise ValueError when validated
        with pytest.raises(ValueError):
            contact = Contact(
                domain_id=1,
                email='invalid-email'
            )
            # Trigger validation
            contact.__class__.email.property.columns[0].type._validate_email('email', 'invalid-email')
    
    def test_email_campaign_creation(self):
        """Test EmailCampaign model creation."""
        campaign = EmailCampaign(
            name='Test Campaign',
            description='Test description',
            template_name='test_template',
            subject_template='Test Subject',
            from_address='sender@example.com',
            status='draft'
        )
        
        assert campaign.name == 'Test Campaign'
        assert campaign.template_name == 'test_template'
        assert campaign.status == 'draft'
        assert campaign.total_recipients == 0  # default value
        assert campaign.send_rate_limit == 10  # default value
    
    def test_email_log_creation(self):
        """Test EmailLog model creation."""
        log = EmailLog(
            campaign_id=1,
            contact_id=1,
            to_address='recipient@example.com',
            from_address='sender@example.com',
            subject='Test Subject',
            status='queued'
        )
        
        assert log.to_address == 'recipient@example.com'
        assert log.from_address == 'sender@example.com'
        assert log.status == 'queued'
        assert log.retry_count == 0  # default value
    
    def test_audit_log_creation(self):
        """Test AuditLog model creation."""
        log = AuditLog(
            action='crawl',
            entity_type='search_result',
            entity_id=1,
            details={'keyword': 'test'},
            success=True
        )
        
        assert log.action == 'crawl'
        assert log.entity_type == 'search_result'
        assert log.entity_id == 1
        assert log.details == {'keyword': 'test'}
        assert log.success is True
    
    def test_utility_functions(self):
        """Test utility functions for model creation."""
        # Test create_crawl_session
        session = create_crawl_session(
            session_name='test',
            keywords=['test'],
            config={'test': True}
        )
        assert isinstance(session, CrawlSession)
        assert session.session_name == 'test'
        
        # Test create_search_result
        result = create_search_result(
            crawl_session_id=1,
            title='Test',
            url='https://example.com',
            snippet='Test',
            rank=1,
            domain='example.com'
        )
        assert isinstance(result, SearchResult)
        assert result.crawl_session_id == 1
        
        # Test create_email_campaign
        campaign = create_email_campaign(
            name='Test Campaign',
            template_name='test',
            subject_template='Test Subject',
            from_address='test@example.com'
        )
        assert isinstance(campaign, EmailCampaign)
        assert campaign.name == 'Test Campaign'
        
        # Test log_audit_event
        audit = log_audit_event(
            action='test_action',
            entity_type='test_entity',
            entity_id=1,
            success=True
        )
        assert isinstance(audit, AuditLog)
        assert audit.action == 'test_action'


class TestDatabaseManager:
    """Test DatabaseManager functionality."""
    
    def test_database_manager_initialization(self, test_config):
        """Test DatabaseManager initialization."""
        db_manager = DatabaseManager(test_config)
        
        assert db_manager.config == test_config
        assert db_manager._engine is None  # Not created yet
        assert db_manager._session_factory is None
    
    @patch('app.database.db.create_engine')
    def test_create_engine_sqlite(self, mock_create_engine, test_config):
        """Test engine creation for SQLite."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        db_manager = DatabaseManager(test_config)
        engine = db_manager._create_engine()
        
        assert engine == mock_engine
        mock_create_engine.assert_called_once()
        
        # Check SQLite-specific configuration
        call_args = mock_create_engine.call_args
        assert 'poolclass' in call_args[1]
        assert 'connect_args' in call_args[1]
    
    @patch('app.database.db.create_engine')
    def test_create_engine_postgresql(self, mock_create_engine, test_config):
        """Test engine creation for PostgreSQL."""
        # Change config to PostgreSQL
        test_config.database.url = 'postgresql://user:pass@localhost/db'
        
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        db_manager = DatabaseManager(test_config)
        engine = db_manager._create_engine()
        
        assert engine == mock_engine
        
        # Check PostgreSQL-specific configuration
        call_args = mock_create_engine.call_args
        assert 'pool_size' in call_args[1]
        assert 'max_overflow' in call_args[1]
    
    @patch('app.database.db.sessionmaker')
    @patch('app.database.db.create_engine')
    def test_get_session_factory(self, mock_create_engine, mock_sessionmaker, test_config):
        """Test session factory creation."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_session_factory = Mock()
        mock_sessionmaker.return_value = mock_session_factory
        
        db_manager = DatabaseManager(test_config)
        session_factory = db_manager.get_session_factory()
        
        assert session_factory == mock_session_factory
        mock_sessionmaker.assert_called_once_with(bind=mock_engine)
    
    @patch('app.database.db.sessionmaker')
    @patch('app.database.db.create_engine')
    def test_get_session_context_manager(self, mock_create_engine, mock_sessionmaker, test_config):
        """Test session context manager."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_sessionmaker.return_value = mock_session_factory
        
        db_manager = DatabaseManager(test_config)
        
        # Test successful session usage
        with db_manager.get_session() as session:
            assert session == mock_session
        
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
    
    @patch('app.database.db.sessionmaker')
    @patch('app.database.db.create_engine')
    def test_get_session_with_exception(self, mock_create_engine, mock_sessionmaker, test_config):
        """Test session context manager with exception."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_sessionmaker.return_value = mock_session_factory
        
        db_manager = DatabaseManager(test_config)
        
        # Test session with exception
        with pytest.raises(ValueError):
            with db_manager.get_session() as session:
                raise ValueError("Test exception")
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
    
    @patch('app.database.db.Base')
    @patch('app.database.db.create_engine')
    def test_init_database(self, mock_create_engine, mock_base, test_config):
        """Test database initialization."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        db_manager = DatabaseManager(test_config)
        db_manager.init_database()
        
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)
    
    @patch('app.database.db.text')
    @patch('app.database.db.sessionmaker')
    @patch('app.database.db.create_engine')
    def test_health_check_success(self, mock_create_engine, mock_sessionmaker, mock_text, test_config):
        """Test successful health check."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_sessionmaker.return_value = mock_session_factory
        
        db_manager = DatabaseManager(test_config)
        result = db_manager.health_check()
        
        assert result is True
        mock_session.execute.assert_called_once()
    
    @patch('app.database.db.sessionmaker')
    @patch('app.database.db.create_engine')
    def test_health_check_failure(self, mock_create_engine, mock_sessionmaker, test_config):
        """Test failed health check."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database error")
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_sessionmaker.return_value = mock_session_factory
        
        db_manager = DatabaseManager(test_config)
        result = db_manager.health_check()
        
        assert result is False


class TestRepositories:
    """Test repository classes."""
    
    def test_crawl_session_repository_create(self):
        """Test CrawlSessionRepository create method."""
        mock_session = Mock()
        repo = CrawlSessionRepository(mock_session)
        
        crawl_session = repo.create(
            session_name='test_session',
            keywords=['test'],
            config={'max_results': 10}
        )
        
        assert isinstance(crawl_session, CrawlSession)
        assert crawl_session.session_name == 'test_session'
        assert crawl_session.keywords == ['test']
        
        mock_session.add.assert_called_once_with(crawl_session)
        mock_session.flush.assert_called_once()
    
    def test_crawl_session_repository_get_by_id(self):
        """Test CrawlSessionRepository get_by_id method."""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_crawl_session = Mock()
        mock_filter.first.return_value = mock_crawl_session
        
        repo = CrawlSessionRepository(mock_session)
        result = repo.get_by_id(1)
        
        assert result == mock_crawl_session
        mock_session.query.assert_called_once_with(CrawlSession)
    
    def test_crawl_session_repository_update_status(self):
        """Test CrawlSessionRepository update_status method."""
        mock_session = Mock()
        mock_crawl_session = Mock()
        
        repo = CrawlSessionRepository(mock_session)
        repo.get_by_id = Mock(return_value=mock_crawl_session)
        
        repo.update_status(1, 'completed', 'Success')
        
        assert mock_crawl_session.status == 'completed'
        assert mock_crawl_session.error_message == 'Success'
        assert mock_crawl_session.end_time is not None
    
    def test_search_result_repository_create(self):
        """Test SearchResultRepository create method."""
        mock_session = Mock()
        repo = SearchResultRepository(mock_session)
        
        result = repo.create(
            crawl_session_id=1,
            title='Test Result',
            url='https://example.com',
            snippet='Test snippet',
            rank=1,
            domain='example.com'
        )
        
        assert isinstance(result, SearchResult)
        assert result.crawl_session_id == 1
        assert result.title == 'Test Result'
        
        mock_session.add.assert_called_once_with(result)
    
    def test_search_result_repository_bulk_create(self):
        """Test SearchResultRepository bulk_create method."""
        mock_session = Mock()
        repo = SearchResultRepository(mock_session)
        
        results_data = [
            {
                'crawl_session_id': 1,
                'title': 'Result 1',
                'url': 'https://example1.com',
                'snippet': 'Snippet 1',
                'rank': 1,
                'domain': 'example1.com'
            },
            {
                'crawl_session_id': 1,
                'title': 'Result 2',
                'url': 'https://example2.com',
                'snippet': 'Snippet 2',
                'rank': 2,
                'domain': 'example2.com'
            }
        ]
        
        results = repo.bulk_create(results_data)
        
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        mock_session.add_all.assert_called_once()
    
    def test_domain_repository_get_or_create_new(self):
        """Test DomainRepository get_or_create for new domain."""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Domain doesn't exist
        
        repo = DomainRepository(mock_session)
        domain = repo.get_or_create('example.com')
        
        assert isinstance(domain, Domain)
        assert domain.domain == 'example.com'
        mock_session.add.assert_called_once_with(domain)
        mock_session.flush.assert_called_once()
    
    def test_domain_repository_get_or_create_existing(self):
        """Test DomainRepository get_or_create for existing domain."""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_existing_domain = Mock()
        mock_existing_domain.crawl_count = 5
        mock_filter.first.return_value = mock_existing_domain
        
        repo = DomainRepository(mock_session)
        domain = repo.get_or_create('example.com')
        
        assert domain == mock_existing_domain
        assert domain.crawl_count == 6  # Should be incremented
        assert domain.last_crawled is not None
    
    def test_contact_repository_create_new(self):
        """Test ContactRepository create for new contact."""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Contact doesn't exist
        
        repo = ContactRepository(mock_session)
        contact = repo.create(
            domain_id=1,
            email='test@example.com',
            name='John Doe'
        )
        
        assert isinstance(contact, Contact)
        assert contact.domain_id == 1
        assert contact.email == 'test@example.com'
        assert contact.name == 'John Doe'
        mock_session.add.assert_called_once_with(contact)
    
    def test_contact_repository_create_existing(self):
        """Test ContactRepository create for existing contact."""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_existing_contact = Mock()
        mock_filter.first.return_value = mock_existing_contact
        
        repo = ContactRepository(mock_session)
        contact = repo.create(
            domain_id=1,
            email='test@example.com',
            name='John Doe'
        )
        
        assert contact == mock_existing_contact
        # Should not add to session since it already exists
        mock_session.add.assert_not_called()
    
    def test_email_log_repository_create(self):
        """Test EmailLogRepository create method."""
        mock_session = Mock()
        repo = EmailLogRepository(mock_session)
        
        log = repo.create(
            campaign_id=1,
            contact_id=1,
            to_address='test@example.com',
            from_address='sender@example.com',
            subject='Test Subject',
            status='queued'
        )
        
        assert isinstance(log, EmailLog)
        assert log.campaign_id == 1
        assert log.to_address == 'test@example.com'
        assert log.status == 'queued'
        mock_session.add.assert_called_once_with(log)
    
    def test_email_log_repository_update_status(self):
        """Test EmailLogRepository update_status method."""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_email_log = Mock()
        mock_filter.first.return_value = mock_email_log
        
        repo = EmailLogRepository(mock_session)
        repo.update_status(1, 'sent', sent_at=datetime.utcnow())
        
        assert mock_email_log.status == 'sent'
        assert mock_email_log.updated_at is not None
    
    def test_email_log_repository_get_campaign_stats(self):
        """Test EmailLogRepository get_campaign_stats method."""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        
        # Mock email logs with different statuses
        mock_logs = [
            Mock(status='sent'),
            Mock(status='sent'),
            Mock(status='failed'),
            Mock(status='queued')
        ]
        mock_filter.all.return_value = mock_logs
        
        repo = EmailLogRepository(mock_session)
        stats = repo.get_campaign_stats(1)
        
        assert stats['total'] == 4
        assert stats['sent'] == 2
        assert stats['failed'] == 1
        assert stats['queued'] == 1
