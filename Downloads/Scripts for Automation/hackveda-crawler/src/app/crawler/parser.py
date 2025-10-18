"""
Result parser for processing and normalizing crawled data.
Handles data cleaning, validation, and enrichment.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from datetime import datetime

from .google_serp import SearchResult
from .page_fetcher import PageContent


@dataclass
class ParsedResult:
    """Normalized and enriched search result."""
    # Original data
    title: str
    url: str
    snippet: str
    rank: int
    domain: str
    
    # Enriched data
    normalized_title: str
    normalized_snippet: str
    domain_info: Dict[str, Any]
    keywords: List[str]
    language: str
    
    # Metadata
    crawl_timestamp: datetime
    response_time: float
    source_keyword: str
    
    # Quality scores
    relevance_score: float
    quality_score: float
    
    # Additional metadata
    metadata: Dict[str, Any]


class ResultParser:
    """Handles parsing and normalization of crawl results."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common stop words for keyword extraction
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'
        }
        
        # Domain quality indicators
        self.quality_indicators = {
            'high': ['.edu', '.gov', '.org'],
            'medium': ['.com', '.net'],
            'low': ['.tk', '.ml', '.ga', '.cf']
        }
    
    def parse_search_results(self, results: List[SearchResult]) -> List[ParsedResult]:
        """Parse and normalize multiple search results."""
        parsed_results = []
        
        for result in results:
            try:
                parsed = self.parse_search_result(result)
                if parsed:
                    parsed_results.append(parsed)
            except Exception as e:
                self.logger.error(f"Error parsing result {result.url}: {e}")
        
        return parsed_results
    
    def parse_search_result(self, result: SearchResult) -> Optional[ParsedResult]:
        """Parse and normalize a single search result."""
        try:
            # Normalize text fields
            normalized_title = self._normalize_text(result.title)
            normalized_snippet = self._normalize_text(result.snippet)
            
            # Extract keywords
            keywords = self._extract_keywords(f"{result.title} {result.snippet}")
            
            # Analyze domain
            domain_info = self._analyze_domain(result.domain)
            
            # Detect language (simple heuristic)
            language = self._detect_language(f"{result.title} {result.snippet}")
            
            # Calculate quality scores
            relevance_score = self._calculate_relevance_score(result)
            quality_score = self._calculate_quality_score(result, domain_info)
            
            return ParsedResult(
                title=result.title,
                url=result.url,
                snippet=result.snippet,
                rank=result.rank,
                domain=result.domain,
                normalized_title=normalized_title,
                normalized_snippet=normalized_snippet,
                domain_info=domain_info,
                keywords=keywords,
                language=language,
                crawl_timestamp=result.crawl_timestamp,
                response_time=result.response_time,
                source_keyword=result.result_metadata.get('keyword', ''),
                relevance_score=relevance_score,
                quality_score=quality_score,
                result_metadata=result.result_metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing search result: {e}")
            return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text by cleaning and standardizing."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-.,!?()"]', '', text)
        
        # Remove multiple punctuation
        text = re.sub(r'[.]{2,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text.strip()
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text."""
        if not text:
            return []
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and short words
        keywords = [
            word for word in words 
            if word not in self.stop_words and len(word) > 2
        ]
        
        # Count frequency and get top keywords
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:max_keywords]]
    
    def _analyze_domain(self, domain: str) -> Dict[str, Any]:
        """Analyze domain for quality indicators."""
        if not domain:
            return {}
        
        domain_lower = domain.lower()
        
        # Determine domain quality
        quality = 'medium'  # default
        for quality_level, extensions in self.quality_indicators.items():
            if any(domain_lower.endswith(ext) for ext in extensions):
                quality = quality_level
                break
        
        # Extract TLD
        tld = domain.split('.')[-1] if '.' in domain else ''
        
        # Check if it's a subdomain
        is_subdomain = len(domain.split('.')) > 2
        
        # Extract main domain (without subdomain)
        main_domain = '.'.join(domain.split('.')[-2:]) if '.' in domain else domain
        
        return {
            'quality': quality,
            'tld': tld,
            'is_subdomain': is_subdomain,
            'main_domain': main_domain,
            'length': len(domain),
            'has_numbers': bool(re.search(r'\d', domain)),
            'has_hyphens': '-' in domain
        }
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection (English by default)."""
        if not text:
            return 'unknown'
        
        # Simple heuristic: check for common English words
        english_indicators = ['the', 'and', 'or', 'is', 'are', 'was', 'were', 'a', 'an']
        text_lower = text.lower()
        
        english_count = sum(1 for word in english_indicators if word in text_lower)
        
        if english_count >= 2:
            return 'en'
        
        return 'unknown'
    
    def _calculate_relevance_score(self, result: SearchResult) -> float:
        """Calculate relevance score based on rank and content quality."""
        # Base score from rank (higher rank = lower score)
        rank_score = max(0, 1.0 - (result.rank - 1) * 0.1)
        
        # Content quality indicators
        content_score = 0.5  # base score
        
        # Title length (not too short, not too long)
        title_len = len(result.title)
        if 30 <= title_len <= 100:
            content_score += 0.2
        
        # Snippet quality
        if result.snippet and len(result.snippet) > 50:
            content_score += 0.2
        
        # Domain quality
        if not any(spam_indicator in result.domain.lower() 
                  for spam_indicator in ['spam', 'ads', 'click', 'buy']):
            content_score += 0.1
        
        return min(1.0, (rank_score + content_score) / 2)
    
    def _calculate_quality_score(self, result: SearchResult, domain_info: Dict[str, Any]) -> float:
        """Calculate overall quality score."""
        score = 0.5  # base score
        
        # Domain quality
        domain_quality = domain_info.get('quality', 'medium')
        if domain_quality == 'high':
            score += 0.3
        elif domain_quality == 'medium':
            score += 0.1
        
        # Response time (faster is better)
        if result.response_time < 2.0:
            score += 0.1
        elif result.response_time > 5.0:
            score -= 0.1
        
        # Content indicators
        if result.title and len(result.title) > 10:
            score += 0.1
        
        if result.snippet and len(result.snippet) > 30:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def deduplicate_results(self, results: List[ParsedResult]) -> List[ParsedResult]:
        """Remove duplicate results based on URL and title similarity."""
        seen_urls = set()
        seen_titles = set()
        unique_results = []
        
        for result in results:
            # Check URL duplicates
            if result.url in seen_urls:
                continue
            
            # Check title similarity (simple approach)
            title_key = self._normalize_text(result.title).lower()
            if title_key in seen_titles:
                continue
            
            seen_urls.add(result.url)
            seen_titles.add(title_key)
            unique_results.append(result)
        
        self.logger.info(f"Deduplicated {len(results)} results to {len(unique_results)} unique results")
        return unique_results
    
    def filter_results(self, results: List[ParsedResult], 
                      min_quality_score: float = 0.3,
                      min_relevance_score: float = 0.2) -> List[ParsedResult]:
        """Filter results based on quality and relevance scores."""
        filtered_results = [
            result for result in results
            if result.quality_score >= min_quality_score 
            and result.relevance_score >= min_relevance_score
        ]
        
        self.logger.info(f"Filtered {len(results)} results to {len(filtered_results)} high-quality results")
        return filtered_results
    
    def sort_results(self, results: List[ParsedResult], 
                    sort_by: str = 'relevance') -> List[ParsedResult]:
        """Sort results by specified criteria."""
        if sort_by == 'relevance':
            return sorted(results, key=lambda x: x.relevance_score, reverse=True)
        elif sort_by == 'quality':
            return sorted(results, key=lambda x: x.quality_score, reverse=True)
        elif sort_by == 'rank':
            return sorted(results, key=lambda x: x.rank)
        elif sort_by == 'domain':
            return sorted(results, key=lambda x: x.domain)
        else:
            return results
    
    def to_dict(self, result: ParsedResult) -> Dict[str, Any]:
        """Convert ParsedResult to dictionary."""
        return asdict(result)
    
    def to_csv_row(self, result: ParsedResult) -> Dict[str, Any]:
        """Convert ParsedResult to CSV-friendly dictionary."""
        return {
            'title': result.title,
            'url': result.url,
            'snippet': result.snippet,
            'domain': result.domain,
            'rank': result.rank,
            'relevance_score': result.relevance_score,
            'quality_score': result.quality_score,
            'keywords': ', '.join(result.keywords),
            'language': result.language,
            'crawl_timestamp': result.crawl_timestamp.isoformat(),
            'source_keyword': result.source_keyword,
            'response_time': result.response_time
        }
