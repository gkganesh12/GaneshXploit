"""
Repository classes for database operations in HackVeda Crawler.
Provides clean interface for database CRUD operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from .models import (
    CrawlSession, SearchResult, Domain, Contact, 
    EmailCampaign, EmailLog, AuditLog
)


class BaseRepository:
    """Base repository with common operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, **kwargs):
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()  # Get ID without committing
        return instance
    
    def get_by_id(self, id: int):
        """Get record by ID."""
        return self.session.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, limit: int = None):
        """Get all records."""
        query = self.session.query(self.model)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update(self, id: int, **kwargs):
        """Update record by ID."""
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.session.flush()
        return instance
    
    def delete(self, id: int):
        """Delete record by ID."""
        instance = self.get_by_id(id)
        if instance:
            self.session.delete(instance)
            self.session.flush()
        return instance


class CrawlSessionRepository(BaseRepository):
    """Repository for crawl sessions."""
    
    model = CrawlSession
    
    def get_recent(self, limit: int = 20) -> List[CrawlSession]:
        """Get recent crawl sessions."""
        return self.session.query(CrawlSession)\
            .order_by(desc(CrawlSession.start_time))\
            .limit(limit)\
            .all()
    
    def get_by_status(self, status: str) -> List[CrawlSession]:
        """Get sessions by status."""
        return self.session.query(CrawlSession)\
            .filter(CrawlSession.status == status)\
            .all()
    
    def update_status(self, session_id: int, status: str, error_message: str = None):
        """Update session status."""
        session = self.get_by_id(session_id)
        if session:
            session.status = status
            if error_message:
                session.error_message = error_message
            if status == 'completed':
                session.end_time = datetime.utcnow()
            self.session.flush()
        return session


class SearchResultRepository(BaseRepository):
    """Repository for search results."""
    
    model = SearchResult
    
    def get_by_session(self, session_id: int) -> List[SearchResult]:
        """Get results by crawl session."""
        return self.session.query(SearchResult)\
            .filter(SearchResult.crawl_session_id == session_id)\
            .order_by(SearchResult.rank)\
            .all()
    
    def get_by_domain(self, domain: str) -> List[SearchResult]:
        """Get results by domain."""
        return self.session.query(SearchResult)\
            .filter(SearchResult.domain == domain)\
            .all()
    
    def get_by_keyword(self, keyword: str) -> List[SearchResult]:
        """Get results by source keyword."""
        return self.session.query(SearchResult)\
            .filter(SearchResult.source_keyword == keyword)\
            .all()
    
    def get_recent(self, limit: int = 100) -> List[SearchResult]:
        """Get recent search results."""
        return self.session.query(SearchResult)\
            .order_by(desc(SearchResult.crawl_timestamp))\
            .limit(limit)\
            .all()


class DomainRepository(BaseRepository):
    """Repository for domains."""
    
    model = Domain
    
    def get_by_domain(self, domain: str) -> Optional[Domain]:
        """Get domain by name."""
        return self.session.query(Domain)\
            .filter(Domain.domain == domain)\
            .first()
    
    def get_or_create(self, domain: str, **kwargs) -> Domain:
        """Get existing domain or create new one."""
        existing = self.get_by_domain(domain)
        if existing:
            return existing
        
        return self.create(domain=domain, **kwargs)
    
    def get_with_contacts(self) -> List[Domain]:
        """Get domains that have contact information."""
        return self.session.query(Domain)\
            .filter(Domain.has_contact_info == True)\
            .all()


class ContactRepository(BaseRepository):
    """Repository for contacts."""
    
    model = Contact
    
    def get_by_email(self, email: str) -> Optional[Contact]:
        """Get contact by email."""
        return self.session.query(Contact)\
            .filter(Contact.email == email)\
            .first()
    
    def get_by_domain(self, domain: str) -> List[Contact]:
        """Get contacts by domain."""
        return self.session.query(Contact)\
            .filter(Contact.domain == domain)\
            .all()
    
    def get_verified(self) -> List[Contact]:
        """Get verified contacts."""
        return self.session.query(Contact)\
            .filter(Contact.is_verified == True)\
            .all()
    
    def search_by_name(self, name: str) -> List[Contact]:
        """Search contacts by name."""
        return self.session.query(Contact)\
            .filter(Contact.name.ilike(f'%{name}%'))\
            .all()


