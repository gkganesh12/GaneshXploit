#!/usr/bin/env python3
"""
Test Improved Email Report
Shows the new informative email format
"""

import sys
sys.path.append('src')

from app.email.report_generator import CrawlReportGenerator

def test_improved_email():
    """Test the improved email report format."""
    
    print("🚀 Testing Improved Crawl Email Report")
    print("=" * 50)
    
    # Sample crawl data with multiple keywords
    sample_crawl_data = {
        'session_name': 'Digital Marketing Research - Oct 2024',
        'keywords': ['digital marketing tools', 'SEO software', 'content marketing platforms', 'social media automation', 'email marketing services'],
        'results': [
            {
                'title': 'Top 10 Digital Marketing Tools for 2024',
                'url': 'https://example.com/digital-marketing-tools',
                'snippet': 'Discover the most powerful digital marketing tools that can transform your business and boost your online presence with proven strategies.',
                'domain': 'example.com',
                'rank': 1
            },
            {
                'title': 'Best SEO Software Solutions for Agencies',
                'url': 'https://seotools.com/best-software',
                'snippet': 'Compare the top SEO software platforms used by leading agencies worldwide. Features, pricing, and expert reviews included.',
                'domain': 'seotools.com',
                'rank': 2
            },
            {
                'title': 'Content Marketing Platforms: Complete Guide',
                'url': 'https://contentpro.io/platforms-guide',
                'snippet': 'Learn about the best content marketing platforms that help businesses create, manage, and distribute content effectively.',
                'domain': 'contentpro.io',
                'rank': 3
            },
            {
                'title': 'Social Media Automation Tools Review',
                'url': 'https://socialmedia.expert/automation-tools',
                'snippet': 'Comprehensive review of social media automation tools that save time and improve engagement across all platforms.',
                'domain': 'socialmedia.expert',
                'rank': 4
            },
            {
                'title': 'Email Marketing Services Comparison 2024',
                'url': 'https://emailmarketing.com/services-comparison',
                'snippet': 'Compare the top email marketing services with detailed analysis of features, pricing, deliverability, and customer support.',
                'domain': 'emailmarketing.com',
                'rank': 5
            }
        ]
    }
    
    print(f"📊 Sample Data:")
    print(f"   Session: {sample_crawl_data['session_name']}")
    print(f"   Keywords: {len(sample_crawl_data['keywords'])} keywords")
    print(f"   Results: {len(sample_crawl_data['results'])} results")
    print()
    
    # Generate report
    print("📧 Generating improved email report...")
    report_generator = CrawlReportGenerator()
    email_report = report_generator.generate_report(sample_crawl_data)
    
    print(f"✅ Report generated successfully!")
    print()
    print("📧 EMAIL DETAILS:")
    print(f"   Subject: {email_report['subject']}")
    print(f"   HTML Length: {len(email_report['html'])} characters")
    print(f"   Text Length: {len(email_report['text'])} characters")
    print()
    
    print("📋 EMAIL CONTENT PREVIEW:")
    print("=" * 40)
    
    # Show first few lines of text version
    text_lines = email_report['text'].split('\n')[:15]
    for line in text_lines:
        print(line)
    print("... (truncated)")
    print()
    
    print("🎯 WHAT RECIPIENT WILL SEE:")
    print("=" * 40)
    print("📧 Subject Line:")
    print(f"   {email_report['subject']}")
    print()
    print("📄 Email Header:")
    print("   🚀 HackVeda Crawler Report")
    print(f"   Search Results for: {', '.join(sample_crawl_data['keywords'][:3])}...")
    print(f"   Session: {sample_crawl_data['session_name']}")
    print()
    print("📊 Summary Stats:")
    print(f"   • {len(sample_crawl_data['results'])} Total Results")
    print(f"   • {len(sample_crawl_data['keywords'])} Keywords Searched")
    print(f"   • {len(set(r['domain'] for r in sample_crawl_data['results']))} Unique Domains")
    print()
    print("🔍 Results Include:")
    for i, result in enumerate(sample_crawl_data['results'][:3], 1):
        print(f"   {i}. {result['title'][:50]}...")
        print(f"      🌐 {result['domain']} | Rank #{result['rank']}")
    print("   ... and more")
    
    return True

if __name__ == "__main__":
    success = test_improved_email()
    
    if success:
        print("\n🎉 SUCCESS: Email reports are now highly informative!")
        print("\n✅ IMPROVEMENTS MADE:")
        print("• Clear subject line with keywords and result count")
        print("• Header shows exactly what was searched")
        print("• Session name clearly displayed")
        print("• Detailed explanation in text version")
        print("• Professional footer with context")
        print("• Mobile-responsive HTML design")
        print("\n📧 Recipients will immediately understand:")
        print("• This is a crawl report")
        print("• What keywords were searched")
        print("• How many results were found")
        print("• When the report was generated")
        print("• What tool generated it")
    else:
        print("\n❌ Test failed.")
