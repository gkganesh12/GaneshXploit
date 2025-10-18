"""
Pytest configuration and fixtures for HackVeda Crawler tests.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.config import Config, ConfigManager
from app.database.db import DatabaseManager


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return Config(
        crawler=Mock(
            mode='light',
            user_agent='TestBot/1.0',
            delay_min=0.1,
            delay_max=0.2,
            max_results=5,
            respect_robots_txt=False,
            timeout=10,
            max_retries=1
        ),
        database=Mock(
            url='sqlite:///:memory:',
            pool_size=1,
            max_overflow=0,
            echo=False
        ),
        email=Mock(
            provider='gmail_api',
            gmail=Mock(
                credentials_path='test_credentials.json',
                token_path='test_token.json',
                from_address='test@example.com',
                from_name='Test User',
                daily_limit=100,
                rate_limit=10
            )
        ),
        app=Mock(
            concurrency=1,
            log_level='DEBUG',
            data_retention_days=30
        )
    )


@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_db_manager(test_config):
    """Provide mock database manager."""
    db_manager = Mock(spec=DatabaseManager)
    db_manager.get_session = MagicMock()
    db_manager.init_database = Mock()
    db_manager.health_check = Mock(return_value=True)
    db_manager.get_stats = Mock(return_value={
        'crawl_sessions': 0,
        'search_results': 0,
        'domains': 0,
        'contacts': 0
    })
    return db_manager


@pytest.fixture
def sample_search_results():
    """Provide sample search results for testing."""
    from app.crawler.google_serp import SearchResult
    from datetime import datetime
    
    return [
        SearchResult(
            title="Test Result 1",
            url="https://example.com/1",
            snippet="This is a test snippet for result 1",
            rank=1,
            domain="example.com",
            crawl_timestamp=datetime.now(),
            response_time=1.5,
            metadata={'keyword': 'test query'}
        ),
        SearchResult(
            title="Test Result 2",
            url="https://example.org/2",
            snippet="This is a test snippet for result 2",
            rank=2,
            domain="example.org",
            crawl_timestamp=datetime.now(),
            response_time=2.1,
            metadata={'keyword': 'test query'}
        )
    ]


@pytest.fixture
def mock_requests():
    """Mock requests module for HTTP testing."""
    import responses
    return responses


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <h1>Welcome to Test Site</h1>
        <p>Contact us at <a href="mailto:contact@example.com">contact@example.com</a></p>
        <p>Phone: <a href="tel:+1234567890">+1 (234) 567-890</a></p>
        <div>
            <a href="/contact">Contact Us</a>
            <a href="/about">About Us</a>
        </div>
        <footer>
            <a href="https://twitter.com/example">Twitter</a>
            <a href="https://linkedin.com/company/example">LinkedIn</a>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service for testing."""
    service = Mock()
    service.send_email = Mock(return_value={
        'success': True,
        'message_id': 'test_message_id',
        'sent_at': '2024-01-01T00:00:00Z'
    })
    service.test_connection = Mock(return_value=True)
    service.get_quota_info = Mock(return_value={
        'daily_limit': 500,
        'sent_today': 0,
        'remaining_today': 500
    })
    return service


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')


@pytest.fixture
def mock_google_search_response():
    """Mock Google search response HTML."""
    return """
    <html>
    <body>
        <div class="g">
            <h3>Test Result 1</h3>
            <a href="https://example.com/1">https://example.com/1</a>
            <span class="VwiC3b">This is a test snippet for the first result</span>
        </div>
        <div class="g">
            <h3>Test Result 2</h3>
            <a href="https://example.org/2">https://example.org/2</a>
            <span class="VwiC3b">This is a test snippet for the second result</span>
        </div>
    </body>
    </html>
    """


# Test data fixtures
@pytest.fixture
def sample_email_template():
    """Sample email template for testing."""
    return {
        'name': 'test_template',
        'subject': 'Test Subject - {{ recipient_name }}',
        'html_body': '''
        <html>
        <body>
            <h1>Hello {{ recipient_name }}!</h1>
            <p>This is a test email from {{ company_name }}.</p>
            <p>Best regards,<br>{{ sender_name }}</p>
        </body>
        </html>
        ''',
        'text_body': '''
        Hello {{ recipient_name }}!
        
        This is a test email from {{ company_name }}.
        
        Best regards,
        {{ sender_name }}
        '''
    }


@pytest.fixture
def sample_contacts():
    """Sample contact data for testing."""
    return [
        {
            'email': 'john@example.com',
            'name': 'John Doe',
            'company': 'Example Corp',
            'domain': 'example.com'
        },
        {
            'email': 'jane@testsite.org',
            'name': 'Jane Smith',
            'company': 'Test Site',
            'domain': 'testsite.org'
        }
    ]
