"""
Tests for email module.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime

from app.email.gmail_api import GmailService, GmailAuthManager, GmailRateLimiter
from app.email.smtp_client import SMTPClient, EmailServiceManager
from app.email.templates import EmailTemplateManager


class TestGmailAuthManager:
    """Test Gmail OAuth2 authentication manager."""
    
    def test_auth_manager_initialization(self, test_config):
        """Test auth manager initialization."""
        auth_manager = GmailAuthManager(test_config)
        
        assert auth_manager.config == test_config
        assert auth_manager.credentials_path == test_config.email.gmail.credentials_path
        assert auth_manager.token_path == test_config.email.gmail.token_path
        assert auth_manager.SCOPES is not None
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"token": "test_token"}')
    @patch('app.email.gmail_api.Credentials')
    def test_get_credentials_existing_valid(self, mock_credentials, mock_file, mock_exists, test_config):
        """Test getting existing valid credentials."""
        mock_exists.return_value = True
        mock_creds = Mock()
        mock_creds.valid = True
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        auth_manager = GmailAuthManager(test_config)
        creds = auth_manager.get_credentials()
        
        assert creds == mock_creds
        mock_credentials.from_authorized_user_file.assert_called_once()
    
    @patch('os.path.exists')
    def test_get_credentials_no_token_file(self, mock_exists, test_config):
        """Test behavior when no token file exists."""
        mock_exists.return_value = False
        
        auth_manager = GmailAuthManager(test_config)
        
        # Should attempt OAuth flow (which will fail in test)
        with pytest.raises(FileNotFoundError):
            auth_manager.get_credentials()
    
    def test_check_credentials_status_no_files(self, test_config):
        """Test credentials status when no files exist."""
        with patch('os.path.exists', return_value=False):
            auth_manager = GmailAuthManager(test_config)
            status = auth_manager.check_credentials_status()
            
            assert status['has_credentials_file'] is False
            assert status['has_token_file'] is False
            assert status['is_valid'] is False


class TestGmailRateLimiter:
    """Test Gmail rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = GmailRateLimiter(daily_limit=100, rate_limit=5)
        
        assert limiter.daily_limit == 100
        assert limiter.rate_limit == 5
        assert limiter.sent_today == 0
    
    def test_can_send_email_within_limit(self):
        """Test email sending within daily limit."""
        limiter = GmailRateLimiter(daily_limit=100, rate_limit=5)
        
        assert limiter.can_send_email() is True
        
        # Simulate sending emails
        for _ in range(50):
            limiter.record_sent_email()
        
        assert limiter.can_send_email() is True
        assert limiter.sent_today == 50
    
    def test_can_send_email_exceeds_limit(self):
        """Test email sending when exceeding daily limit."""
        limiter = GmailRateLimiter(daily_limit=10, rate_limit=5)
        
        # Simulate sending emails up to limit
        for _ in range(10):
            limiter.record_sent_email()
        
        # Should not allow more emails
        assert limiter.can_send_email() is False
        assert limiter.sent_today == 10
    
    def test_daily_reset(self):
        """Test daily counter reset."""
        limiter = GmailRateLimiter(daily_limit=100, rate_limit=5)
        
        # Send some emails
        for _ in range(5):
            limiter.record_sent_email()
        
        assert limiter.sent_today == 5
        
        # Simulate new day by changing last_reset
        from datetime import date, timedelta
        limiter.last_reset = date.today() - timedelta(days=1)
        
        # Should reset counter
        assert limiter.can_send_email() is True
        # After checking, counter should be reset
        assert limiter.sent_today == 0


