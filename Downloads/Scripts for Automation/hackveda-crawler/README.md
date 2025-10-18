# HackVeda Crawler - Google Crawler + Gmail Email Sender

A production-ready Python application for digital marketing that crawls Google search results and sends personalized outreach emails via Gmail API.

## 🚀 Features

### Crawling
- **Smart Google SERP Crawling**: Fetch top N search results for keywords
- **Dual Mode Support**: Light mode (requests + BeautifulSoup) and Browser mode (Playwright)
- **Respectful Crawling**: Rate limiting, randomized delays, robots.txt compliance
- **Data Enrichment**: Extract contact info, domain metadata, and social links

### Email Marketing
- **Secure Gmail Integration**: OAuth2 authentication with Gmail API
- **Personalized Templates**: Jinja2 templating for dynamic email content
- **Send Tracking**: Monitor email status (queued, sent, failed, bounces)
- **Rate Limiting**: Respect Gmail sending limits with intelligent backoff

### Data Management
- **Persistent Storage**: PostgreSQL/SQLite with SQLAlchemy ORM
- **Deduplication**: Smart duplicate detection and data normalization
- **Export Options**: CSV export and audit trails
- **GDPR Compliance**: Data protection and opt-out mechanisms

### Operations
- **Containerized**: Docker and docker-compose ready
- **Scheduling**: Cron and APScheduler support for recurring tasks
- **Monitoring**: Comprehensive logging and health checks
- **Testing**: Unit tests and integration tests included

## 🛠️ Tech Stack

- **Python 3.10+**
- **Crawling**: Requests, BeautifulSoup4, Playwright
- **Database**: SQLAlchemy + PostgreSQL/SQLite
- **Email**: Google API Client, OAuth2
- **Templating**: Jinja2
- **Scheduling**: APScheduler
- **Testing**: Pytest
- **Deployment**: Docker, Docker Compose

## 📋 Prerequisites

1. **Python 3.10+** installed
2. **Google Cloud Console** account for Gmail API
3. **Docker** (optional, for containerized deployment)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd hackveda-crawler
pip install -r requirements.txt
```

### 2. Configure Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth2 credentials (Desktop application)
5. Download `credentials.json` to `secrets/` directory

### 3. Configuration

```bash
cp examples/config.example.yml config.yml
# Edit config.yml with your settings
```

### 4. Initial OAuth2 Setup

```bash
python src/cli.py auth setup
# Follow the browser prompt to authorize the application
```

### 5. Run Demo

```bash
# Crawl keywords and send test email
python src/cli.py crawl --keywords "productivity tools,project management"
python src/cli.py email send --template welcome --to test@example.com
```

## 🐳 Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# Run demo in container
docker-compose exec app python src/cli.py crawl --keywords "saas tools"
```

## 📊 Usage Examples

### Crawling

```python
from src.app.crawler.google_serp import GoogleSERPCrawler

crawler = GoogleSERPCrawler()
results = crawler.crawl_keywords(["productivity tools"], max_results=10)
```

### Email Sending

```python
from src.app.email.gmail_api import GmailService

gmail = GmailService()
gmail.send_templated_email(
    to="lead@company.com",
    template="outreach",
    context={"company": "Company Name", "product": "Your Product"}
)
```

## 🔒 Security & Compliance

### Gmail API Security
- **OAuth2 Flow**: Secure token-based authentication
- **Token Storage**: Encrypted token storage with automatic refresh
- **No Passwords**: Never store Gmail passwords or app passwords

### Data Protection
- **GDPR Compliance**: Data minimization and opt-out mechanisms
- **Audit Trails**: Complete logging of all data processing
- **Secure Storage**: Encrypted sensitive data storage

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
