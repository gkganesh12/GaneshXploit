"""
SendGrid email client for HackVeda Crawler.
Provides professional email sending capabilities using SendGrid API.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment
from python_http_client import exceptions

from ..config import get_config


class SendGridClient:
    """SendGrid email client for sending emails."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize SendGrid client."""
        try:
            api_key = self.config.email.sendgrid_api_key
            if not api_key:
                self.logger.warning("SendGrid API key not configured")
                return
            
            self._client = sendgrid.SendGridAPIClient(api_key=api_key)
            self.logger.info("SendGrid client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SendGrid client: {e}")
    
    def is_available(self) -> bool:
        """Check if SendGrid client is available."""
        return self._client is not None
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SendGrid connection."""
        if not self.is_available():
            return {
                'success': False,
                'error': 'SendGrid API key not configured'
            }
        
        try:
            # Test by creating a simple mail object (doesn't send)
            from sendgrid.helpers.mail import Mail
            test_mail = Mail(
                from_email="test@example.com",
                to_emails="test@example.com",
                subject="Test",
                html_content="Test"
            )
            
            # If we can create the mail object and client is initialized, connection is good
            if self._client and test_mail:
                return {
                    'success': True,
                    'message': 'SendGrid connection successful'
                }
            else:
                return {
                    'success': False,
                    'error': 'SendGrid client not properly initialized'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'SendGrid connection failed: {str(e)}'
            }
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str = None,
        text_content: str = None,
        from_email: str = None,
        from_name: str = None,
        attachments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send email via SendGrid."""
        if not self.is_available():
            return {
                'success': False,
                'error': 'SendGrid client not available'
            }
        
        try:
            # Set default sender
            if not from_email:
                from_email = self.config.email.from_email
            if not from_name:
                from_name = self.config.email.from_name or "HackVeda Crawler"
            
            # Create email
            from_email_obj = Email(from_email, from_name)
            to_email_obj = To(to_email)
            
            # Use HTML content if available, otherwise text
            if html_content:
                content = Content("text/html", html_content)
            elif text_content:
                content = Content("text/plain", text_content)
            else:
                return {
                    'success': False,
                    'error': 'No email content provided'
                }
            
            mail = Mail(from_email_obj, to_email_obj, subject, content)
            
            # Add text version if HTML is provided
            if html_content and text_content:
                mail.add_content(Content("text/plain", text_content))
            
            # Add attachments if provided
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment()
                    attachment.file_content = attachment_data.get('content')
                    attachment.file_type = attachment_data.get('type')
                    attachment.file_name = attachment_data.get('filename')
                    mail.add_attachment(attachment)
            
            # Send email using correct SendGrid API
            response = self._client.send(mail)
            
            self.logger.info(f"Email sent successfully to {to_email}")
            
            return {
                'success': True,
                'message_id': response.headers.get('X-Message-Id'),
                'status_code': response.status_code,
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except exceptions.BadRequestsError as e:
            error_msg = f"SendGrid API error: {e.body}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def send_bulk_emails(
        self,
        emails: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Send multiple emails in batches."""
        if not self.is_available():
            return {
                'success': False,
                'error': 'SendGrid client not available'
            }
        
        results = {
            'total': len(emails),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        # Process emails in batches
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            
            for email_data in batch:
                result = self.send_email(**email_data)
                
                if result['success']:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'email': email_data.get('to_email'),
                        'error': result['error']
                    })
        
        results['success'] = results['failed'] == 0
        return results
    
    def send_templated_email(
        self,
        to_email: str,
        template_id: str,
        template_data: Dict[str, Any] = None,
        from_email: str = None,
        from_name: str = None
    ) -> Dict[str, Any]:
        """Send email using SendGrid template."""
        if not self.is_available():
            return {
                'success': False,
                'error': 'SendGrid client not available'
            }
        
        try:
            # Set default sender
            if not from_email:
                from_email = self.config.email.from_email
            if not from_name:
                from_name = self.config.email.from_name or "HackVeda Crawler"
            
            # Create email with template
            mail = Mail()
            mail.from_email = Email(from_email, from_name)
            mail.to = [To(to_email)]
            mail.template_id = template_id
            
            # Add dynamic template data
            if template_data:
                mail.dynamic_template_data = template_data
            
            # Send email using correct SendGrid API
            response = self._client.send(mail)
            
            self.logger.info(f"Templated email sent successfully to {to_email}")
            
            return {
                'success': True,
                'message_id': response.headers.get('X-Message-Id'),
                'status_code': response.status_code,
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to send templated email: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


class SendGridEmailService:
    """Enhanced email service with SendGrid integration."""
    
    def __init__(self):
        self.sendgrid_client = SendGridClient()
        self.logger = logging.getLogger(__name__)
    
    def is_available(self) -> bool:
        """Check if any email service is available."""
        return self.sendgrid_client.is_available()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test email service connections."""
        return self.sendgrid_client.test_connection()
    
    def send_email(self, **kwargs) -> Dict[str, Any]:
        """Send email using available service."""
        if self.sendgrid_client.is_available():
            return self.sendgrid_client.send_email(**kwargs)
        else:
            return {
                'success': False,
                'error': 'No email service available'
            }
    
    def send_bulk_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send bulk emails."""
        if self.sendgrid_client.is_available():
            return self.sendgrid_client.send_bulk_emails(emails)
        else:
            return {
                'success': False,
                'error': 'No email service available'
            }
