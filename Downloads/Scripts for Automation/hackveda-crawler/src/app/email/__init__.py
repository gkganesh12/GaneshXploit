"""
Email module for HackVeda Crawler.
Handles SendGrid, Gmail API integration, SMTP client, and email templating.
"""

from .gmail_api import GmailService, GmailAuthManager
from .smtp_client import SMTPClient
from .sendgrid_client import SendGridClient, SendGridEmailService
from .templates import EmailTemplateManager

__all__ = [
    'GmailService', 'GmailAuthManager', 'SMTPClient', 
    'SendGridClient', 'SendGridEmailService', 'EmailTemplateManager'
]
