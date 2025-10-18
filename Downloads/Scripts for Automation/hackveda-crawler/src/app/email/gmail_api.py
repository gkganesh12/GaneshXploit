"""
Gmail API integration with OAuth2 authentication.
Handles secure email sending through Gmail API with proper authentication and rate limiting.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64

from ..config import get_config
from ..database.models import EmailLog


class GmailAuthManager:
    """Manages Gmail OAuth2 authentication and token refresh."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly'
    ]
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self.credentials_path = self.config.email.gmail.credentials_path
        self.token_path = self.config.email.gmail.token_path
        
        # Ensure directories exist
        Path(self.credentials_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get valid Gmail API credentials."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
                self.logger.debug("Loaded existing credentials from token file")
            except Exception as e:
                self.logger.warning(f"Failed to load existing credentials: {e}")
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info("Successfully refreshed expired credentials")
                except Exception as e:
                    self.logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                creds = self._run_oauth_flow()
            
            # Save the credentials for the next run
            if creds:
                self._save_credentials(creds)
        
        return creds
    
    def _run_oauth_flow(self) -> Optional[Credentials]:
        """Run OAuth2 flow to get new credentials."""
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"Gmail credentials file not found: {self.credentials_path}\n"
                "Please follow the setup instructions to download credentials.json"
            )
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, self.SCOPES
            )
            
            # Run local server flow
            creds = flow.run_local_server(port=0)
            self.logger.info("Successfully completed OAuth2 flow")
            return creds
            
        except Exception as e:
            self.logger.error(f"OAuth2 flow failed: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials):
        """Save credentials to token file."""
        try:
            with open(self.token_path, 'w') as token_file:
                token_file.write(creds.to_json())
            self.logger.info(f"Credentials saved to {self.token_path}")
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")
    
    def revoke_credentials(self):
        """Revoke and delete stored credentials."""
        try:
            creds = self.get_credentials()
            if creds:
                creds.revoke(Request())
            
            # Delete token file
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
            
            self.logger.info("Credentials revoked and deleted")
            
        except Exception as e:
            self.logger.error(f"Failed to revoke credentials: {e}")
    
    def check_credentials_status(self) -> Dict[str, Any]:
        """Check the status of current credentials."""
        status = {
            'has_credentials_file': os.path.exists(self.credentials_path),
            'has_token_file': os.path.exists(self.token_path),
            'is_valid': False,
            'expires_at': None,
            'scopes': self.SCOPES
        }
        
        try:
            creds = self.get_credentials()
            if creds:
                status['is_valid'] = creds.valid
                if creds.expiry:
                    status['expires_at'] = creds.expiry.isoformat()
        except Exception as e:
            status['error'] = str(e)
        
        return status


class GmailRateLimiter:
    """Handles Gmail API rate limiting."""
    
    def __init__(self, daily_limit: int = 500, rate_limit: int = 10):
        self.daily_limit = daily_limit
        self.rate_limit = rate_limit  # emails per minute
        self.sent_today = 0
        self.last_reset = datetime.now().date()
        self.last_send_time = 0
        self.logger = logging.getLogger(__name__)
    
    def can_send_email(self) -> bool:
        """Check if we can send an email within rate limits."""
        # Reset daily counter if new day
        today = datetime.now().date()
        if today > self.last_reset:
            self.sent_today = 0
            self.last_reset = today
        
        # Check daily limit
        if self.sent_today >= self.daily_limit:
            self.logger.warning(f"Daily email limit reached: {self.sent_today}/{self.daily_limit}")
            return False
        
        return True
    
    def wait_if_needed(self):
        """Wait if rate limit requires it."""
        current_time = time.time()
        time_since_last = current_time - self.last_send_time
        
        # Calculate minimum time between emails (60 seconds / rate_limit)
        min_interval = 60.0 / self.rate_limit
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            self.logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        self.last_send_time = time.time()
    
    def record_sent_email(self):
        """Record that an email was sent."""
        self.sent_today += 1
        self.logger.debug(f"Emails sent today: {self.sent_today}/{self.daily_limit}")


class GmailService:
    """Main Gmail service for sending emails."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self.auth_manager = GmailAuthManager(config)
        self.rate_limiter = GmailRateLimiter(
            daily_limit=self.config.email.gmail.daily_limit,
            rate_limit=self.config.email.gmail.rate_limit
        )
        self._service = None
    
    def _get_service(self):
        """Get Gmail API service instance."""
        if self._service is None:
            creds = self.auth_manager.get_credentials()
            if not creds:
                raise Exception("Failed to get valid Gmail credentials")
            
            self._service = build('gmail', 'v1', credentials=creds)
            self.logger.debug("Gmail service initialized")
        
        return self._service
    
    def send_email(self, to_address: str, subject: str, body: str, 
                   html_body: str = None, attachments: List[str] = None,
                   from_name: str = None) -> Dict[str, Any]:
        """Send an email via Gmail API."""
        
        # Check rate limits
        if not self.rate_limiter.can_send_email():
            raise Exception("Daily email limit exceeded")
        
        # Wait for rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            # Create message
            message = self._create_message(
                to_address, subject, body, html_body, attachments, from_name
            )
            
            # Send message
            service = self._get_service()
            result = service.users().messages().send(
                userId='me', 
                body=message
            ).execute()
            
            # Record successful send
            self.rate_limiter.record_sent_email()
            
            self.logger.info(f"Email sent successfully to {to_address}")
            
            return {
                'success': True,
                'message_id': result.get('id'),
                'thread_id': result.get('threadId'),
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except HttpError as e:
            error_msg = f"Gmail API error: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': e.resp.status if hasattr(e, 'resp') else None
            }
        
        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _create_message(self, to_address: str, subject: str, body: str,
                       html_body: str = None, attachments: List[str] = None,
                       from_name: str = None) -> Dict[str, str]:
        """Create email message for Gmail API."""
        
        # Determine from address
        from_address = self.config.email.gmail.from_address
        if from_name:
            from_header = f"{from_name} <{from_address}>"
        else:
            from_header = from_address
        
        # Create message
        if html_body or attachments:
            message = MIMEMultipart('alternative')
        else:
            message = MIMEText(body, 'plain', 'utf-8')
            message['to'] = to_address
            message['from'] = from_header
            message['subject'] = subject
            
            return {
                'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            }
        
        # Multipart message
        message['to'] = to_address
        message['from'] = from_header
        message['subject'] = subject
        
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
        
        return {
            'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        }
    
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
    
    def send_templated_email(self, to_address: str, template_name: str,
                           context: Dict[str, Any], from_name: str = None) -> Dict[str, Any]:
        """Send email using a template."""
        from .templates import EmailTemplateManager
        
        template_manager = EmailTemplateManager()
        
        try:
            # Render template
            rendered = template_manager.render_template(template_name, context)
            
            # Send email
            return self.send_email(
                to_address=to_address,
                subject=rendered['subject'],
                body=rendered['text_body'],
                html_body=rendered.get('html_body'),
                from_name=from_name
            )
            
        except Exception as e:
            error_msg = f"Failed to send templated email: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def send_bulk_emails(self, recipients: List[Dict[str, Any]], 
                        template_name: str, delay_between: int = 5) -> List[Dict[str, Any]]:
        """Send bulk emails with rate limiting."""
        results = []
        
        for i, recipient in enumerate(recipients):
            try:
                # Extract recipient info
                to_address = recipient['email']
                context = recipient.get('context', {})
                from_name = recipient.get('from_name')
                
                # Send email
                result = self.send_templated_email(
                    to_address, template_name, context, from_name
                )
                
                result['recipient'] = to_address
                result['index'] = i
                results.append(result)
                
                # Log progress
                if result['success']:
                    self.logger.info(f"Bulk email {i+1}/{len(recipients)} sent to {to_address}")
                else:
                    self.logger.error(f"Bulk email {i+1}/{len(recipients)} failed for {to_address}")
                
                # Delay between emails (except for last one)
                if i < len(recipients) - 1:
                    time.sleep(delay_between)
                
            except Exception as e:
                self.logger.error(f"Error sending bulk email to {recipient.get('email', 'unknown')}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'recipient': recipient.get('email', 'unknown'),
                    'index': i
                })
        
        return results
    
    def test_connection(self) -> bool:
        """Test Gmail API connection."""
        try:
            service = self._get_service()
            profile = service.users().getProfile(userId='me').execute()
            self.logger.info(f"Gmail connection test successful for {profile.get('emailAddress')}")
            return True
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {e}")
            return False
    
    def get_quota_info(self) -> Dict[str, Any]:
        """Get current quota and usage information."""
        return {
            'daily_limit': self.rate_limiter.daily_limit,
            'sent_today': self.rate_limiter.sent_today,
            'remaining_today': self.rate_limiter.daily_limit - self.rate_limiter.sent_today,
            'rate_limit_per_minute': self.rate_limiter.rate_limit,
            'last_reset': self.rate_limiter.last_reset.isoformat()
        }
    
    def get_sent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently sent messages."""
        try:
            service = self._get_service()
            
            # Get sent messages
            results = service.users().messages().list(
                userId='me',
                labelIds=['SENT'],
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            sent_messages = []
            
            for msg in messages:
                # Get message details
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata'
                ).execute()
                
                # Extract headers
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
                
                sent_messages.append({
                    'id': message['id'],
                    'thread_id': message['threadId'],
                    'to': headers.get('To'),
                    'subject': headers.get('Subject'),
                    'date': headers.get('Date'),
                    'snippet': message.get('snippet', '')
                })
            
            return sent_messages
            
        except Exception as e:
            self.logger.error(f"Failed to get sent messages: {e}")
            return []
