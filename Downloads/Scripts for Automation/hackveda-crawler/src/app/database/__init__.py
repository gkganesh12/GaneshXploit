"""
Database module for HackVeda Crawler.
Handles database models, connections, and data persistence.
"""

from .models import (
    CrawlSession, SearchResult, EmailCampaign, EmailLog, 
    Contact, Domain, AuditLog
)
from .db import DatabaseManager, get_db_session

__all__ = [
    'CrawlSession', 'SearchResult', 'EmailCampaign', 'EmailLog',
    'Contact', 'Domain', 'AuditLog', 'DatabaseManager', 'get_db_session'
]
