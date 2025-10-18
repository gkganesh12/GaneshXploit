"""
Crawler module for HackVeda Crawler.
Handles Google SERP crawling, page fetching, and data parsing.
"""

from .google_serp import GoogleSERPCrawler
from .page_fetcher import PageFetcher
from .parser import ResultParser

__all__ = ['GoogleSERPCrawler', 'PageFetcher', 'ResultParser']
