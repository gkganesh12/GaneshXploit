"""
Google SERP (Search Engine Results Page) crawler.
Handles fetching and parsing Google search results with rate limiting and respect for robots.txt.
"""

import time
import random
import logging
import urllib.robotparser
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urljoin, urlparse
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from ..config import get_config


@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    url: str
    snippet: str
    rank: int
    domain: str
    crawl_timestamp: datetime
    response_time: float
    result_metadata: Dict[str, Any]


class RobotsTxtChecker:
    """Handles robots.txt compliance checking."""
    
    def __init__(self):
        self._cache: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.logger = logging.getLogger(__name__)
    
    def can_fetch(self, url: str, user_agent: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self._cache:
                robots_url = urljoin(base_url, '/robots.txt')
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self._cache[base_url] = rp
                except Exception as e:
                    self.logger.warning(f"Could not read robots.txt for {base_url}: {e}")
                    # If we can't read robots.txt, assume we can fetch
                    return True
            
            return self._cache[base_url].can_fetch(user_agent, url)
        
        except Exception as e:
            self.logger.error(f"Error checking robots.txt for {url}: {e}")
            # On error, be conservative and allow fetching
            return True


class RateLimiter:
    """Handles rate limiting for requests."""
    
    def __init__(self, delay_min: int = 2, delay_max: int = 6):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.last_request_time = 0
    
    def wait(self):
        """Wait for appropriate delay between requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # Calculate random delay
        delay = random.uniform(self.delay_min, self.delay_max)
        
        # If not enough time has passed, wait
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class GoogleSERPCrawler:
    """Main Google SERP crawler class."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter(
            self.config.crawler.delay_min,
            self.config.crawler.delay_max
        )
        self.robots_checker = RobotsTxtChecker() if self.config.crawler.respect_robots_txt else None
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.crawler.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def crawl_keywords(self, keywords: List[str], max_results: int = None) -> List[SearchResult]:
        """Crawl multiple keywords and return all results."""
        max_results = max_results or self.config.crawler.max_results
        all_results = []
        
        for keyword in keywords:
            self.logger.info(f"Crawling keyword: {keyword}")
            try:
                results = self.crawl_keyword(keyword, max_results)
                all_results.extend(results)
                self.logger.info(f"Found {len(results)} results for keyword: {keyword}")
            except Exception as e:
                self.logger.error(f"Error crawling keyword '{keyword}': {e}")
        
        return all_results
    
    def crawl_keyword(self, keyword: str, max_results: int = 10) -> List[SearchResult]:
        """Crawl a single keyword and return search results."""
        if self.config.crawler.mode == 'browser':
            return self._crawl_with_browser(keyword, max_results)
        else:
            return self._crawl_with_requests(keyword, max_results)
    
    def _crawl_with_requests(self, keyword: str, max_results: int) -> List[SearchResult]:
        """Crawl using requests + BeautifulSoup (light mode)."""
        results = []
        
        try:
            # Prepare search URL
            query = quote_plus(keyword)
            url = f"https://www.google.com/search?q={query}&num={max_results}"
            
            # Check robots.txt
            if self.robots_checker and not self.robots_checker.can_fetch(url, self.config.crawler.user_agent):
                self.logger.warning(f"Robots.txt disallows crawling: {url}")
                return results
            
            # Rate limiting
            self.rate_limiter.wait()
            
            # Make request
            start_time = time.time()
            response = self.session.get(
                url,
                timeout=self.config.crawler.timeout
            )
            response_time = time.time() - start_time
            
            response.raise_for_status()
            
            # Parse results
            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_google_results(soup, keyword, response_time)
            
            self.logger.info(f"Successfully crawled {len(results)} results for '{keyword}'")
            
        except requests.RequestException as e:
            self.logger.error(f"Request error for keyword '{keyword}': {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error crawling keyword '{keyword}': {e}")
        
        return results
    
    def _crawl_with_browser(self, keyword: str, max_results: int) -> List[SearchResult]:
        """Crawl using Playwright browser (browser mode)."""
        results = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set user agent
                page.set_extra_http_headers({
                    'User-Agent': self.config.crawler.user_agent
                })
                
                # Prepare search URL
                query = quote_plus(keyword)
                url = f"https://www.google.com/search?q={query}&num={max_results}"
                
                # Rate limiting
                self.rate_limiter.wait()
                
                # Navigate to search page
                start_time = time.time()
                page.goto(url, timeout=self.config.crawler.timeout * 1000)
                response_time = time.time() - start_time
                
                # Wait for results to load
                page.wait_for_selector('div.g', timeout=10000)
                
                # Get page content and parse
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                results = self._parse_google_results(soup, keyword, response_time)
                
                browser.close()
                
                self.logger.info(f"Successfully crawled {len(results)} results for '{keyword}' using browser")
        
        except Exception as e:
            self.logger.error(f"Browser crawling error for keyword '{keyword}': {e}")
        
        return results
    
    def _parse_google_results(self, soup: BeautifulSoup, keyword: str, response_time: float) -> List[SearchResult]:
        """Parse Google search results from BeautifulSoup object."""
        results = []
        
        # Find all result containers
        result_containers = soup.select('div.g')
        
        for rank, container in enumerate(result_containers, 1):
            try:
                # Extract title and URL
                title_elem = container.select_one('h3')
                link_elem = container.select_one('a')
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = link_elem.get('href', '')
                
                # Skip invalid URLs
                if not url or url.startswith('/search') or 'google.com' in url:
                    continue
                
                # Extract snippet
                snippet_elem = container.select_one('span[data-ved]') or container.select_one('.VwiC3b')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                
                # Extract domain
                domain = urlparse(url).netloc
                
                # Create result object
                result = SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    rank=rank,
                    domain=domain,
                    crawl_timestamp=datetime.now(),
                    response_time=response_time,
                    result_metadata={
                        'keyword': keyword,
                        'search_engine': 'google',
                        'crawl_mode': self.config.crawler.mode,
                    }
                )
                
                results.append(result)
                
            except Exception as e:
                self.logger.warning(f"Error parsing result container: {e}")
                continue
        
        return results
    
    def validate_result(self, result: SearchResult) -> bool:
        """Validate a search result."""
        if not result.title or not result.url:
            return False
        
        # Check if URL is valid
        try:
            parsed = urlparse(result.url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False
        
        return True
    
    def deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on URL."""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        self.logger.info(f"Deduplicated {len(results)} results to {len(unique_results)} unique results")
        return unique_results
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
