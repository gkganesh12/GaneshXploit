"""
Contact extraction and enrichment for crawled pages.
Extracts email addresses, contact pages, and social media links.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

from bs4 import BeautifulSoup
from ..crawler.page_fetcher import PageFetcher, PageContent
from ..config import get_config


@dataclass
class ContactInfo:
    """Represents extracted contact information."""
    emails: List[str]
    contact_pages: List[str]
    social_links: Dict[str, str]  # platform -> url
    phone_numbers: List[str]
    addresses: List[str]
    confidence_score: float
    extraction_method: str
    source_urls: List[str]


class ContactExtractor:
    """Extracts contact information from web pages."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self.page_fetcher = PageFetcher(config)
        
        # Email regex patterns
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+\s*\[at\]\s*[A-Za-z0-9.-]+\s*\[dot\]\s*[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\s*\.\s*[A-Z|a-z]{2,}\b',
        ]
        
        # Phone number patterns
        self.phone_patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            r'\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}',
        ]
        
        # Common contact page paths
        self.contact_page_paths = [
            '/contact', '/contact-us', '/contact_us', '/contactus',
            '/about', '/about-us', '/about_us', '/aboutus',
            '/team', '/staff', '/people',
            '/support', '/help', '/feedback',
            '/info', '/information',
        ]
        
        # Social media patterns
        self.social_patterns = {
            'linkedin': r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9-]+',
            'twitter': r'https?://(?:www\.)?twitter\.com/[a-zA-Z0-9_]+',
            'facebook': r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9.]+',
            'instagram': r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+',
            'youtube': r'https?://(?:www\.)?youtube\.com/(?:channel/|user/|c/)[a-zA-Z0-9_-]+',
            'github': r'https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+',
        }
        
        # Spam/invalid email indicators
        self.spam_indicators = {
            'noreply', 'no-reply', 'donotreply', 'do-not-reply',
            'mailer-daemon', 'postmaster', 'webmaster',
            'example.com', 'test.com', 'localhost',
            'sentry.io', 'bugsnag.com'
        }
    
    def extract_contacts_from_domain(self, domain: str, max_pages: int = 3) -> ContactInfo:
        """Extract contact information from a domain."""
        base_url = f"https://{domain}" if not domain.startswith('http') else domain
        
        # Initialize contact info
        all_emails = set()
        all_contact_pages = set()
        all_social_links = {}
        all_phone_numbers = set()
        all_addresses = set()
        source_urls = []
        
        # Start with homepage
        urls_to_check = [base_url]
        
        # Add common contact pages
        for path in self.contact_page_paths:
            urls_to_check.append(urljoin(base_url, path))
        
        # Limit to max_pages
        urls_to_check = urls_to_check[:max_pages]
        
        total_confidence = 0
        pages_processed = 0
        
        for url in urls_to_check:
            try:
                self.logger.debug(f"Extracting contacts from: {url}")
                page_content = self.page_fetcher.fetch_page(url)
                
                if page_content and page_content.status_code == 200:
                    contact_info = self.extract_contacts_from_page(page_content)
                    
                    # Merge results
                    all_emails.update(contact_info.emails)
                    all_contact_pages.update(contact_info.contact_pages)
                    all_social_links.update(contact_info.social_links)
                    all_phone_numbers.update(contact_info.phone_numbers)
                    all_addresses.update(contact_info.addresses)
                    source_urls.append(url)
                    
                    total_confidence += contact_info.confidence_score
                    pages_processed += 1
                
            except Exception as e:
                self.logger.warning(f"Error extracting contacts from {url}: {e}")
        
        # Calculate overall confidence
        avg_confidence = total_confidence / pages_processed if pages_processed > 0 else 0
        
        # Filter and validate results
        validated_emails = self._validate_emails(list(all_emails))
        
        return ContactInfo(
            emails=validated_emails,
            contact_pages=list(all_contact_pages),
            social_links=all_social_links,
            phone_numbers=list(all_phone_numbers),
            addresses=list(all_addresses),
            confidence_score=avg_confidence,
            extraction_method='domain_crawl',
            source_urls=source_urls
        )
    
    def extract_contacts_from_page(self, page_content: PageContent) -> ContactInfo:
        """Extract contact information from a single page."""
        if not page_content or not page_content.html:
            return ContactInfo([], [], {}, [], [], 0.0, 'empty_page', [])
        
        soup = BeautifulSoup(page_content.html, 'html.parser')
        
        # Extract emails
        emails = self._extract_emails(page_content.content, soup)
        
        # Extract contact pages
        contact_pages = self._extract_contact_pages(soup, page_content.url)
        
        # Extract social links
        social_links = self._extract_social_links(soup)
        
        # Extract phone numbers
        phone_numbers = self._extract_phone_numbers(page_content.content)
        
        # Extract addresses (simple approach)
        addresses = self._extract_addresses(page_content.content)
        
        # Calculate confidence score
        confidence = self._calculate_confidence_score(
            emails, contact_pages, social_links, phone_numbers, page_content
        )
        
        return ContactInfo(
            emails=emails,
            contact_pages=contact_pages,
            social_links=social_links,
            phone_numbers=phone_numbers,
            addresses=addresses,
            confidence_score=confidence,
            extraction_method='page_analysis',
            source_urls=[page_content.url]
        )
    
    def _extract_emails(self, text: str, soup: BeautifulSoup) -> List[str]:
        """Extract email addresses from text and HTML."""
        emails = set()
        
        # Extract from text content
        for pattern in self.email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            emails.update(matches)
        
        # Extract from mailto links
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        for link in mailto_links:
            href = link.get('href', '')
            if href.startswith('mailto:'):
                email = href[7:].split('?')[0]  # Remove query parameters
                if '@' in email:
                    emails.add(email)
        
        # Clean and validate emails
        cleaned_emails = []
        for email in emails:
            email = email.strip().lower()
            if self._is_valid_email(email):
                cleaned_emails.append(email)
        
        return list(set(cleaned_emails))
    
    def _extract_contact_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract contact page URLs."""
        contact_pages = set()
        
        # Find links that might lead to contact pages
        contact_keywords = [
            'contact', 'about', 'team', 'support', 'help',
            'info', 'reach', 'touch', 'connect'
        ]
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            
            # Check if link or text contains contact keywords
            if any(keyword in href or keyword in text for keyword in contact_keywords):
                full_url = urljoin(base_url, link['href'])
                contact_pages.add(full_url)
        
        return list(contact_pages)
    
    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links."""
        social_links = {}
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            
            # Check against social media patterns
            for platform, pattern in self.social_patterns.items():
                if re.match(pattern, href, re.IGNORECASE):
                    social_links[platform] = href
                    break
        
        return social_links
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text."""
        phone_numbers = set()
        
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            phone_numbers.update(matches)
        
        # Clean phone numbers
        cleaned_phones = []
        for phone in phone_numbers:
            # Remove common formatting
            cleaned = re.sub(r'[^\d+]', '', phone)
            if len(cleaned) >= 10:  # Minimum valid phone length
                cleaned_phones.append(phone.strip())
        
        return list(set(cleaned_phones))
    
    def _extract_addresses(self, text: str) -> List[str]:
        """Extract physical addresses (simple approach)."""
        addresses = []
        
        # Simple address pattern (US-focused)
        address_pattern = r'\d+\s+[A-Za-z0-9\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl)\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?'
        
        matches = re.findall(address_pattern, text, re.IGNORECASE)
        addresses.extend(matches)
        
        return list(set(addresses))
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address."""
        if not email or '@' not in email:
            return False
        
        # Check against spam indicators
        email_lower = email.lower()
        if any(indicator in email_lower for indicator in self.spam_indicators):
            return False
        
        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
        
        return True
    
    def _validate_emails(self, emails: List[str]) -> List[str]:
        """Validate and filter email list."""
        validated = []
        
        for email in emails:
            if self._is_valid_email(email):
                validated.append(email)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_emails = []
        for email in validated:
            if email not in seen:
                seen.add(email)
                unique_emails.append(email)
        
        return unique_emails
    
    def _calculate_confidence_score(self, emails: List[str], contact_pages: List[str],
                                  social_links: Dict[str, str], phone_numbers: List[str],
                                  page_content: PageContent) -> float:
        """Calculate confidence score for extracted contact information."""
        score = 0.0
        
        # Email score (most important)
        if emails:
            score += 0.4 * min(1.0, len(emails) / 3)  # Max score for 3+ emails
        
        # Contact pages score
        if contact_pages:
            score += 0.2 * min(1.0, len(contact_pages) / 2)
        
        # Social links score
        if social_links:
            score += 0.2 * min(1.0, len(social_links) / 3)
        
        # Phone numbers score
        if phone_numbers:
            score += 0.1 * min(1.0, len(phone_numbers) / 2)
        
        # Page quality indicators
        if page_content:
            # Check if it's a contact page
            url_lower = page_content.url.lower()
            if any(keyword in url_lower for keyword in ['contact', 'about', 'team']):
                score += 0.1
            
            # Check content quality
            if len(page_content.content) > 500:
                score += 0.05
        
        return min(1.0, score)
    
    def enrich_domain_info(self, domain: str) -> Dict[str, Any]:
        """Enrich domain with additional metadata."""
        enrichment_data = {
            'domain': domain,
            'tld': domain.split('.')[-1] if '.' in domain else '',
            'is_subdomain': len(domain.split('.')) > 2,
            'main_domain': '.'.join(domain.split('.')[-2:]) if '.' in domain else domain,
        }
        
        # Analyze domain characteristics
        domain_lower = domain.lower()
        
        # Quality indicators
        quality_score = 0.5  # Base score
        
        if any(tld in domain_lower for tld in ['.edu', '.gov', '.org']):
            quality_score += 0.3
        elif any(tld in domain_lower for tld in ['.com', '.net']):
            quality_score += 0.1
        
        # Check for spam indicators
        spam_indicators = ['ads', 'click', 'buy', 'cheap', 'free', 'win']
        if any(indicator in domain_lower for indicator in spam_indicators):
            quality_score -= 0.2
        
        enrichment_data['quality_score'] = max(0.0, min(1.0, quality_score))
        
        # Additional metadata
        enrichment_data['has_numbers'] = bool(re.search(r'\d', domain))
        enrichment_data['has_hyphens'] = '-' in domain
        enrichment_data['length'] = len(domain)
        
        return enrichment_data
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'page_fetcher'):
            self.page_fetcher.close()
