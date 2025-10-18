"""
SMTP client for email sending (fallback option).
Provides SMTP-based email sending with OAuth2 and App Password support.
"""

import smtplib
import logging
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime

from ..config import get_config


class SMTPClient:
    """SMTP client for sending emails (fallback to Gmail API)."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        # SMTP configuration
        self.smtp_host = getattr(self.config.email, 'smtp', {}).get('host', 'smtp.gmail.com')
        self.smtp_port = getattr(self.config.email, 'smtp', {}).get('port', 587)
        self.use_tls = getattr(self.config.email, 'smtp', {}).get('use_tls', True)
        self.username = getattr(self.config.email, 'smtp', {}).get('username', '')
        self.password = getattr(self.config.email, 'smtp', {}).get('password', '')
        
        if not self.password:
            self.password = os.getenv('SMTP_PASSWORD', '')
        
        # Validate configuration
        if not self.username or not self.password:
            # Only warn if SMTP is actually needed (not when using SendGrid)
            import os
            if os.getenv('EMAIL_PROVIDER', '').lower() != 'sendgrid':
                self.logger.warning("SMTP credentials not configured. Set username/password in config or SMTP_PASSWORD environment variable.")
            self._configured = False
        else:
            self._configured = True
    
    def send_email(self, to_address: str, subject: str, body: str,
                   html_body: str = None, attachments: List[str] = None,
                   from_name: str = None) -> Dict[str, Any]:
        """Send email via SMTP."""
        
        if not self.username or not self.password:
            return {
                'success': False,
                'error': 'SMTP credentials not configured'
            }
        
        try:
            # Create message
            message = self._create_message(
                to_address, subject, body, html_body, attachments, from_name
            )
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                # Login
                server.login(self.username, self.password)
                
                # Send message
                from_address = self.config.email.gmail.from_address or self.username
                server.send_message(message, from_addr=from_address, to_addrs=[to_address])
            
            self.logger.info(f"Email sent successfully via SMTP to {to_address}")
            
            return {
                'success': True,
                'message_id': None,  # SMTP doesn't provide message ID
                'sent_at': datetime.utcnow().isoformat(),
                'method': 'smtp'
            }
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': 'auth_failed'
            }
        
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"SMTP recipients refused: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': 'recipients_refused'
            }
        
        except Exception as e:
            error_msg = f"SMTP send failed: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _create_message(self, to_address: str, subject: str, body: str,
                       html_body: str = None, attachments: List[str] = None,
                       from_name: str = None) -> MIMEMultipart:
        """Create email message for SMTP."""
        
        # Determine from address
        from_address = self.config.email.gmail.from_address or self.username
        if from_name:
            from_header = f"{from_name} <{from_address}>"
        else:
            from_header = from_address
        
        # Create message
        if html_body or attachments:
            message = MIMEMultipart('alternative')
        else:
            message = MIMEText(body, 'plain', 'utf-8')
            message['To'] = to_address
            message['From'] = from_header
            message['Subject'] = subject
            return message
        
        # Multipart message
        message['To'] = to_address
        message['From'] = from_header
        message['Subject'] = subject
        
        # Add text part
        if body:
            text_part = MIMEText(body, 'plain', 'utf-8')
            message.attach(text_part)
        
        # Add HTML part
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            message.attach(html_part)
        
        # Add attachments
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    self._add_attachment(message, file_path)
        
        return message
    
    def _add_attachment(self, message: MIMEMultipart, file_path: str):
        """Add file attachment to email message."""
        try:
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            
            filename = os.path.basename(file_path)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            message.attach(part)
            self.logger.debug(f"Added attachment: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to add attachment {file_path}: {e}")
    
    def test_connection(self) -> bool:
        """Test SMTP connection and authentication."""
        if not self.username or not self.password:
            self.logger.error("SMTP credentials not configured")
            return False
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                
            self.logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def send_test_email(self, to_address: str) -> Dict[str, Any]:
        """Send a test email to verify SMTP functionality."""
        subject = "HackVeda Crawler - SMTP Test Email"
        body = """
This is a test email from HackVeda Crawler to verify SMTP functionality.

If you received this email, your SMTP configuration is working correctly.

