"""
Tests for crawler module.
"""

import pytest
import responses
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.crawler.google_serp import GoogleSERPCrawler, SearchResult, RobotsTxtChecker, RateLimiter
from app.crawler.page_fetcher import PageFetcher, PageContent
from app.crawler.parser import ResultParser, ParsedResult


class TestGoogleSERPCrawler:
    """Test Google SERP crawler functionality."""
    
    def test_crawler_initialization(self, test_config):
        """Test crawler initialization."""
        crawler = GoogleSERPCrawler(test_config)
        
        assert crawler.config == test_config
        assert crawler.rate_limiter is not None
        assert crawler.session is not None
    
    @responses.activate
    def test_crawl_keyword_success(self, test_config, mock_google_search_response):
        """Test successful keyword crawling."""
        # Mock Google search response
        responses.add(
            responses.GET,
            'https://www.google.com/search',
            html=mock_google_search_response,
            status=200
        )
        
        crawler = GoogleSERPCrawler(test_config)
        results = crawler.crawl_keyword('test query', max_results=2)
        
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title == "Test Result 1"
        assert results[0].url == "https://example.com/1"
        assert results[0].rank == 1
    
    @responses.activate
    def test_crawl_keywords_multiple(self, test_config, mock_google_search_response):
        """Test crawling multiple keywords."""
        # Mock multiple responses
        responses.add(
            responses.GET,
            'https://www.google.com/search',
            html=mock_google_search_response,
            status=200
        )
        
        crawler = GoogleSERPCrawler(test_config)
        keywords = ['test query 1', 'test query 2']
        results = crawler.crawl_keywords(keywords, max_results=2)
        
        # Should get results from both keywords
        assert len(results) >= 2
        
        # Check that results contain both keywords in metadata
        keywords_found = set()
        for result in results:
            if 'keyword' in result.metadata:
                keywords_found.add(result.metadata['keyword'])
        
        assert len(keywords_found) <= len(keywords)
    
    def test_deduplicate_results(self, test_config, sample_search_results):
        """Test result deduplication."""
        crawler = GoogleSERPCrawler(test_config)
        
        # Add duplicate result
        duplicate_result = SearchResult(
            title="Duplicate Title",
            url="https://example.com/1",  # Same URL as first result
            snippet="Different snippet",
            rank=3,
            domain="example.com",
            crawl_timestamp=datetime.now(),
            response_time=1.0,
            metadata={'keyword': 'test'}
        )
        
        results_with_duplicates = sample_search_results + [duplicate_result]
        unique_results = crawler.deduplicate_results(results_with_duplicates)
        
        # Should remove the duplicate URL
        assert len(unique_results) == len(sample_search_results)
        urls = [r.url for r in unique_results]
        assert len(set(urls)) == len(urls)  # All URLs should be unique
    
    def test_validate_result(self, test_config):
        """Test result validation."""
        crawler = GoogleSERPCrawler(test_config)
        
        # Valid result
        valid_result = SearchResult(
            title="Valid Title",
            url="https://example.com/valid",
            snippet="Valid snippet",
            rank=1,
            domain="example.com",
            crawl_timestamp=datetime.now(),
            response_time=1.0,
            metadata={}
        )
        
        assert crawler.validate_result(valid_result) is True
        
        # Invalid result (no title)
        invalid_result = SearchResult(
            title="",
            url="https://example.com/invalid",
            snippet="Invalid snippet",
            rank=1,
            domain="example.com",
            crawl_timestamp=datetime.now(),
            response_time=1.0,
            metadata={}
        )
        
        assert crawler.validate_result(invalid_result) is False


