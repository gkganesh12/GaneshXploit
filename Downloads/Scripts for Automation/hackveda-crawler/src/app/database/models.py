"""
Database models for HackVeda Crawler.
Defines SQLAlchemy models for storing crawl results, email campaigns, and audit logs.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import json

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class CrawlSession(Base):
    """Represents a crawling session."""
    __tablename__ = 'crawl_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(255), nullable=False)
    keywords = Column(JSON, nullable=False)  # List of keywords to crawl
    status = Column(String(50), default='running')  # running, completed, failed
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    total_results = Column(Integer, default=0)
    config = Column(JSON)  # Crawl configuration
    error_message = Column(Text)
    
    # Relationships
    search_results = relationship("SearchResult", back_populates="crawl_session", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_crawl_session_status', 'status'),
        Index('idx_crawl_session_start_time', 'start_time'),
    )
    
    def __repr__(self):
        return f"<CrawlSession(id={self.id}, name='{self.session_name}', status='{self.status}')>"


class SearchResult(Base):
    """Represents a search result from crawling."""
    __tablename__ = 'search_results'
    
    id = Column(Integer, primary_key=True)
    crawl_session_id = Column(Integer, ForeignKey('crawl_sessions.id'), nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=True)
    
    # Basic result data
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    snippet = Column(Text)
    rank = Column(Integer, nullable=False)
    domain = Column(String(255), nullable=False)
    
    # Enriched data
    normalized_title = Column(Text)
    normalized_snippet = Column(Text)
    keywords = Column(JSON)  # List of extracted keywords
    language = Column(String(10), default='en')
    
    # Metadata
    crawl_timestamp = Column(DateTime, default=datetime.utcnow)
    response_time = Column(Float)
    source_keyword = Column(String(255))
    
    # Quality scores
    relevance_score = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    
    # Additional metadata
    result_metadata = Column(JSON)
    
    # Relationships
    crawl_session = relationship("CrawlSession", back_populates="search_results")
    domain_info = relationship("Domain", back_populates="search_results")
    
    # Indexes
    __table_args__ = (
        Index('idx_search_result_url', 'url'),
        Index('idx_search_result_domain', 'domain'),
        Index('idx_search_result_keyword', 'source_keyword'),
        Index('idx_search_result_timestamp', 'crawl_timestamp'),
        Index('idx_search_result_quality', 'quality_score'),
    )
    
    @validates('url')
    def validate_url(self, key, url):
        if not url or not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return url
    
    def __repr__(self):
        return f"<SearchResult(id={self.id}, domain='{self.domain}', rank={self.rank})>"


class Domain(Base):
    """Represents domain information and metadata."""
    __tablename__ = 'domains'
    
    id = Column(Integer, primary_key=True)
    domain = Column(String(255), unique=True, nullable=False)
    
    # Domain analysis
    tld = Column(String(50))
    is_subdomain = Column(Boolean, default=False)
    main_domain = Column(String(255))
    quality_rating = Column(String(20))  # high, medium, low
    
    # Contact information
    has_contact_info = Column(Boolean, default=False)
    contact_emails = Column(JSON)  # List of found email addresses
    contact_pages = Column(JSON)  # List of contact page URLs
    social_links = Column(JSON)  # Social media links
    
    # Metadata
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_crawled = Column(DateTime, default=datetime.utcnow)
    crawl_count = Column(Integer, default=1)
    
    # External data (optional)
    domain_authority = Column(Integer)  # From external APIs
    page_authority = Column(Integer)
    
    # Relationships
    search_results = relationship("SearchResult", back_populates="domain_info")
    contacts = relationship("Contact", back_populates="domain_info")
    
    # Indexes
    __table_args__ = (
        Index('idx_domain_name', 'domain'),
        Index('idx_domain_quality', 'quality_rating'),
        Index('idx_domain_last_crawled', 'last_crawled'),
    )
    
    def __repr__(self):
        return f"<Domain(id={self.id}, domain='{self.domain}', quality='{self.quality_rating}')>"


class Contact(Base):
    """Represents extracted contact information."""
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    
    # Contact details
    email = Column(String(255))
    name = Column(String(255))
    title = Column(String(255))
    company = Column(String(255))
    phone = Column(String(50))
    
    # Source information
    source_url = Column(Text)  # Where the contact was found
    extraction_method = Column(String(50))  # email_pattern, contact_page, etc.
    confidence_score = Column(Float, default=0.0)
    
    # Email status
    email_status = Column(String(50), default='new')  # new, contacted, bounced, opted_out
    last_contacted = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domain_info = relationship("Domain", back_populates="contacts")
    email_logs = relationship("EmailLog", back_populates="contact")
    
    # Indexes
    __table_args__ = (
        Index('idx_contact_email', 'email'),
        Index('idx_contact_domain', 'domain_id'),
        Index('idx_contact_status', 'email_status'),
        UniqueConstraint('email', 'domain_id', name='uq_contact_email_domain'),
    )
    
    @validates('email')
    def validate_email(self, key, email):
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email
    
    def __repr__(self):
        return f"<Contact(id={self.id}, email='{self.email}', status='{self.email_status}')>"


class EmailCampaign(Base):
    """Represents an email marketing campaign."""
    __tablename__ = 'email_campaigns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Campaign settings
    template_name = Column(String(255), nullable=False)
    subject_template = Column(Text, nullable=False)
    from_address = Column(String(255), nullable=False)
    from_name = Column(String(255))
    
    # Status and timing
    status = Column(String(50), default='draft')  # draft, scheduled, running, completed, paused
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Statistics
    total_recipients = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_failed = Column(Integer, default=0)
    emails_bounced = Column(Integer, default=0)
    
    # Configuration
    send_rate_limit = Column(Integer, default=10)  # emails per minute
    target_domains = Column(JSON)  # List of target domains
    exclude_domains = Column(JSON)  # List of domains to exclude
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email_logs = relationship("EmailLog", back_populates="campaign")
    
    # Indexes
    __table_args__ = (
        Index('idx_campaign_status', 'status'),
        Index('idx_campaign_scheduled', 'scheduled_at'),
        Index('idx_campaign_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<EmailCampaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class EmailLog(Base):
    """Represents individual email send logs."""
    __tablename__ = 'email_logs'
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('email_campaigns.id'))
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    
    # Email details
    to_address = Column(String(255), nullable=False)
    from_address = Column(String(255), nullable=False)
    subject = Column(Text, nullable=False)
    
    # Status tracking
    status = Column(String(50), default='queued')  # queued, sent, failed, bounced, delivered
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    
    # Error information
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # External IDs
    message_id = Column(String(255))  # Gmail message ID
    thread_id = Column(String(255))   # Gmail thread ID
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("EmailCampaign", back_populates="email_logs")
    contact = relationship("Contact", back_populates="email_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_email_log_status', 'status'),
        Index('idx_email_log_sent', 'sent_at'),
        Index('idx_email_log_campaign', 'campaign_id'),
        Index('idx_email_log_contact', 'contact_id'),
        Index('idx_email_log_message_id', 'message_id'),
    )
    
    def __repr__(self):
        return f"<EmailLog(id={self.id}, to='{self.to_address}', status='{self.status}')>"


class AuditLog(Base):
    """Represents audit trail for compliance and debugging."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # crawl, email_send, data_export, etc.
    entity_type = Column(String(50))  # search_result, contact, email, etc.
    entity_id = Column(Integer)
    
    # User/system information
    user_agent = Column(String(500))
    ip_address = Column(String(45))
    
    # Action details
    details = Column(JSON)  # Additional action-specific data
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration = Column(Float)  # Action duration in seconds
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_action', 'action'),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_success', 'success'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', success={self.success})>"


# Utility functions for working with models

def create_crawl_session(session_name: str, keywords: List[str], config: Dict[str, Any] = None) -> CrawlSession:
    """Create a new crawl session."""
    return CrawlSession(
        session_name=session_name,
        keywords=keywords,
        config=config or {}
    )


def create_search_result(crawl_session_id: int, **kwargs) -> SearchResult:
    """Create a new search result."""
    return SearchResult(
        crawl_session_id=crawl_session_id,
        **kwargs
    )


def create_email_campaign(name: str, template_name: str, subject_template: str, 
                         from_address: str, **kwargs) -> EmailCampaign:
    """Create a new email campaign."""
    return EmailCampaign(
        name=name,
        template_name=template_name,
        subject_template=subject_template,
        from_address=from_address,
        **kwargs
    )


def log_audit_event(action: str, entity_type: str = None, entity_id: int = None,
                   details: Dict[str, Any] = None, success: bool = True,
                   error_message: str = None, **kwargs) -> AuditLog:
    """Create an audit log entry."""
    return AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        success=success,
        error_message=error_message,
        **kwargs
    )