Best regards,
HackVeda Crawler Team
        """.strip()
        
        return self.send_email(to_address, subject, body)


class EmailServiceManager:
    """Manages email services with fallback from SendGrid to Gmail API to SMTP."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.sendgrid_service = None
        self.gmail_service = None
        self.smtp_client = None
        
        # Determine primary service
        self.primary_service = self.config.email.provider
        
        # Initialize SendGrid
        if self.primary_service == 'sendgrid':
            try:
                from .sendgrid_client import SendGridEmailService
                self.sendgrid_service = SendGridEmailService()
            except Exception as e:
                self.logger.warning(f"Failed to initialize SendGrid service: {e}")
        
        # Initialize Gmail API
        elif self.primary_service == 'gmail_api':
            try:
                from .gmail_api import GmailService
                self.gmail_service = GmailService(config)
            except Exception as e:
                self.logger.warning(f"Failed to initialize Gmail API service: {e}")
        
        # Initialize SMTP as fallback only if SendGrid is not primary
        if self.primary_service != 'sendgrid':
            try:
                self.smtp_client = SMTPClient(config)
            except Exception as e:
                self.logger.warning(f"Failed to initialize SMTP client: {e}")
        else:
            # Skip SMTP initialization when using SendGrid
            self.smtp_client = None
    
    def send_email(self, to_address: str, subject: str, body: str,
                   html_body: str = None, attachments: List[str] = None,
                   from_name: str = None) -> Dict[str, Any]:
        """Send email using primary service with fallback."""
        
        # Try SendGrid first (if configured)
        if self.primary_service == 'sendgrid' and self.sendgrid_service:
            try:
                result = self.sendgrid_service.send_email(
                    to_email=to_address,
                    subject=subject,
                    text_content=body,
                    html_content=html_body,
                    from_name=from_name
                )
                if result['success']:
                    return result
                else:
                    self.logger.warning(f"SendGrid failed: {result.get('error')}")
            except Exception as e:
                self.logger.warning(f"SendGrid error: {e}")
        
        # Try Gmail API (if configured)
        elif self.primary_service == 'gmail_api' and self.gmail_service:
            try:
                result = self.gmail_service.send_email(
                    to_address, subject, body, html_body, attachments, from_name
                )
                if result['success']:
                    return result
                else:
                    self.logger.warning(f"Gmail API failed: {result.get('error')}")
            except Exception as e:
                self.logger.warning(f"Gmail API error: {e}")
        
        # Fallback to SMTP
        if self.smtp_client:
            try:
                result = self.smtp_client.send_email(
                    to_address, subject, body, html_body, attachments, from_name
                )
                if result['success']:
                    result['fallback_used'] = True
                return result
            except Exception as e:
                self.logger.error(f"SMTP fallback also failed: {e}")
        
        # All methods failed
        return {
            'success': False,
            'error': 'All email services failed',
            'primary_service': self.primary_service
        }
    
    def test_services(self) -> Dict[str, Any]:
        """Test all available email services."""
        results = {
            'sendgrid': {'available': False, 'working': False},
            'gmail_api': {'available': False, 'working': False},
            'smtp': {'available': False, 'working': False}
        }
        
        # Test SendGrid
        if self.sendgrid_service:
            results['sendgrid']['available'] = True
            try:
                test_result = self.sendgrid_service.test_connection()
                results['sendgrid']['working'] = test_result.get('success', False)
                if not test_result.get('success'):
                    results['sendgrid']['error'] = test_result.get('error', 'Unknown error')
            except Exception as e:
                results['sendgrid']['error'] = str(e)
        
        # Test Gmail API
        if self.gmail_service:
            results['gmail_api']['available'] = True
            try:
                results['gmail_api']['working'] = self.gmail_service.test_connection()
            except Exception as e:
                results['gmail_api']['error'] = str(e)
        
        # Test SMTP
        if self.smtp_client:
            results['smtp']['available'] = True
            try:
                results['smtp']['working'] = self.smtp_client.test_connection()
            except Exception as e:
                results['smtp']['error'] = str(e)
        
        return results
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of email services."""
        status = {
            'primary_service': self.primary_service,
            'services': self.test_services()
        }
        
        # Add quota info if Gmail API is available
        if self.gmail_service:
            try:
                status['gmail_quota'] = self.gmail_service.get_quota_info()
            except Exception as e:
                status['gmail_quota_error'] = str(e)
        
        return status