class TestGmailService:
    """Test Gmail service functionality."""
    
    @patch('app.email.gmail_api.GmailAuthManager')
    def test_gmail_service_initialization(self, mock_auth_manager, test_config):
        """Test Gmail service initialization."""
        service = GmailService(test_config)
        
        assert service.config == test_config
        assert service.auth_manager is not None
        assert service.rate_limiter is not None
    
    @patch('app.email.gmail_api.build')
    @patch('app.email.gmail_api.GmailAuthManager')
    def test_send_email_success(self, mock_auth_manager, mock_build, test_config):
        """Test successful email sending."""
        # Mock credentials and service
        mock_creds = Mock()
        mock_auth_manager.return_value.get_credentials.return_value = mock_creds
        
        mock_gmail_service = Mock()
        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'test_message_id',
            'threadId': 'test_thread_id'
        }
        mock_build.return_value = mock_gmail_service
        
        service = GmailService(test_config)
        
        result = service.send_email(
            to_address='test@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        assert result['success'] is True
        assert result['message_id'] == 'test_message_id'
        assert result['thread_id'] == 'test_thread_id'
    
    @patch('app.email.gmail_api.GmailAuthManager')
    def test_send_email_rate_limit_exceeded(self, mock_auth_manager, test_config):
        """Test email sending when rate limit is exceeded."""
        service = GmailService(test_config)
        
        # Mock rate limiter to return False
        service.rate_limiter.can_send_email = Mock(return_value=False)
        
        with pytest.raises(Exception, match="Daily email limit exceeded"):
            service.send_email(
                to_address='test@example.com',
                subject='Test Subject',
                body='Test body'
            )
    
    @patch('app.email.gmail_api.EmailTemplateManager')
    @patch('app.email.gmail_api.build')
    @patch('app.email.gmail_api.GmailAuthManager')
    def test_send_templated_email(self, mock_auth_manager, mock_build, mock_template_manager, test_config):
        """Test sending templated email."""
        # Mock template rendering
        mock_template_manager.return_value.render_template.return_value = {
            'subject': 'Rendered Subject',
            'text_body': 'Rendered text body',
            'html_body': '<p>Rendered HTML body</p>'
        }
        
        # Mock Gmail service
        mock_creds = Mock()
        mock_auth_manager.return_value.get_credentials.return_value = mock_creds
        
        mock_gmail_service = Mock()
        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'test_message_id'
        }
        mock_build.return_value = mock_gmail_service
        
        service = GmailService(test_config)
        
        result = service.send_templated_email(
            to_address='test@example.com',
            template_name='test_template',
            context={'name': 'Test User'}
        )
        
        assert result['success'] is True
        mock_template_manager.return_value.render_template.assert_called_once()


