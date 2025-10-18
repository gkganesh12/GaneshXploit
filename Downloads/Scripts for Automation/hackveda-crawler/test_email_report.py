#!/usr/bin/env python3
"""
Test Email Report Generator
Sends a beautiful crawl report via email
"""

import os
import sys
sys.path.append('src')

from app.email.report_generator import CrawlReportGenerator
from app.email.sendgrid_client import SendGridClient

def test_email_report():
    """Test sending a beautiful crawl report via email."""
    
    print("🚀 Testing HackVeda Crawler Email Report")
    print("=" * 50)
    
    # Sample crawl data (like what we get from demo crawler)
    sample_crawl_data = {
        'session_name': 'Demo Crawl Session',
        'keywords': ['productivity tools', 'project management', 'automation software'],
        'results': [
            {
                'title': 'Top 10 Productivity Tools for 2024',
                'url': 'https://github.com/productivity-tools-2024',
                'snippet': 'Discover the most powerful productivity solutions that can transform your workflow and boost productivity with these amazing tools.',
                'domain': 'github.com',
                'rank': 1
            },
            {
                'title': 'Best Project Management Software Solutions',
                'url': 'https://stackoverflow.com/project-management-guide',
                'snippet': 'Learn everything you need to know about project management with our comprehensive guide and expert tips for teams.',
                'domain': 'stackoverflow.com',
                'rank': 2
            },
            {
                'title': 'Ultimate Guide to Automation Software',
                'url': 'https://medium.com/automation-guide',
                'snippet': 'Compare the top automation tools and find the perfect solution for your business needs with detailed reviews.',
                'domain': 'medium.com',
                'rank': 3
            },
            {
                'title': 'Free Productivity Resources',
                'url': 'https://dev.to/productivity-resources',
                'snippet': 'Explore free and premium productivity options that deliver exceptional results for developers and teams.',
                'domain': 'dev.to',
                'rank': 4
            },
            {
                'title': 'Professional Project Management Platform',
                'url': 'https://notion.so/project-management',
                'snippet': 'Master project management with proven strategies and real-world examples from industry experts.',
                'domain': 'notion.so',
                'rank': 5
            }
        ]
    }
    
    print(f"📊 Sample Data:")
    print(f"   Session: {sample_crawl_data['session_name']}")
    print(f"   Keywords: {len(sample_crawl_data['keywords'])}")
    print(f"   Results: {len(sample_crawl_data['results'])}")
    print()
    
    # Generate report
    print("📧 Generating beautiful email report...")
    report_generator = CrawlReportGenerator()
    email_report = report_generator.generate_report(sample_crawl_data)
    
    print(f"✅ Report generated successfully!")
    print(f"   Subject: {email_report['subject']}")
    print(f"   HTML Length: {len(email_report['html'])} characters")
    print(f"   Text Length: {len(email_report['text'])} characters")
    print()
    
    # Get email address
    to_email = os.getenv('TO_EMAIL', 'ganeshkhetawat12@gmail.com')
    print(f"📬 Sending report to: {to_email}")
    
    # Send email using SendGrid
    sendgrid_client = SendGridClient()
    
    if not sendgrid_client.is_available():
        print("❌ SendGrid not configured. Please set SENDGRID_API_KEY environment variable.")
        return False
    
    result = sendgrid_client.send_email(
        to_email=to_email,
        subject=email_report['subject'],
        text_content=email_report['text'],
        html_content=email_report['html']
    )
    
    if result['success']:
        print(f"✅ Beautiful crawl report sent successfully!")
        print(f"   Message ID: {result.get('message_id', 'N/A')}")
        print(f"   Status Code: {result.get('status_code', 'N/A')}")
        print()
        print("🎉 SUCCESS: Check your email inbox for the beautiful report!")
        print()
        print("📋 Report Features:")
        print("   • Beautiful HTML design with gradients and animations")
        print("   • Summary statistics cards")
        print("   • Keyword tags")
        print("   • Formatted search results with clickable links")
        print("   • Domain badges and ranking indicators")
        print("   • Mobile-responsive design")
        print("   • Professional footer")
        return True
    else:
        print(f"❌ Failed to send email: {result.get('error', 'Unknown error')}")
        return False

if __name__ == "__main__":
    # Set environment variables
    os.environ.setdefault('DATABASE_URL', 'sqlite:///data/hackveda.db')
    os.environ.setdefault('EMAIL_PROVIDER', 'sendgrid')
    
    success = test_email_report()
    
    if success:
        print("\n🎊 AMAZING! Your HackVeda Crawler now sends beautiful email reports!")
        print("\nNext steps:")
        print("1. Use the web interface to crawl keywords")
        print("2. Click 'Email Report' button in the sessions table")
        print("3. Enter your email address")
        print("4. Receive beautiful formatted reports!")
    else:
        print("\n❌ Test failed. Please check your SendGrid configuration.")
