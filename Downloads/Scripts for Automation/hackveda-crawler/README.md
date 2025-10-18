# 🚀 HackVeda Crawler - Complete Web Scraping & Email Marketing Tool

A production-ready Python application for digital marketing that crawls Google search results and sends beautiful HTML email reports. Features a modern web dashboard, CLI interface, and professional email templates with sender identification.

## 🚀 Features

### Crawling
- **Smart Google SERP Crawling**: Fetch top N search results for keywords
- **Dual Mode Support**: Light mode (requests + BeautifulSoup) and Browser mode (Playwright)
- **Respectful Crawling**: Rate limiting, randomized delays, robots.txt compliance
- **Data Enrichment**: Extract contact info, domain metadata, and social links

### Email Marketing
- **SendGrid Integration**: Professional email delivery with high deliverability
- **Beautiful HTML Reports**: Responsive email templates with sender identification
- **Professional Templates**: Jinja2 templating with crawl results formatting
- **Send Tracking**: Monitor email status with real-time dashboard updates
- **Sender Information**: Clear sender name and email in all reports

### Data Management
- **Persistent Storage**: PostgreSQL/SQLite with SQLAlchemy ORM
- **Deduplication**: Smart duplicate detection and data normalization
- **Export Options**: CSV export and audit trails
- **GDPR Compliance**: Data protection and opt-out mechanisms

### Web Interface
- **Modern Dashboard**: Real-time web interface on port 3000
- **Socket.IO Integration**: Live updates and progress tracking
- **Session Management**: View and manage all crawl sessions
- **Email Reports**: Send reports directly from web interface
- **API Endpoints**: Complete REST API for all operations

### Operations
- **Containerized**: Docker and docker-compose ready
- **CLI Interface**: Rich command-line tools with colored output
- **Monitoring**: Comprehensive logging and health checks
- **Testing**: Unit tests and integration tests included

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, SQLAlchemy
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS
- **Database**: SQLite (development), PostgreSQL (production)
- **Email**: SendGrid API, Jinja2 templating
- **Real-time**: Socket.IO, Flask-SocketIO
- **Crawling**: Requests, BeautifulSoup4, Demo mode
- **Testing**: Pytest, comprehensive test suite
- **Deployment**: Docker, Docker Compose

## 📋 Prerequisites

1. **Python 3.10+** installed
2. **SendGrid Account** for email delivery (free tier available)
3. **Docker** (optional, for containerized deployment)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/gkganesh12/GaneshXploit.git
cd GaneshXploit
pip install -r requirements.txt
```

### 2. Configure SendGrid

1. Sign up at [SendGrid](https://sendgrid.com/) (free tier available)
2. Create an API key in SendGrid dashboard
3. Set environment variables:

```bash
export SENDGRID_API_KEY="your_sendgrid_api_key"
export FROM_EMAIL="your_verified_email@domain.com"
export DATABASE_URL="sqlite:///data/hackveda.db"
```

### 3. Run Web Interface

```bash
python web_app.py
# Open http://localhost:3000 in your browser
```

### 4. Run CLI Demo

```bash
# Crawl keywords with demo mode
python src/cli.py crawl keywords --keywords "productivity tools" --demo --max-results 5

# Check database stats
python src/cli.py db stats
```

### 5. Send Email Reports

Use the web interface to:
1. Enter keywords and start crawling
2. View results in the sessions table
3. Click "Email Report" to send beautiful HTML reports

## 🐳 Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# Run demo in container
docker-compose exec app python src/cli.py crawl --keywords "saas tools"
```

## 🌐 Web Interface Features

### Dashboard Overview
- **Real-time Stats**: Live database statistics and system health
- **Session Management**: View all crawl sessions with results count
- **Progress Tracking**: Live crawling progress with Socket.IO
- **Email Activity**: Real-time email sending notifications

