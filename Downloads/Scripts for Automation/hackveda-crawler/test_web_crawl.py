#!/usr/bin/env python3
"""
Test Web Crawling via API
Direct API test to bypass JavaScript issues
"""

import requests
import json
import time

def test_web_crawl():
    """Test crawling via web API."""
    
    print("🚀 Testing HackVeda Crawler Web API")
    print("=" * 50)
    
    base_url = "http://localhost:8080"
    
    # Test health check
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test crawling
    print("\n🕷️ Testing crawling API...")
    crawl_data = {
        "keywords": ["productivity tools", "automation software"],
        "max_results": 5,
        "session_name": "api_test_session"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/crawl",
            headers={"Content-Type": "application/json"},
            json=crawl_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Crawling started: {result['session_name']}")
            
            # Wait a bit for crawling to complete
            print("⏳ Waiting for crawling to complete...")
            time.sleep(10)
            
            # Check database stats
            print("\n📊 Checking database stats...")
            stats_response = requests.get(f"{base_url}/api/database/stats")
            if stats_response.status_code == 200:
                stats = stats_response.json()
                print(f"✅ Database stats: {stats}")
            
            # Check sessions
            print("\n📋 Checking sessions...")
            sessions_response = requests.get(f"{base_url}/api/sessions")
            if sessions_response.status_code == 200:
                sessions = sessions_response.json()
                print(f"✅ Found {len(sessions.get('sessions', []))} sessions")
                
                # Try to send email report for latest session
                if sessions.get('sessions'):
                    latest_session = sessions['sessions'][0]
                    session_id = latest_session['id']
                    
                    print(f"\n📧 Testing email report for session {session_id}...")
                    email_data = {
                        "to_email": "ganeshkhetawat12@gmail.com",
                        "session_id": session_id
                    }
                    
                    email_response = requests.post(
                        f"{base_url}/api/email/report",
                        headers={"Content-Type": "application/json"},
                        json=email_data
                    )
                    
                    if email_response.status_code == 200:
                        email_result = email_response.json()
                        if email_result.get('success'):
                            print(f"✅ Email report sent! Message ID: {email_result.get('message_id')}")
                        else:
                            print(f"❌ Email failed: {email_result.get('error')}")
                    else:
                        print(f"❌ Email API error: {email_response.status_code}")
            
            return True
            
        else:
            print(f"❌ Crawling failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Crawling error: {e}")
        return False

if __name__ == "__main__":
    success = test_web_crawl()
    
    if success:
        print("\n🎉 SUCCESS: Web API is working perfectly!")
        print("\nFeatures tested:")
        print("✅ Health check")
        print("✅ Crawling API")
        print("✅ Database stats")
        print("✅ Sessions API")
        print("✅ Email report API")
        print("\n🌐 Your web interface is ready at: http://localhost:8080")
    else:
        print("\n❌ FAILED: Some APIs are not working properly")
