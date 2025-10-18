"""
Demo Crawler for HackVeda - Generates sample data for testing
Since Google blocks automated crawling, this creates realistic demo data
"""

import random
import time
from datetime import datetime
from typing import List
from dataclasses import dataclass

from .google_serp import SearchResult


class DemoCrawler:
    """Demo crawler that generates realistic sample data."""
    
    def __init__(self, config=None):
        self.config = config
        
        # Sample data for demo
        self.sample_domains = [
            'github.com', 'stackoverflow.com', 'medium.com', 'dev.to',
            'hackernoon.com', 'freecodecamp.org', 'codepen.io', 'replit.com',
            'notion.so', 'trello.com', 'asana.com', 'slack.com',
            'discord.com', 'zoom.us', 'microsoft.com', 'google.com'
        ]
        
        self.sample_titles = [
            "Top 10 {keyword} Tools for 2024",
            "Best {keyword} Software Solutions",
            "Ultimate Guide to {keyword}",
            "How to Choose the Right {keyword}",
            "{keyword}: Complete Tutorial",
            "Free {keyword} Resources",
            "Professional {keyword} Platform",
            "{keyword} for Beginners",
            "Advanced {keyword} Techniques",
            "Open Source {keyword} Tools"
        ]
        
        self.sample_snippets = [
            "Discover the most powerful {keyword} solutions that can transform your workflow and boost productivity.",
            "Learn everything you need to know about {keyword} with our comprehensive guide and expert tips.",
            "Compare the top {keyword} tools and find the perfect solution for your business needs.",
            "Get started with {keyword} using our step-by-step tutorial and best practices.",
            "Explore free and premium {keyword} options that deliver exceptional results.",
            "Master {keyword} with proven strategies and real-world examples from industry experts.",
            "Find the best {keyword} software that fits your budget and requirements.",
            "Unlock the potential of {keyword} with these innovative tools and techniques."
        ]
    
    def crawl_keyword(self, keyword: str, max_results: int = 10) -> List[SearchResult]:
        """Generate demo search results for a keyword."""
        print(f"🎭 Demo Mode: Generating sample results for '{keyword}'...")
        
        results = []
        
        for i in range(min(max_results, 10)):  # Limit to 10 for demo
            # Simulate crawling delay
            time.sleep(random.uniform(0.5, 1.5))
            
            # Generate realistic data
            domain = random.choice(self.sample_domains)
            title = random.choice(self.sample_titles).format(keyword=keyword.title())
            snippet = random.choice(self.sample_snippets).format(keyword=keyword)
            
            result = SearchResult(
                title=title,
                url=f"https://{domain}/{keyword.replace(' ', '-').lower()}-{i+1}",
                snippet=snippet,
                rank=i + 1,
                domain=domain,
                crawl_timestamp=datetime.now(),
                response_time=random.uniform(0.2, 2.0),
                result_metadata={
                    'keyword': keyword,
                    'search_engine': 'google_demo',
                    'crawl_mode': 'demo',
                    'demo': True
                }
            )
            
            results.append(result)
            print(f"  ✅ Generated result {i+1}: {title[:50]}...")
        
        print(f"🎉 Demo crawl completed! Generated {len(results)} results for '{keyword}'")
        return results
    
    def crawl_keywords(self, keywords: List[str], max_results_per_keyword: int = 10) -> List[SearchResult]:
        """Crawl multiple keywords and return all results."""
        all_results = []
        
        for keyword in keywords:
            results = self.crawl_keyword(keyword, max_results_per_keyword)
            all_results.extend(results)
        
        return all_results