class TestRobotsTxtChecker:
    """Test robots.txt compliance checker."""
    
    @responses.activate
    def test_can_fetch_allowed(self):
        """Test URL allowed by robots.txt."""
        robots_content = """
        User-agent: *
        Allow: /
        Disallow: /private/
        """
        
        responses.add(
            responses.GET,
            'https://example.com/robots.txt',
            body=robots_content,
            status=200
        )
        
        checker = RobotsTxtChecker()
        assert checker.can_fetch('https://example.com/public', 'TestBot/1.0') is True
    
    @responses.activate
    def test_can_fetch_disallowed(self):
        """Test URL disallowed by robots.txt."""
        robots_content = """
        User-agent: *
        Allow: /
        Disallow: /private/
        """
        
        responses.add(
            responses.GET,
            'https://example.com/robots.txt',
            body=robots_content,
            status=200
        )
        
        checker = RobotsTxtChecker()
        assert checker.can_fetch('https://example.com/private/secret', 'TestBot/1.0') is False
    
    @responses.activate
    def test_can_fetch_no_robots_txt(self):
        """Test behavior when robots.txt doesn't exist."""
        responses.add(
            responses.GET,
            'https://example.com/robots.txt',
            status=404
        )
        
        checker = RobotsTxtChecker()
        # Should allow when robots.txt is not found
        assert checker.can_fetch('https://example.com/anything', 'TestBot/1.0') is True


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(delay_min=1, delay_max=2)
        
        assert limiter.delay_min == 1
        assert limiter.delay_max == 2
        assert limiter.last_request_time == 0
    
    def test_wait_timing(self):
        """Test wait timing calculation."""
        limiter = RateLimiter(delay_min=0.1, delay_max=0.2)
        
        import time
        start_time = time.time()
        limiter.wait()
        end_time = time.time()
        
        # Should wait at least delay_min
        elapsed = end_time - start_time
        assert elapsed >= 0.1


class TestPageFetcher:
    """Test page fetching functionality."""
    
    def test_page_fetcher_initialization(self, test_config):
        """Test page fetcher initialization."""
        fetcher = PageFetcher(test_config)
        
        assert fetcher.config == test_config
        assert fetcher.session is not None
    
    @responses.activate
    def test_fetch_page_success(self, test_config, sample_html_content):
        """Test successful page fetching."""
        responses.add(
            responses.GET,
            'https://example.com/test',
            body=sample_html_content,
            status=200,
            headers={'content-type': 'text/html'}
        )
        
        fetcher = PageFetcher(test_config)
        page_content = fetcher.fetch_page('https://example.com/test')
        
        assert page_content is not None
        assert isinstance(page_content, PageContent)
        assert page_content.url == 'https://example.com/test'
        assert page_content.status_code == 200
        assert 'Test Page' in page_content.title
        assert 'Welcome to Test Site' in page_content.content
    
    @responses.activate
    def test_fetch_page_404(self, test_config):
        """Test fetching non-existent page."""
        responses.add(
            responses.GET,
            'https://example.com/notfound',
            status=404
        )
        
        fetcher = PageFetcher(test_config)
        page_content = fetcher.fetch_page('https://example.com/notfound')
        
        # Should return None for 404
        assert page_content is None
    
    def test_is_valid_url(self, test_config):
        """Test URL validation."""
        fetcher = PageFetcher(test_config)
        
        # Valid URLs
        assert fetcher.is_valid_url('https://example.com') is True
        assert fetcher.is_valid_url('http://test.org/path') is True
        
        # Invalid URLs
        assert fetcher.is_valid_url('not-a-url') is False
        assert fetcher.is_valid_url('') is False
        assert fetcher.is_valid_url('ftp://example.com') is False
    
    def test_get_base_url(self, test_config):
        """Test base URL extraction."""
        fetcher = PageFetcher(test_config)
        
        assert fetcher.get_base_url('https://example.com/path/page') == 'https://example.com'
        assert fetcher.get_base_url('http://test.org:8080/') == 'http://test.org:8080'