class EmailCampaignRepository(BaseRepository):
    """Repository for email campaigns."""
    
    model = EmailCampaign
    
    def get_active(self) -> List[EmailCampaign]:
        """Get active campaigns."""
        return self.session.query(EmailCampaign)\
            .filter(EmailCampaign.status == 'active')\
            .all()
    
    def get_by_status(self, status: str) -> List[EmailCampaign]:
        """Get campaigns by status."""
        return self.session.query(EmailCampaign)\
            .filter(EmailCampaign.status == status)\
            .all()
    
    def get_recent(self, limit: int = 20) -> List[EmailCampaign]:
        """Get recent campaigns."""
        return self.session.query(EmailCampaign)\
            .order_by(desc(EmailCampaign.created_at))\
            .limit(limit)\
            .all()
    
    def update_stats(self, campaign_id: int):
        """Update campaign statistics."""
        campaign = self.get_by_id(campaign_id)
        if campaign:
            # Count email logs for this campaign
            stats = self.session.query(
                EmailLog.status,
                func.count(EmailLog.id).label('count')
            ).filter(
                EmailLog.campaign_id == campaign_id
            ).group_by(EmailLog.status).all()
            
            # Update campaign stats
            total_sent = sum(stat.count for stat in stats)
            campaign.total_sent = total_sent
            
            # Update other stats based on email log statuses
            for stat in stats:
                if stat.status == 'delivered':
                    campaign.delivered = stat.count
                elif stat.status == 'failed':
                    campaign.failed = stat.count
                elif stat.status == 'bounced':
                    campaign.bounced = stat.count
            
            self.session.flush()
        return campaign


class EmailLogRepository(BaseRepository):
    """Repository for email logs."""
    
    model = EmailLog
    
    def get_by_campaign(self, campaign_id: int) -> List[EmailLog]:
        """Get logs by campaign."""
        return self.session.query(EmailLog)\
            .filter(EmailLog.campaign_id == campaign_id)\
            .order_by(desc(EmailLog.sent_at))\
            .all()
    
    def get_by_status(self, status: str) -> List[EmailLog]:
        """Get logs by status."""
        return self.session.query(EmailLog)\
            .filter(EmailLog.status == status)\
            .all()
    
    def get_recent(self, limit: int = 100) -> List[EmailLog]:
        """Get recent email logs."""
        return self.session.query(EmailLog)\
            .order_by(desc(EmailLog.sent_at))\
            .limit(limit)\
            .all()
    
    def get_failed(self) -> List[EmailLog]:
        """Get failed email logs."""
        return self.session.query(EmailLog)\
            .filter(EmailLog.status.in_(['failed', 'bounced']))\
            .all()
    
    def update_status(self, log_id: int, status: str, error_message: str = None):
        """Update email log status."""
        log = self.get_by_id(log_id)
        if log:
            log.status = status
            if error_message:
                log.error_message = error_message
            if status in ['delivered', 'failed', 'bounced']:
                log.delivered_at = datetime.utcnow()
            self.session.flush()
        return log


class AuditLogRepository(BaseRepository):
    """Repository for audit logs."""
    
    model = AuditLog
    
    def get_by_action(self, action: str) -> List[AuditLog]:
        """Get logs by action."""
        return self.session.query(AuditLog)\
            .filter(AuditLog.action == action)\
            .order_by(desc(AuditLog.timestamp))\
            .all()
    
    def get_by_user(self, user_id: str) -> List[AuditLog]:
        """Get logs by user."""
        return self.session.query(AuditLog)\
            .filter(AuditLog.user_id == user_id)\
            .order_by(desc(AuditLog.timestamp))\
            .all()
    
    def get_recent(self, limit: int = 100) -> List[AuditLog]:
        """Get recent audit logs."""
        return self.session.query(AuditLog)\
            .order_by(desc(AuditLog.timestamp))\
            .limit(limit)\
            .all()
    
    def log_action(self, action: str, user_id: str = None, details: Dict[str, Any] = None):
        """Log an action."""
        return self.create(
            action=action,
            user_id=user_id,
            details=details,
            timestamp=datetime.utcnow()
        )
