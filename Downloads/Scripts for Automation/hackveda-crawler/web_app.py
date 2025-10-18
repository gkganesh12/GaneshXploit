#!/usr/bin/env python3
"""
HackVeda Crawler - Modern Web Interface
Beautiful, responsive web UI for the Google Crawler + Email Sender
"""

import os
import sys
import json
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging

# Add src to path
sys.path.append('src')

from app.config import get_config
from app.database.db import get_db_manager
from app.email.smtp_client import EmailServiceManager
from app.crawler.google_serp import GoogleSERPCrawler
from app.crawler.demo_crawler import DemoCrawler
from app.email.report_generator import CrawlReportGenerator

# Initialize Flask app
app = Flask(__name__, 
           template_folder='web/templates',
           static_folder='web/static')
app.config['SECRET_KEY'] = 'hackveda-crawler-secret-key'

# Enable CORS and SocketIO
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
config = None
db_manager = None
email_service = None

def initialize_services():
    """Initialize all services."""
    global config, db_manager, email_service
    
    try:
        # Load configuration
        config = get_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize database
        db_manager = get_db_manager()
        logger.info("Database manager initialized")
        
        # Initialize email service
        email_service = EmailServiceManager(config)
        logger.info("Email service initialized")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False

# Routes
@app.route('/')
def dashboard():
    """Main dashboard."""
    return render_template('dashboard.html')

@app.route('/debug')
def debug():
    """Debug page."""
    with open('debug_status.html', 'r') as f:
        return f.read()

@app.route('/test')
def simple_test():
    """Simple test page."""
    with open('simple_test.html', 'r') as f:
        return f.read()

