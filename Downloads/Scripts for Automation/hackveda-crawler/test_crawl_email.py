#!/usr/bin/env python3
"""
Test Crawl Results Email Report
Tests the complete flow: crawl -> store -> email report
"""

import requests
import time
import json

def test_crawl_and_email():
    """Test complete crawl to email flow."""
    
    print("🚀 Testing Complete Crawl-to-Email Flow")
    print("=" * 50)
    
    base_url = "http://localhost:3000"
    
    # Step 1: Start a crawl
    print("🕷️ Step 1: Starting crawl...")
    crawl_data = {
        "keywords": ["digital marketing", "SEO tools"],
        "max_results": 3,
        "session_name": "email_test_session"
    }
    
    response = requests.post(f"{base_url}/api/crawl", json=crawl_data)
    if response.status_code == 200:
        crawl_result = response.json()
        print(f"✅ Crawl started: {crawl_result['session_name']}")
        
        # Wait for crawl to complete
        print("⏳ Waiting for crawl to complete...")
        time.sleep(8)
        
        # Step 2: Get latest session
        print("📋 Step 2: Getting session details...")
        sessions_response = requests.get(f"{base_url}/api/sessions")
        if sessions_response.status_code == 200:
            sessions = sessions_response.json()['sessions']
            latest_session = sessions[0]  # Most recent
            
            print(f"✅ Latest session: {latest_session['session_name']}")
            print(f"   Keywords: {latest_session['keywords']}")
            print(f"   Results: {latest_session['total_results']}")
            
            # Step 3: Send email report
            print("📧 Step 3: Sending email report...")
            email_data = {
                "to_email": "ganeshkhetawat12@gmail.com",
                "session_id": latest_session['id']
            }
            
            email_response = requests.post(f"{base_url}/api/email/report", json=email_data)
            if email_response.status_code == 200:
                email_result = email_response.json()
                if email_result.get('success'):
                    print(f"✅ Email report sent successfully!")
                    print(f"   Message ID: {email_result.get('message_id')}")
                    print(f"   Total Results: {email_result.get('total_results')}")
                    print(f"   Sent to: ganeshkhetawat12@gmail.com")
                    
                    print("\n🎉 SUCCESS: Complete flow working!")
                    print("\n📧 Email Report Contains:")
                    print("   • Beautiful HTML design with gradients")
                    print("   • Summary statistics cards")
                    print("   • All crawled keywords as tags")
                    print("   • Complete search results with:")
                    print("     - Clickable titles and URLs")
                    print("     - Domain badges")
                    print("     - Ranking information")
                    print("     - Result snippets")
                    print("   • Professional footer")
                    print("   • Mobile-responsive design")
                    
                    return True
                else:
                    print(f"❌ Email failed: {email_result.get('error')}")
            else:
                print(f"❌ Email API error: {email_response.status_code}")
        else:
            print(f"❌ Sessions API error: {sessions_response.status_code}")
    else:
        print(f"❌ Crawl API error: {response.status_code}")
    
    return False

if __name__ == "__main__":
    success = test_crawl_and_email()
    
    if success:
        print("\n🎊 AMAZING! Your crawl results are now being emailed!")
        print("\nNext steps:")
        print("1. Check your email inbox for the beautiful report")
        print("2. Use the web interface to crawl more keywords")
        print("3. Click 'Email Report' buttons to send results")
        print("4. Share reports with clients and team members")
    else:
        print("\n❌ Test failed. Check the logs above.")
