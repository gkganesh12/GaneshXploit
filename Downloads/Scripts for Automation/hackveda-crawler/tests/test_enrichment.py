"""
Tests for enrichment module.
"""

import pytest
import responses
from unittest.mock import Mock, patch, MagicMock

from app.enrichment.contact_extractor import ContactExtractor, ContactInfo
from app.crawler.page_fetcher import PageContent


class TestContactExtractor:
    """Test contact extraction functionality."""
    
    def test_contact_extractor_initialization(self, test_config):
        """Test contact extractor initialization."""
        extractor = ContactExtractor(test_config)
        
        assert extractor.config == test_config
        assert extractor.page_fetcher is not None
        assert len(extractor.email_patterns) > 0
        assert len(extractor.contact_page_paths) > 0
        assert len(extractor.social_patterns) > 0
    
    def test_extract_emails_from_text(self, test_config):
        """Test email extraction from text content."""
        extractor = ContactExtractor(test_config)
        
        text = """
        Contact us at info@example.com or support@testsite.org.
        You can also reach john.doe@company.net for sales inquiries.
        Invalid emails like @invalid.com or incomplete@ should be ignored.
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<html></html>', 'html.parser')
        
        emails = extractor._extract_emails(text, soup)
        
        assert 'info@example.com' in emails
        assert 'support@testsite.org' in emails
        assert 'john.doe@company.net' in emails
        assert '@invalid.com' not in emails
        assert 'incomplete@' not in emails
    
    def test_extract_emails_from_mailto_links(self, test_config, sample_html_content):
        """Test email extraction from mailto links."""
        extractor = ContactExtractor(test_config)
        
        html_with_mailto = """
        <html>
        <body>
            <a href="mailto:contact@example.com">Contact Us</a>
            <a href="mailto:sales@example.com?subject=Inquiry">Sales</a>
            <a href="mailto:noreply@example.com">No Reply</a>
        </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_with_mailto, 'html.parser')
        
        emails = extractor._extract_emails('', soup)
        
        assert 'contact@example.com' in emails
        assert 'sales@example.com' in emails
        # noreply emails should be filtered out by validation
        assert 'noreply@example.com' not in emails
    
    def test_extract_contact_pages(self, test_config, sample_html_content):
        """Test contact page URL extraction."""
        extractor = ContactExtractor(test_config)
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html_content, 'html.parser')
        
        contact_pages = extractor._extract_contact_pages(soup, 'https://example.com')
        
        # Should find contact and about links
        assert any('contact' in url.lower() for url in contact_pages)
        assert any('about' in url.lower() for url in contact_pages)
    
    def test_extract_social_links(self, test_config, sample_html_content):
        """Test social media link extraction."""
        extractor = ContactExtractor(test_config)
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html_content, 'html.parser')
        
        social_links = extractor._extract_social_links(soup)
        
        assert 'twitter' in social_links
        assert 'linkedin' in social_links
        assert 'https://twitter.com/example' in social_links.values()
        assert 'https://linkedin.com/company/example' in social_links.values()
    
    def test_extract_phone_numbers(self, test_config):
        """Test phone number extraction."""
        extractor = ContactExtractor(test_config)
        
        text = """
        Call us at +1 (234) 567-890 or 555-123-4567.
        International: +44 20 7946 0958
        Invalid: 123 (too short)
        """
        
        phone_numbers = extractor._extract_phone_numbers(text)
        
        assert len(phone_numbers) >= 2
        # Should find properly formatted phone numbers
        assert any('234' in phone for phone in phone_numbers)
        assert any('555' in phone for phone in phone_numbers)
    
    def test_is_valid_email(self, test_config):
        """Test email validation."""
        extractor = ContactExtractor(test_config)
        
        # Valid emails
        assert extractor._is_valid_email('user@example.com') is True
        assert extractor._is_valid_email('test.email+tag@domain.org') is True
        
        # Invalid emails
        assert extractor._is_valid_email('') is False
        assert extractor._is_valid_email('invalid-email') is False
        assert extractor._is_valid_email('@domain.com') is False
        assert extractor._is_valid_email('user@') is False
        
        # Spam emails (should be filtered out)
        assert extractor._is_valid_email('noreply@example.com') is False
        assert extractor._is_valid_email('no-reply@example.com') is False
        assert extractor._is_valid_email('donotreply@example.com') is False
    
    def test_validate_emails(self, test_config):
        """Test email list validation and deduplication."""
        extractor = ContactExtractor(test_config)
        
        emails = [
            'valid@example.com',
            'another@test.org',
            'noreply@spam.com',  # Should be filtered out
            'valid@example.com',  # Duplicate
            'invalid-email',      # Invalid format
            'good.email@domain.net'
        ]
        
        validated = extractor._validate_emails(emails)
        
        # Should contain only valid, unique emails
        assert 'valid@example.com' in validated
        assert 'another@test.org' in validated
        assert 'good.email@domain.net' in validated
        
        # Should not contain invalid or spam emails
        assert 'noreply@spam.com' not in validated
        assert 'invalid-email' not in validated
        
        # Should not have duplicates
        assert validated.count('valid@example.com') == 1
    
    @patch('app.enrichment.contact_extractor.PageFetcher')
    def test_extract_contacts_from_page(self, mock_page_fetcher, test_config, sample_html_content):
        """Test contact extraction from a single page."""
        extractor = ContactExtractor(test_config)
        
        # Create mock page content
        page_content = PageContent(
            url='https://example.com/contact',
            title='Contact Us - Example Site',
            content='Contact us at info@example.com or call +1-234-567-890',
            html=sample_html_content,
            status_code=200,
            response_time=1.5,
            headers={'content-type': 'text/html'},
            fetch_timestamp=None
        )
        
        contact_info = extractor.extract_contacts_from_page(page_content)
        
        assert isinstance(contact_info, ContactInfo)
        assert len(contact_info.emails) > 0
        assert len(contact_info.social_links) > 0
        assert contact_info.confidence_score > 0
        assert contact_info.extraction_method == 'page_analysis'
        assert contact_info.source_urls == [page_content.url]
    
    @patch('app.enrichment.contact_extractor.PageFetcher')
    def test_extract_contacts_from_domain(self, mock_page_fetcher_class, test_config, sample_html_content):
        """Test contact extraction from entire domain."""
        # Mock page fetcher
        mock_page_fetcher = Mock()
        mock_page_content = PageContent(
            url='https://example.com',
            title='Example Site',
            content='Contact us at info@example.com',
            html=sample_html_content,
            status_code=200,
            response_time=1.0,
            headers={'content-type': 'text/html'},
            fetch_timestamp=None
        )
        mock_page_fetcher.fetch_page.return_value = mock_page_content
        mock_page_fetcher_class.return_value = mock_page_fetcher
        
        extractor = ContactExtractor(test_config)
        extractor.page_fetcher = mock_page_fetcher
        
        contact_info = extractor.extract_contacts_from_domain('example.com', max_pages=2)
        
        assert isinstance(contact_info, ContactInfo)
        assert contact_info.extraction_method == 'domain_crawl'
        assert len(contact_info.source_urls) > 0
        
        # Should have called fetch_page multiple times
        assert mock_page_fetcher.fetch_page.call_count >= 1
    
    def test_calculate_confidence_score(self, test_config, sample_html_content):
        """Test confidence score calculation."""
        extractor = ContactExtractor(test_config)
        
        # Create mock page content
        page_content = PageContent(
            url='https://example.com/contact',
            title='Contact Us',
            content='Contact information page',
            html=sample_html_content,
            status_code=200,
            response_time=1.0,
            headers={},
            fetch_timestamp=None
        )
        
        # Test with various combinations
        emails = ['info@example.com', 'sales@example.com']
        contact_pages = ['/contact', '/about']
        social_links = {'twitter': 'https://twitter.com/example'}
        phone_numbers = ['+1-234-567-890']
        
        confidence = extractor._calculate_confidence_score(
            emails, contact_pages, social_links, phone_numbers, page_content
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0  # Should have some confidence with this data
    
    def test_enrich_domain_info(self, test_config):
        """Test domain information enrichment."""
        extractor = ContactExtractor(test_config)
        
        # Test various domain types
        test_cases = [
            ('example.com', 'medium'),
            ('university.edu', 'high'),
            ('government.gov', 'high'),
            ('nonprofit.org', 'high'),
            ('blog.example.com', 'medium'),  # subdomain
            ('spammy-ads-click.tk', 'low')   # low quality TLD
        ]
        
        for domain, expected_quality in test_cases:
            enrichment = extractor.enrich_domain_info(domain)
            
            assert enrichment['domain'] == domain
            assert 'quality_score' in enrichment
            assert 'tld' in enrichment
            assert 'is_subdomain' in enrichment
            assert 'main_domain' in enrichment
            
            # Check quality assessment
            if expected_quality == 'high':
                assert enrichment['quality_score'] > 0.7
            elif expected_quality == 'low':
                assert enrichment['quality_score'] < 0.4
    
    def test_extract_contacts_empty_page(self, test_config):
        """Test contact extraction from empty page."""
        extractor = ContactExtractor(test_config)
        
        empty_page = PageContent(
            url='https://example.com/empty',
            title='',
            content='',
            html='',
            status_code=200,
            response_time=1.0,
            headers={},
            fetch_timestamp=None
        )
        
        contact_info = extractor.extract_contacts_from_page(empty_page)
        
        assert isinstance(contact_info, ContactInfo)
        assert len(contact_info.emails) == 0
        assert len(contact_info.contact_pages) == 0
        assert len(contact_info.social_links) == 0
        assert contact_info.confidence_score == 0.0
    
    def test_extract_contacts_none_page(self, test_config):
        """Test contact extraction from None page content."""
        extractor = ContactExtractor(test_config)
        
        contact_info = extractor.extract_contacts_from_page(None)
        
        assert isinstance(contact_info, ContactInfo)
        assert len(contact_info.emails) == 0
        assert contact_info.extraction_method == 'empty_page'
        assert contact_info.confidence_score == 0.0
    
    def test_social_pattern_matching(self, test_config):
        """Test social media pattern matching."""
        extractor = ContactExtractor(test_config)
        
        html_with_social = """
        <html>
        <body>
            <a href="https://twitter.com/company_handle">Twitter</a>
            <a href="https://www.linkedin.com/company/company-name">LinkedIn</a>
            <a href="https://facebook.com/company.page">Facebook</a>
            <a href="https://instagram.com/company_insta">Instagram</a>
            <a href="https://github.com/company-repo">GitHub</a>
            <a href="https://youtube.com/channel/UC123456789">YouTube</a>
            <a href="https://not-social-media.com">Not Social</a>
        </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_with_social, 'html.parser')
        
        social_links = extractor._extract_social_links(soup)
        
        # Should find all major social media platforms
        assert 'twitter' in social_links
        assert 'linkedin' in social_links
        assert 'facebook' in social_links
        assert 'instagram' in social_links
        assert 'github' in social_links
        assert 'youtube' in social_links
        
        # Should not include non-social media links
        assert 'not-social-media.com' not in social_links.values()
    
    def test_phone_number_patterns(self, test_config):
        """Test various phone number format recognition."""
        extractor = ContactExtractor(test_config)
        
        text_with_phones = """
        US formats:
        +1 (555) 123-4567
        555-123-4567
        555.123.4567
        555 123 4567
        (555) 123-4567
        
        International:
        +44 20 7946 0958
        +33 1 42 86 83 26
        +81-3-1234-5678
        
        Invalid:
        123 (too short)
        abc-def-ghij (letters)
        """
        
        phone_numbers = extractor._extract_phone_numbers(text_with_phones)
        
        # Should find multiple valid phone numbers
        assert len(phone_numbers) >= 4
        
        # Should contain some expected patterns
        phone_str = ' '.join(phone_numbers)
        assert '555' in phone_str or '123' in phone_str
        
        # Should not contain invalid entries
        assert 'abc' not in phone_str
        assert not any(len(phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) < 10 
                      for phone in phone_numbers if phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '').isdigit())
    
    def test_contact_info_dataclass(self):
        """Test ContactInfo dataclass functionality."""
        contact_info = ContactInfo(
            emails=['test@example.com'],
            contact_pages=['/contact'],
            social_links={'twitter': 'https://twitter.com/test'},
            phone_numbers=['+1-555-123-4567'],
            addresses=['123 Main St, City, State 12345'],
            confidence_score=0.8,
            extraction_method='test',
            source_urls=['https://example.com']
        )
        
        assert len(contact_info.emails) == 1
        assert contact_info.emails[0] == 'test@example.com'
        assert contact_info.confidence_score == 0.8
        assert contact_info.extraction_method == 'test'
        assert isinstance(contact_info.social_links, dict)
        assert isinstance(contact_info.phone_numbers, list)
        assert isinstance(contact_info.addresses, list)
