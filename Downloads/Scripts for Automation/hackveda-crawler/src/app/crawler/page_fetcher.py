"""
Page fetcher for crawling individual web pages.
Handles fetching page content with proper error handling and rate limiting.
"""

import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from ..config import get_config


@dataclass
class PageContent:
    """Represents fetched page content."""
    url: str
    title: str
    content: str
    html: str
    status_code: int
    response_time: float
    headers: Dict[str, str]
    fetch_timestamp: datetime
    error: Optional[str] = None


class PageFetcher:
    """Handles fetching individual web pages."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        # Setup session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.crawler.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Rate limiting
        self.last_request_time = 0
    
    def fetch_page(self, url: str, retries: int = None) -> Optional[PageContent]:
        """Fetch a single web page with retries."""
        retries = retries or self.config.crawler.max_retries
        
        for attempt in range(retries + 1):
            try:
                # Rate limiting
                self._apply_rate_limit()
                
                # Make request
                start_time = time.time()
                response = self.session.get(
                    url,
                    timeout=self.config.crawler.timeout,
                    allow_redirects=True
                )
                response_time = time.time() - start_time
                
                # Parse content
                page_content = self._parse_page_content(response, url, response_time)
                
                if page_content:
                    self.logger.debug(f"Successfully fetched: {url}")
                    return page_content
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{retries + 1})")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error fetching {url} (attempt {attempt + 1}/{retries + 1})")
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request error fetching {url}: {e} (attempt {attempt + 1}/{retries + 1})")
            except Exception as e:
                self.logger.error(f"Unexpected error fetching {url}: {e}")
                break
            
            # Wait before retry
            if attempt < retries:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        # Return error result if all attempts failed
        return PageContent(
            url=url,
            title="",
            content="",
            html="",
            status_code=0,
            response_time=0,
            headers={},
            fetch_timestamp=datetime.now(),
            error="Failed to fetch after retries"
        )
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        min_delay = self.config.crawler.delay_min
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        
        self.last_request_time = time.time()
    
    def _parse_page_content(self, response: requests.Response, url: str, response_time: float) -> Optional[PageContent]:
        """Parse page content from HTTP response."""
        try:
            # Check status code
            if response.status_code >= 400:
                self.logger.warning(f"HTTP {response.status_code} for {url}")
                return None
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                self.logger.debug(f"Skipping non-HTML content: {url} ({content_type})")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract text content
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text content
            content = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = ' '.join(chunk for chunk in chunks if chunk)
            
            return PageContent(
                url=url,
                title=title,
                content=content,
                html=response.text,
                status_code=response.status_code,
                response_time=response_time,
                headers=dict(response.headers),
                fetch_timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing page content for {url}: {e}")
            return None
    
    def fetch_multiple_pages(self, urls: list, max_concurrent: int = 3) -> Dict[str, PageContent]:
        """Fetch multiple pages with limited concurrency."""
        results = {}
        
        # Simple sequential fetching for now
        # TODO: Implement proper async/concurrent fetching
        for url in urls:
            try:
                page_content = self.fetch_page(url)
                if page_content:
                    results[url] = page_content
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {e}")
        
        return results
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and fetchable."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def get_base_url(self, url: str) -> str:
        """Get base URL from a full URL."""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return url
    
    def resolve_relative_url(self, base_url: str, relative_url: str) -> str:
        """Resolve relative URL against base URL."""
        try:
            return urljoin(base_url, relative_url)
        except Exception:
            return relative_url
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
