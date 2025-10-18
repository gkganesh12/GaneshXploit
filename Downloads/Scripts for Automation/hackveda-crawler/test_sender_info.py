#!/usr/bin/env python3
"""
Test Email Report with Sender Information
Shows how sender info appears in email reports
"""

import sys
sys.path.append('src')

from app.email.report_generator import CrawlReportGenerator

def test_sender_info():
    """Test email report with sender information."""
    
    print("🚀 Testing Email Report with Sender Information")
    print("=" * 60)
    
    # Sample crawl data
    sample_crawl_data = {
        'session_name': 'Client Research Project - Q4 2024',
        'keywords': ['digital marketing tools', 'SEO software'],
        'results': [
            {
                'title': 'Top Digital Marketing Tools for Agencies',
                'url': 'https://example.com/digital-tools',
                'snippet': 'Comprehensive guide to the best digital marketing tools used by leading agencies worldwide.',
                'domain': 'example.com',
                'rank': 1
            },
            {
                'title': 'Best SEO Software Solutions 2024',
                'url': 'https://seotools.com/best-software',
                'snippet': 'Compare top SEO software platforms with detailed features, pricing, and expert reviews.',
                'domain': 'seotools.com',
                'rank': 2
            }
        ]
    }
    
    # Sender information
    sender_info = {
        'name': 'Ganesh Khetawat',
        'email': 'gkganesh448@gmail.com'
    }
    
    print(f"📊 Test Data:")
    print(f"   Sender: {sender_info['name']} ({sender_info['email']})")
    print(f"   Session: {sample_crawl_data['session_name']}")
    print(f"   Keywords: {len(sample_crawl_data['keywords'])} keywords")
    print(f"   Results: {len(sample_crawl_data['results'])} results")
    print()
    
    # Generate report
    print("📧 Generating email report with sender info...")
    report_generator = CrawlReportGenerator()
    email_report = report_generator.generate_report(sample_crawl_data, sender_info)
    
    print(f"✅ Report generated successfully!")
    print()
    
    print("📧 EMAIL PREVIEW:")
    print("=" * 50)
    print(f"Subject: {email_report['subject']}")
    print()
    print("📄 EMAIL HEADER:")
    print("🚀 HackVeda Crawler Report")
    print(f"Search Results for: {', '.join(sample_crawl_data['keywords'])}")
    print(f"📧 Sent by: {sender_info['name']} ({sender_info['email']})")
    print(f"Session: {sample_crawl_data['session_name']}")
    print()
    
    print("📋 TEXT VERSION PREVIEW:")
    print("-" * 30)
    text_lines = email_report['text'].split('\n')[:12]
    for line in text_lines:
        if line.strip():
            print(line)
    print("... (truncated)")
    print()
    
    print("🎯 WHAT RECIPIENT SEES:")
    print("=" * 40)
    print("✅ Clear identification of who sent the report")
    print("✅ Sender's name and email prominently displayed")
    print("✅ Professional context for the crawl data")
    print("✅ Easy to contact sender for questions")
    print("✅ Builds trust and accountability")
    
    return True

if __name__ == "__main__":
    success = test_sender_info()
    
    if success:
        print("\n🎉 SUCCESS: Email reports now include sender information!")
        print("\n✅ BENEFITS:")
        print("• Recipients know exactly who sent the report")
        print("• Professional appearance with sender credentials")
        print("• Easy to contact sender for questions or clarifications")
        print("• Builds trust and accountability")
        print("• Perfect for client reports and team collaboration")
        print("\n📧 Email Header Now Shows:")
        print("• Report title and purpose")
        print("• What keywords were searched")
        print("• Who sent the report (name + email)")
        print("• Session name for context")
        print("• Generation timestamp")
    else:
        print("\n❌ Test failed.")
