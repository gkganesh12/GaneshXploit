"""
Email Report Generator for HackVeda Crawler
Creates beautiful HTML email reports from crawling results
"""

from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Template

class CrawlReportGenerator:
    """Generate beautiful email reports from crawl results."""
    
    def __init__(self):
        self.html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HackVeda Crawler Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 10px;
            min-width: 150px;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .results-section {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        .result-item {
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 20px;
            background: #f8f9fa;
            border-radius: 0 8px 8px 0;
            transition: transform 0.2s ease;
        }
        .result-item:hover {
            transform: translateX(5px);
        }
        .result-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        .result-title a {
            color: #667eea;
            text-decoration: none;
        }
        .result-title a:hover {
            text-decoration: underline;
        }
        .result-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        .result-domain {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 500;
        }
        .result-rank {
            background: #28a745;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .result-snippet {
            color: #666;
            font-size: 0.95em;
            line-height: 1.5;
            margin-top: 10px;
        }
        .keywords-section {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .keyword-tag {
            display: inline-block;
            background: #2196f3;
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            margin: 4px;
            font-size: 0.9em;
        }
        .footer {
            text-align: center;
            padding: 30px;
            color: #666;
            border-top: 1px solid #eee;
            margin-top: 40px;
        }
        .footer a {
            color: #667eea;
            text-decoration: none;
        }
        .timestamp {
            color: #999;
            font-size: 0.9em;
            text-align: center;
            margin-bottom: 20px;
        }
        @media (max-width: 600px) {
            .stats {
                flex-direction: column;
            }
            .result-meta {
                flex-direction: column;
                align-items: flex-start;
            }
            .result-domain {
                margin-bottom: 8px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 HackVeda Crawler Report</h1>
        <p>Search Results for: <strong>{{ keywords|join(', ') }}</strong></p>
        <p style="opacity: 0.9; font-size: 0.95em;">📧 Sent by: <strong>{{ sender_name }}</strong> ({{ sender_email }})</p>
        <p style="opacity: 0.8; font-size: 0.9em;">Session: {{ session_name }}</p>
    </div>
    
    <div class="timestamp">
        📅 Generated on {{ report_date }}
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{{ total_results }}</div>
            <div class="stat-label">Total Results</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ total_keywords }}</div>
            <div class="stat-label">Keywords</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ unique_domains }}</div>
            <div class="stat-label">Unique Domains</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ session_name }}</div>
            <div class="stat-label">Session</div>
        </div>
    </div>
    
    {% if keywords %}
    <div class="keywords-section">
        <h3>🎯 Keywords Searched:</h3>
        {% for keyword in keywords %}
        <span class="keyword-tag">{{ keyword }}</span>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="results-section">
        <h2 class="section-title">🔍 Search Results</h2>
        
        {% for result in results %}
        <div class="result-item">
            <div class="result-meta">
                <span class="result-domain">{{ result.domain }}</span>
                <span class="result-rank">Rank #{{ result.rank }}</span>
            </div>
            <div class="result-title">
                <a href="{{ result.url }}" target="_blank">{{ result.title }}</a>
            </div>
            <div class="result-snippet">
                {{ result.snippet }}
            </div>
        </div>
        {% endfor %}
    </div>
    
    <div class="footer">
        <p>🤖 Generated by <a href="#">HackVeda Crawler</a></p>
        <p>Powered by Google Search + SendGrid Email</p>
        <p><small>This is an automated report. Results are for research purposes only.</small></p>
    </div>
</body>
</html>
        """
    
    def generate_report(self, crawl_data: Dict[str, Any], sender_info: Dict[str, str] = None) -> Dict[str, str]:
        """Generate HTML and text email report from crawl data."""
        
        # Extract data
        results = crawl_data.get('results', [])
        keywords = crawl_data.get('keywords', [])
        session_name = crawl_data.get('session_name', 'Unknown')
        
        # Calculate stats
        total_results = len(results)
        total_keywords = len(keywords)
        unique_domains = len(set(r.get('domain', '') for r in results))
        
        # Add sender information
        sender_name = sender_info.get('name', 'HackVeda User') if sender_info else 'HackVeda User'
        sender_email = sender_info.get('email', 'Unknown') if sender_info else 'Unknown'
        
        # Prepare template data
        template_data = {
            'results': results,
            'keywords': keywords,
            'session_name': session_name,
            'total_results': total_results,
            'total_keywords': total_keywords,
            'unique_domains': unique_domains,
            'report_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
            'sender_name': sender_name,
            'sender_email': sender_email
        }
        
        # Generate HTML
        template = Template(self.html_template)
        html_content = template.render(**template_data)
        
        # Generate text version
        text_content = self._generate_text_report(template_data)
        
        # Create informative subject line
        keywords_text = ', '.join(keywords[:3])  # First 3 keywords
        if len(keywords) > 3:
            keywords_text += f" (+{len(keywords)-3} more)"
        
        subject = f"🚀 Crawl Report: {total_results} Results for '{keywords_text}' - {session_name}"
        
        return {
            'html': html_content,
            'text': text_content,
            'subject': subject
        }
    
    def _generate_text_report(self, data: Dict[str, Any]) -> str:
        """Generate plain text version of the report."""
        
        keywords_list = ', '.join(data['keywords'])
        text = f"""
🚀 HACKVEDA CRAWLER REPORT
========================

This is your automated crawl report containing search results for the keywords you specified.

📧 Sent by: {data['sender_name']} ({data['sender_email']})
📅 Generated: {data['report_date']}
📊 Session: {data['session_name']}
🎯 Keywords: {keywords_list}

SUMMARY STATISTICS:
• Total Results Found: {data['total_results']}
• Keywords Searched: {data['total_keywords']}
• Unique Domains: {data['unique_domains']}

🔍 DETAILED SEARCH RESULTS:
=========================

"""
        
        for i, result in enumerate(data['results'], 1):
            text += f"""
{i}. {result.get('title', 'No Title')}
   🌐 {result.get('domain', 'Unknown Domain')} | Rank #{result.get('rank', 'N/A')}
   🔗 {result.get('url', 'No URL')}
   📝 {result.get('snippet', 'No description available')}
   
"""
        
        text += """
---
ABOUT THIS REPORT:
This automated report was generated by HackVeda Crawler, a professional web scraping tool.
The search results above were collected from Google search for your specified keywords.

🤖 Generated by HackVeda Crawler
🔧 Powered by Google Search + SendGrid Email
📧 For questions about this report, contact the sender.

Thank you for using HackVeda Crawler!
"""
        
        return text
