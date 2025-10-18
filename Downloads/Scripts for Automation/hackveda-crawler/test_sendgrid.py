#!/usr/bin/env python3
"""
Quick SendGrid test script for HackVeda Crawler.
Tests SendGrid integration directly without configuration complexity.
"""

import os
import sys
sys.path.append('src')

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def test_sendgrid():
    """Test SendGrid API directly."""
    
    # Get credentials from environment
    api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('FROM_EMAIL', 'ganeshkhetawat12@gmail.com')
    to_email = os.getenv('TO_EMAIL', 'ganeshkhetawat12@gmail.com')
    
    if not api_key:
        print("❌ SENDGRID_API_KEY environment variable not set")
        return False
    
    print(f"🔧 Testing SendGrid with:")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   From: {from_email}")
    print(f"   To: {to_email}")
    print()
    
    try:
        # Initialize SendGrid client
        sg = SendGridAPIClient(api_key=api_key)
        
        # Test connection by sending email directly
        print("📡 Testing SendGrid connection...")
        
        # Create test email
        print("📧 Sending test email...")
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject='🚀 HackVeda Crawler - SendGrid Test',
            html_content='''
            <h2>🎉 SendGrid Integration Successful!</h2>
            <p>This email confirms that your HackVeda Crawler can successfully send emails via SendGrid.</p>
            <p><strong>Test Details:</strong></p>
            <ul>
                <li>✅ SendGrid API connection: Working</li>
                <li>✅ Email delivery: Successful</li>
                <li>✅ HTML formatting: Enabled</li>
            </ul>
            <p>Your HackVeda Crawler is now ready for production email campaigns!</p>
            <hr>
            <p><small>Sent from HackVeda Crawler via SendGrid</small></p>
            '''
        )
        
        # Send email
        response = sg.client.mail.send.post(request_body=message.get())
        
        if response.status_code == 202:
            print(f"✅ Email sent successfully!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Message ID: {response.headers.get('X-Message-Id', 'N/A')}")
            print()
            print("🎊 SendGrid integration is working perfectly!")
            print("   Check your email inbox for the test message.")
            return True
        else:
            print(f"❌ Email sending failed. Status: {response.status_code}")
            print(f"   Response: {response.body}")
            return False
            
    except Exception as e:
        print(f"❌ SendGrid test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 HackVeda Crawler - SendGrid Test")
    print("=" * 40)
    
    success = test_sendgrid()
    
    if success:
        print("\n🎉 SUCCESS: SendGrid is ready for HackVeda Crawler!")
        print("\nNext steps:")
        print("1. Use SendGrid in your email campaigns")
        print("2. Configure templates in SendGrid dashboard")
        print("3. Monitor email analytics and delivery rates")
    else:
        print("\n❌ FAILED: Please check your SendGrid configuration")
        print("\nTroubleshooting:")
        print("1. Verify your SendGrid API key")
        print("2. Check sender email verification in SendGrid")
        print("3. Ensure your SendGrid account is active")
