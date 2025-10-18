"""
Enrichment module for HackVeda Crawler.
Handles contact extraction, domain analysis, and data enrichment.
"""

from .contact_extractor import ContactExtractor, ContactInfo

__all__ = ['ContactExtractor', 'ContactInfo']