### Crawling Interface
- **Keyword Input**: Multi-line keyword entry with validation
- **Demo Mode**: Safe testing with realistic sample data
- **Progress Bar**: Visual feedback during crawling operations
- **Results Display**: Immediate session creation and status updates

### Email Reports
- **Beautiful HTML**: Professional email templates with gradients
- **Sender Information**: Clear identification of report sender
- **Result Summary**: Statistics cards with total results and domains
- **Responsive Design**: Mobile-friendly email layouts

## 📊 Usage Examples

### Web Interface
1. Open http://localhost:3000
2. Enter keywords (one per line)
3. Click "Start Crawling"
4. View results in sessions table
5. Click "Email Report" to send formatted reports

### CLI Usage

```bash
# Demo crawling
python src/cli.py crawl keywords --keywords "digital marketing tools" --demo

# Database operations
python src/cli.py db stats
python src/cli.py db sessions

# Email testing
python test_sendgrid.py
```

### API Usage

```python
# Direct API calls
import requests

# Start crawling
response = requests.post('http://localhost:3000/api/crawl', json={
    'keywords': ['productivity tools'],
    'max_results': 10
})

# Send email report
response = requests.post('http://localhost:3000/api/email/report', json={
    'to_email': 'recipient@example.com',
    'session_id': 1
})
```

## 🔒 Security & Compliance

### Email Security
- **SendGrid API**: Secure API key-based authentication
- **Environment Variables**: API keys stored in environment, not code
- **Sender Verification**: Professional sender identification in emails
- **No Password Storage**: API-based authentication only

### Data Protection
- **GDPR Compliance**: Data minimization and opt-out mechanisms
- **Audit Trails**: Complete logging of all data processing
- **Secure Storage**: SQLite database with proper access controls
- **API Key Management**: Secure credential handling

### Crawling Ethics
- **Robots.txt Compliance**: Automatic robots.txt checking
- **Rate Limiting**: Respectful crawling with delays
- **Terms of Service**: Guidelines for ethical usage

## 📈 Monitoring & Operations

### Logging
```bash
# View logs
tail -f logs/crawler.log
tail -f logs/email.log
```

### Health Checks
```bash
python src/cli.py health
```

### Database Management
```bash
# Initialize database
python src/cli.py db init

# Export data
python src/cli.py export --format csv --output leads.csv
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/test_crawler.py
pytest tests/test_email.py

# Run integration tests
pytest tests/integration/
```

## 📝 Configuration Reference

### config.yml Structure

```yaml
crawler:
  mode: light                    # light | browser
  user_agent: "HackVedaBot/1.0"
  delay_min: 2                   # seconds
  delay_max: 6                   # seconds
  max_results: 10
  respect_robots_txt: true

database:
  url: "postgresql://user:pass@localhost/db"
  # or sqlite:///data.db

email:
  provider: gmail_api            # gmail_api | smtp
  gmail:
    credentials_path: "secrets/credentials.json"
    token_path: "secrets/token.json"
    from_address: "your@email.com"
    daily_limit: 500
    rate_limit: 10               # emails per minute

app:
  concurrency: 3
  log_level: INFO
  data_retention_days: 90
```

## 🔧 Troubleshooting

### Common Issues

1. **Gmail API Quota Exceeded**
   - Check daily sending limits
   - Implement exponential backoff
   - Monitor rate limiting logs

2. **Crawling Blocked**
   - Increase delays between requests
   - Rotate user agents
   - Use proxy rotation (if configured)

3. **OAuth2 Token Expired**
   - Run `python src/cli.py auth refresh`
   - Check token expiration in logs

### Support

For issues and feature requests, please check the documentation or create an issue.

## 📄 License

MIT License - see LICENSE file for details.

## ⚖️ Legal Notice

This tool is for legitimate marketing purposes only. Users must:
- Comply with GDPR, CAN-SPAM, and local regulations
- Respect website terms of service
- Implement proper opt-out mechanisms
- Use ethical crawling practices

The developers are not responsible for misuse of this software.