class TestResultParser:
    """Test result parsing functionality."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = ResultParser()
        
        assert parser.stop_words is not None
        assert len(parser.stop_words) > 0
        assert parser.quality_indicators is not None
    
    def test_normalize_text(self):
        """Test text normalization."""
        parser = ResultParser()
        
        # Test basic normalization
        text = "  This   is    a   test!  "
        normalized = parser._normalize_text(text)
        assert normalized == "This is a test!"
        
        # Test special character removal
        text = "Test@#$%^&*()text"
        normalized = parser._normalize_text(text)
        assert normalized == "Testtext"
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        parser = ResultParser()
        
        text = "This is a test document about machine learning and artificial intelligence"
        keywords = parser._extract_keywords(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should not contain stop words
        assert 'this' not in keywords
        assert 'is' not in keywords
        assert 'a' not in keywords
        # Should contain meaningful words
        assert any(word in ['machine', 'learning', 'artificial', 'intelligence'] for word in keywords)
    
    def test_analyze_domain(self):
        """Test domain analysis."""
        parser = ResultParser()
        
        # Test .com domain
        domain_info = parser._analyze_domain('example.com')
        assert domain_info['quality'] == 'medium'
        assert domain_info['tld'] == 'com'
        assert domain_info['is_subdomain'] is False
        assert domain_info['main_domain'] == 'example.com'
        
        # Test .edu domain (high quality)
        domain_info = parser._analyze_domain('university.edu')
        assert domain_info['quality'] == 'high'
        assert domain_info['tld'] == 'edu'
        
        # Test subdomain
        domain_info = parser._analyze_domain('blog.example.com')
        assert domain_info['is_subdomain'] is True
        assert domain_info['main_domain'] == 'example.com'
    
    def test_detect_language(self):
        """Test language detection."""
        parser = ResultParser()
        
        # English text
        english_text = "This is an English text with common English words"
        assert parser._detect_language(english_text) == 'en'
        
        # Non-English text (should return unknown)
        non_english_text = "Esto es un texto en español"
        assert parser._detect_language(non_english_text) == 'unknown'
        
        # Empty text
        assert parser._detect_language('') == 'unknown'
    
    def test_parse_search_result(self, sample_search_results):
        """Test parsing individual search result."""
        parser = ResultParser()
        
        result = sample_search_results[0]
        parsed = parser.parse_search_result(result)
        
        assert isinstance(parsed, ParsedResult)
        assert parsed.title == result.title
        assert parsed.url == result.url
        assert parsed.domain == result.domain
        assert parsed.normalized_title is not None
        assert parsed.keywords is not None
        assert isinstance(parsed.keywords, list)
        assert parsed.relevance_score >= 0.0
        assert parsed.quality_score >= 0.0
    
    def test_deduplicate_results(self, sample_search_results):
        """Test result deduplication."""
        parser = ResultParser()
        
        # Convert to ParsedResult objects
        parsed_results = [parser.parse_search_result(r) for r in sample_search_results]
        
        # Add duplicate
        duplicate = parser.parse_search_result(sample_search_results[0])
        parsed_with_duplicate = parsed_results + [duplicate]
        
        unique_results = parser.deduplicate_results(parsed_with_duplicate)
        
        # Should remove duplicate
        assert len(unique_results) == len(parsed_results)
    
    def test_filter_results(self, sample_search_results):
        """Test result filtering."""
        parser = ResultParser()
        
        parsed_results = [parser.parse_search_result(r) for r in sample_search_results]
        
        # Filter with high thresholds (should return fewer results)
        filtered = parser.filter_results(parsed_results, min_quality_score=0.9, min_relevance_score=0.9)
        assert len(filtered) <= len(parsed_results)
        
        # All filtered results should meet criteria
        for result in filtered:
            assert result.quality_score >= 0.9
            assert result.relevance_score >= 0.9
    
    def test_sort_results(self, sample_search_results):
        """Test result sorting."""
        parser = ResultParser()
        
        parsed_results = [parser.parse_search_result(r) for r in sample_search_results]
        
        # Sort by relevance (descending)
        sorted_by_relevance = parser.sort_results(parsed_results, sort_by='relevance')
        relevance_scores = [r.relevance_score for r in sorted_by_relevance]
        assert relevance_scores == sorted(relevance_scores, reverse=True)
        
        # Sort by rank (ascending)
        sorted_by_rank = parser.sort_results(parsed_results, sort_by='rank')
        ranks = [r.rank for r in sorted_by_rank]
        assert ranks == sorted(ranks)
    
    def test_to_csv_row(self, sample_search_results):
        """Test CSV row conversion."""
        parser = ResultParser()
        
        result = sample_search_results[0]
        parsed = parser.parse_search_result(result)
        csv_row = parser.to_csv_row(parsed)
        
        assert isinstance(csv_row, dict)
        assert 'title' in csv_row
        assert 'url' in csv_row
        assert 'domain' in csv_row
        assert 'keywords' in csv_row
        assert isinstance(csv_row['keywords'], str)  # Should be comma-separated string