@app.route('/api/health')
def health_check():
    """System health check API."""
    try:
        # Check database
        db_healthy = db_manager is not None
        
        # Check email services
        email_results = email_service.test_services() if email_service else {}
        
        # Get database stats
        db_stats = db_manager.get_stats() if db_manager else {}
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': 'healthy' if db_healthy else 'error',
                'email_services': email_results,
                'database_stats': db_stats
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/crawl', methods=['POST'])
def start_crawl():
    """Start crawling operation."""
    try:
        data = request.get_json()
        keywords = data.get('keywords', [])
        max_results = data.get('max_results', 10)
        session_name = data.get('session_name', f'web_crawl_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        if not keywords:
            return jsonify({'error': 'Keywords are required'}), 400
        
        # Start crawling in background thread
        def crawl_task():
            try:
                # Use demo crawler for reliable results
                crawler = DemoCrawler(config)
                
                # Emit progress updates
                socketio.emit('crawl_progress', {
                    'status': 'started',
                    'session_name': session_name,
                    'keywords': keywords
                })
                
                all_results = []
                for i, keyword in enumerate(keywords):
                    socketio.emit('crawl_progress', {
                        'status': 'crawling',
                        'current_keyword': keyword,
                        'progress': (i / len(keywords)) * 100
                    })
                    
                    results = crawler.crawl_keyword(keyword, max_results)
                    all_results.extend(results)
                
                # Store results in database
                if db_manager and all_results:
                    with db_manager.get_session() as session:
                        from app.database.repositories import CrawlSessionRepository, SearchResultRepository
                        
                        # Create crawl session
                        session_repo = CrawlSessionRepository(session)
                        crawl_session = session_repo.create(
                            session_name=session_name,
                            keywords=keywords,
                            status='completed'
                        )
                        
                        # Store results
                        result_repo = SearchResultRepository(session)
                        for result in all_results:
                            result_repo.create(
                                crawl_session_id=crawl_session.id,
                                title=result.title,
                                url=result.url,
                                snippet=result.snippet,
                                rank=result.rank,
                                domain=result.domain,
                                crawl_timestamp=result.crawl_timestamp,
                                response_time=result.response_time,
                                source_keyword=result.result_metadata.get('keyword', ''),
                                result_metadata=result.result_metadata
                            )
                        
                        session.commit()
                
                socketio.emit('crawl_complete', {
                    'status': 'completed',
                    'session_name': session_name,
                    'total_results': len(all_results),
                    'results': [
                        {
                            'title': r.title,
                            'url': r.url,
                            'snippet': r.snippet,
                            'domain': r.domain,
                            'rank': r.rank
                        } for r in all_results[:10]  # Send first 10 for preview
                    ]
                })
                
            except Exception as e:
                socketio.emit('crawl_error', {
                    'status': 'error',
                    'error': str(e)
                })
        
        # Start background thread
        thread = threading.Thread(target=crawl_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'started',
            'session_name': session_name,
            'message': 'Crawling started successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/test', methods=['POST'])
def test_email():
    """Test email services."""
    try:
        if not email_service:
            return jsonify({'error': 'Email service not initialized'}), 500
        
        results = email_service.test_services()
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/send', methods=['POST'])
def send_email():
    """Send email."""
    try:
        data = request.get_json()
        to_email = data.get('to_email')
        subject = data.get('subject')
        body = data.get('body')
        html_body = data.get('html_body')
        
        if not all([to_email, subject, body]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not email_service:
            return jsonify({'error': 'Email service not initialized'}), 500
        
        # Use SendGrid directly for web interface
        if email_service.sendgrid_service and email_service.sendgrid_service.is_available():
            result = email_service.sendgrid_service.send_email(
                to_email=to_email,
                subject=subject,
                text_content=body,
                html_content=html_body
            )
        else:
            result = email_service.send_email(
                to_address=to_email,
                subject=subject,
                body=body,
                html_body=html_body
            )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/stats')
def database_stats():
    """Get database statistics."""
    try:
        if not db_manager:
            return jsonify({'error': 'Database not initialized'}), 500
        
        stats = db_manager.get_stats()
        return jsonify({
            'status': 'success',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions')
def get_sessions():
    """Get crawl sessions."""
    try:
        if not db_manager:
            return jsonify({'error': 'Database not initialized'}), 500
        
        sessions_data = []
        try:
            with db_manager.get_session() as session:
                from app.database.repositories import CrawlSessionRepository
                session_repo = CrawlSessionRepository(session)
                sessions = session_repo.get_recent(limit=20)
                
                # Convert sessions to dict within session context
                for s in sessions:
                    sessions_data.append({
                        'id': s.id,
                        'session_name': s.session_name,
                        'keywords': s.keywords,
                        'status': s.status,
                        'start_time': s.start_time.isoformat() if s.start_time else None,
                        'total_results': s.total_results or 0
                    })
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            sessions_data = []
        
        return jsonify({
            'status': 'success',
            'sessions': sessions_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email/report', methods=['POST'])
def send_crawl_report():
    """Send crawl results as a beautiful email report."""
    try:
        data = request.get_json()
        to_email = data.get('to_email')
        session_id = data.get('session_id')
        
        if not to_email or not session_id:
            return jsonify({'error': 'Missing required fields: to_email, session_id'}), 400
        
        if not db_manager:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get crawl session and results from database
        with db_manager.get_session() as session:
            from app.database.repositories import CrawlSessionRepository, SearchResultRepository
            
            session_repo = CrawlSessionRepository(session)
            result_repo = SearchResultRepository(session)
            
            # Get session data
            crawl_session = session_repo.get_by_id(session_id)
            if not crawl_session:
                return jsonify({'error': 'Crawl session not found'}), 404
            
            # Get results
            results = result_repo.get_by_session(session_id)
            
            # Prepare data for report
            crawl_data = {
                'session_name': crawl_session.session_name,
                'keywords': crawl_session.keywords if isinstance(crawl_session.keywords, list) else [crawl_session.keywords],
                'results': [
                    {
                        'title': r.title,
                        'url': r.url,
                        'snippet': r.snippet,
                        'domain': r.domain,
                        'rank': r.rank
                    } for r in results
                ]
            }
        
        # Prepare sender information
        sender_info = {
            'name': config.email.from_name or 'HackVeda User',
            'email': config.email.from_email or 'unknown@example.com'
        }
        
        # Generate beautiful email report
        report_generator = CrawlReportGenerator()
        email_report = report_generator.generate_report(crawl_data, sender_info)
        
        # Send email using SendGrid
        if email_service.sendgrid_service and email_service.sendgrid_service.is_available():
            result = email_service.sendgrid_service.send_email(
                to_email=to_email,
                subject=email_report['subject'],
                text_content=email_report['text'],
                html_content=email_report['html']
            )
        else:
            result = email_service.send_email(
                to_address=to_email,
                subject=email_report['subject'],
                body=email_report['text'],
                html_body=email_report['html']
            )
        
        if result.get('success'):
            # Log email in database
            with db_manager.get_session() as log_session:
                from app.database.repositories import EmailLogRepository
                email_log_repo = EmailLogRepository(log_session)
                email_log_repo.create(
                    to_address=to_email,
                    from_address=config.email.from_email,
                    subject=email_report['subject'],
                    status='sent',
                    sent_at=datetime.now(),
                    message_id=result.get('message_id')
                )
                log_session.commit()
            
            # Emit real-time update to dashboard
            socketio.emit('email_sent', {
                'to_email': to_email,
                'subject': email_report['subject'],
                'message_id': result.get('message_id'),
                'total_results': len(crawl_data['results']),
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'message': f'Crawl report sent successfully to {to_email}',
                'message_id': result.get('message_id'),
                'total_results': len(crawl_data['results'])
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to send email')
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# SocketIO events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('connected', {'message': 'Connected to HackVeda Crawler'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')

if __name__ == '__main__':
    # Set environment variables
    os.environ.setdefault('DATABASE_URL', 'sqlite:///data/hackveda.db')
    os.environ.setdefault('EMAIL_PROVIDER', 'sendgrid')
    
    # Initialize services
    if initialize_services():
        logger.info("🚀 Starting HackVeda Crawler Web Interface...")
        logger.info("📱 Dashboard will be available at: http://localhost:3000")
        
        # Run the app
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=3000, 
                    debug=True,
                    allow_unsafe_werkzeug=True)
    else:
        logger.error("❌ Failed to initialize services. Exiting.")
        sys.exit(1)