class TestSMTPClient:
    """Test SMTP client functionality."""
    
    def test_smtp_client_initialization(self, test_config):
        """Test SMTP client initialization."""
        # Add SMTP config to test config
        test_config.email.smtp = Mock(
            host='smtp.gmail.com',
            port=587,
            use_tls=True,
            username='test@example.com',
            password='test_password'
        )
        
        client = SMTPClient(test_config)
        
        assert client.smtp_host == 'smtp.gmail.com'
        assert client.smtp_port == 587
        assert client.use_tls is True
        assert client.username == 'test@example.com'
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp, test_config):
        """Test successful SMTP email sending."""
        # Add SMTP config
        test_config.email.smtp = Mock(
            host='smtp.gmail.com',
            port=587,
            use_tls=True,
            username='test@example.com',
            password='test_password'
        )
        
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        client = SMTPClient(test_config)
        
        result = client.send_email(
            to_address='recipient@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        assert result['success'] is True
        assert result['method'] == 'smtp'
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    def test_send_email_no_credentials(self, test_config):
        """Test SMTP email sending without credentials."""
        # No SMTP config
        test_config.email.smtp = Mock(
            host='smtp.gmail.com',
            port=587,
            use_tls=True,
            username='',
            password=''
        )
        
        client = SMTPClient(test_config)
        
        result = client.send_email(
            to_address='recipient@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        assert result['success'] is False
        assert 'credentials not configured' in result['error']


class TestEmailServiceManager:
    """Test email service manager with fallback."""
    
    @patch('app.email.smtp_client.GmailService')
    @patch('app.email.smtp_client.SMTPClient')
    def test_service_manager_initialization(self, mock_smtp, mock_gmail, test_config):
        """Test service manager initialization."""
        manager = EmailServiceManager(test_config)
        
        assert manager.config == test_config
        assert manager.primary_service == test_config.email.provider
    
    @patch('app.email.smtp_client.GmailService')
    def test_send_email_gmail_success(self, mock_gmail_class, test_config):
        """Test email sending with Gmail API success."""
        # Mock Gmail service
        mock_gmail = Mock()
        mock_gmail.send_email.return_value = {'success': True, 'message_id': 'test_id'}
        mock_gmail_class.return_value = mock_gmail
        
        manager = EmailServiceManager(test_config)
        manager.gmail_service = mock_gmail
        
        result = manager.send_email(
            to_address='test@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        assert result['success'] is True
        assert result['message_id'] == 'test_id'
        assert 'fallback_used' not in result
    
    @patch('app.email.smtp_client.SMTPClient')
    @patch('app.email.smtp_client.GmailService')
    def test_send_email_fallback_to_smtp(self, mock_gmail_class, mock_smtp_class, test_config):
        """Test email sending with fallback to SMTP."""
        # Mock Gmail service failure
        mock_gmail = Mock()
        mock_gmail.send_email.return_value = {'success': False, 'error': 'Gmail failed'}
        mock_gmail_class.return_value = mock_gmail
        
        # Mock SMTP success
        mock_smtp = Mock()
        mock_smtp.send_email.return_value = {'success': True, 'method': 'smtp'}
        mock_smtp_class.return_value = mock_smtp
        
        manager = EmailServiceManager(test_config)
        manager.gmail_service = mock_gmail
        manager.smtp_client = mock_smtp
        
        result = manager.send_email(
            to_address='test@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        assert result['success'] is True
        assert result['fallback_used'] is True
        assert result['method'] == 'smtp'


class TestEmailTemplateManager:
    """Test email template management."""
    
    def test_template_manager_initialization(self, temp_dir):
        """Test template manager initialization."""
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        assert manager.template_dir == str(temp_dir)
        assert manager.env is not None
    
    def test_render_template_basic(self, temp_dir, sample_email_template):
        """Test basic template rendering."""
        # Create template file
        template_path = temp_dir / 'test_template.html'
        template_path.write_text(sample_email_template['html_body'])
        
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        context = {
            'recipient_name': 'John Doe',
            'company_name': 'Test Corp',
            'sender_name': 'Jane Smith'
        }
        
        result = manager.render_template('test_template', context)
        
        assert 'subject' in result
        assert 'html_body' in result
        assert 'text_body' in result
        assert 'John Doe' in result['html_body']
        assert 'Test Corp' in result['html_body']
    
    def test_render_template_with_subject_comment(self, temp_dir):
        """Test template rendering with subject in comment."""
        template_content = """
        <!-- SUBJECT: Hello {{ recipient_name }}! -->
        <html>
        <body>
            <h1>Hello {{ recipient_name }}!</h1>
            <p>Welcome to {{ company_name }}.</p>
        </body>
        </html>
        """
        
        template_path = temp_dir / 'test_subject.html'
        template_path.write_text(template_content)
        
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        context = {
            'recipient_name': 'Alice',
            'company_name': 'Example Inc'
        }
        
        result = manager.render_template('test_subject', context)
        
        assert result['subject'] == 'Hello Alice!'
        assert 'Alice' in result['html_body']
        assert 'Example Inc' in result['html_body']
    
    def test_render_template_not_found(self, temp_dir):
        """Test rendering non-existent template."""
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        with pytest.raises(FileNotFoundError):
            manager.render_template('nonexistent_template', {})
    
    def test_list_templates(self, temp_dir):
        """Test listing available templates."""
        # Create some template files
        (temp_dir / 'template1.html').write_text('<html>Template 1</html>')
        (temp_dir / 'template2.html').write_text('<html>Template 2</html>')
        (temp_dir / 'not_template.txt').write_text('Not a template')
        
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        templates = manager.list_templates()
        
        assert 'template1.html' in templates
        assert 'template2.html' in templates
        assert 'not_template.txt' not in templates
    
    def test_validate_template(self, temp_dir, sample_email_template):
        """Test template validation."""
        template_path = temp_dir / 'valid_template.html'
        template_path.write_text(sample_email_template['html_body'])
        
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        validation_result = manager.validate_template('valid_template')
        
        assert validation_result['valid'] is True
        assert validation_result['rendered_successfully'] is True
        assert validation_result['subject_length'] > 0
        assert validation_result['html_length'] > 0
    
    def test_validate_invalid_template(self, temp_dir):
        """Test validation of invalid template."""
        # Create template with invalid Jinja2 syntax
        invalid_template = """
        <html>
        <body>
            <h1>Hello {{ recipient_name!</h1>  <!-- Missing closing brace -->
        </body>
        </html>
        """
        
        template_path = temp_dir / 'invalid_template.html'
        template_path.write_text(invalid_template)
        
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        validation_result = manager.validate_template('invalid_template')
        
        assert validation_result['valid'] is False
        assert 'error' in validation_result
    
    def test_html_to_text_conversion(self, temp_dir):
        """Test HTML to text conversion."""
        html_template = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Main Title</h1>
            <p>This is a paragraph with <strong>bold</strong> text.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <script>console.log('should be removed');</script>
        </body>
        </html>
        """
        
        template_path = temp_dir / 'html_template.html'
        template_path.write_text(html_template)
        
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        result = manager.render_template('html_template', {})
        
        text_body = result['text_body']
        
        # Should contain text content
        assert 'Main Title' in text_body
        assert 'This is a paragraph' in text_body
        assert 'Item 1' in text_body
        
        # Should not contain HTML tags or script content
        assert '<h1>' not in text_body
        assert '<script>' not in text_body
        assert 'console.log' not in text_body
    
    def test_currency_filter(self, temp_dir):
        """Test custom currency filter."""
        template_content = """
        <html>
        <body>
            <p>Price: {{ price | currency }}</p>
            <p>Euro Price: {{ euro_price | currency('EUR') }}</p>
        </body>
        </html>
        """
        
        template_path = temp_dir / 'currency_template.html'
        template_path.write_text(template_content)
        
        manager = EmailTemplateManager(template_dir=str(temp_dir))
        
        context = {
            'price': 99.99,
            'euro_price': 85.50
        }
        
        result = manager.render_template('currency_template', context)
        
        assert '$99.99' in result['html_body']
        assert '85.50 EUR' in result['html_body']
