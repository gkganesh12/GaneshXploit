# HackVeda Crawler - Deployment Guide

This guide covers various deployment options for the HackVeda Crawler application.

## 🚀 Deployment Options

### 1. Local Development Setup

#### Prerequisites
- Python 3.10+
- pip or conda
- Git

#### Setup Steps
```bash
# Clone repository
git clone <repository-url>
cd hackveda-crawler

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration
cp examples/config.example.yml config.yml

# Edit configuration
nano config.yml  # Configure your settings

# Initialize database
python src/cli.py db init

# Setup Gmail authentication
python src/cli.py email auth setup

# Run health check
python src/cli.py health
```

### 2. Docker Deployment

#### Single Container
```bash
# Build image
docker build -t hackveda-crawler .

# Run container
docker run -d \
  --name hackveda-crawler \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/secrets:/app/secrets \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  hackveda-crawler
```

#### Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Run CLI commands
docker-compose exec app python src/cli.py health

# Stop services
docker-compose down
```

### 3. Production Server Deployment

#### Ubuntu/Debian Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip git nginx

# Create application user
sudo useradd -m -s /bin/bash hackveda
sudo su - hackveda

# Clone and setup application
git clone <repository-url> /home/hackveda/hackveda-crawler
cd /home/hackveda/hackveda-crawler

# Setup virtual environment
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure application
cp examples/config.example.yml config.yml
# Edit config.yml with production settings

# Create systemd service
sudo tee /etc/systemd/system/hackveda-crawler.service > /dev/null <<EOF
[Unit]
Description=HackVeda Crawler Service
After=network.target

[Service]
Type=simple
User=hackveda
WorkingDirectory=/home/hackveda/hackveda-crawler
Environment=PATH=/home/hackveda/hackveda-crawler/venv/bin
ExecStart=/home/hackveda/hackveda-crawler/venv/bin/python src/cli.py scheduler start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable hackveda-crawler
sudo systemctl start hackveda-crawler
```

### 4. Cloud Deployment

#### AWS EC2 Deployment

1. **Launch EC2 Instance**
   - Choose Ubuntu 22.04 LTS
   - Instance type: t3.medium or larger
   - Configure security groups (SSH, HTTP, HTTPS)

2. **Setup Application**
```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone <repository-url>
cd hackveda-crawler

# Configure for production
cp examples/config.example.yml config.yml
cp examples/docker-compose.prod.yml docker-compose.yml

# Start services
docker-compose up -d
```

#### Google Cloud Platform (GCP)

1. **Create Compute Engine Instance**
```bash
gcloud compute instances create hackveda-crawler \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB
```

2. **Deploy Application**
```bash
# SSH to instance
gcloud compute ssh hackveda-crawler --zone=us-central1-a

# Follow Ubuntu server setup steps above
```

#### DigitalOcean Droplet

1. **Create Droplet**
   - Ubuntu 22.04 LTS
   - 2GB RAM minimum
   - Enable monitoring and backups

2. **Deploy with Docker**
```bash
# SSH to droplet
ssh root@your-droplet-ip

# Install Docker (one-click app) or manual installation
# Follow Docker deployment steps above
```

### 5. Kubernetes Deployment

#### Kubernetes Manifests

**Namespace:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: hackveda-crawler
```

**ConfigMap:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hackveda-config
  namespace: hackveda-crawler
data:
  config.yml: |
    crawler:
      mode: light
      max_results: 10
    database:
      url: "postgresql://user:pass@postgres:5432/hackveda"
    email:
      provider: gmail_api
```

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hackveda-crawler
  namespace: hackveda-crawler
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hackveda-crawler
  template:
    metadata:
      labels:
        app: hackveda-crawler
    spec:
      containers:
      - name: hackveda-crawler
        image: hackveda-crawler:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: config
          mountPath: /app/config.yml
          subPath: config.yml
        - name: secrets
          mountPath: /app/secrets
      volumes:
      - name: config
        configMap:
          name: hackveda-config
      - name: secrets
        secret:
          secretName: hackveda-secrets
```

**Service:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: hackveda-crawler-service
  namespace: hackveda-crawler
spec:
  selector:
    app: hackveda-crawler
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 6. Environment Configuration

#### Production Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hackveda_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Email
GMAIL_CREDENTIALS_PATH=/app/secrets/credentials.json
GMAIL_TOKEN_PATH=/app/secrets/token.json
GMAIL_FROM_ADDRESS=noreply@yourdomain.com
GMAIL_DAILY_LIMIT=500

# Application
LOG_LEVEL=INFO
DATA_RETENTION_DAYS=90
CONCURRENCY=5

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
PROMETHEUS_ENABLED=true
```

#### Configuration Files

**Production config.yml:**
```yaml
crawler:
  mode: light
  user_agent: "HackVedaBot/1.0 (+https://yourdomain.com/bot)"
  delay_min: 3
  delay_max: 8
  max_results: 50
  respect_robots_txt: true
  timeout: 30
  max_retries: 3

database:
  url: "${DATABASE_URL}"
  pool_size: 20
  max_overflow: 30
  echo: false

email:
  provider: gmail_api
  gmail:
    credentials_path: "${GMAIL_CREDENTIALS_PATH}"
    token_path: "${GMAIL_TOKEN_PATH}"
    from_address: "${GMAIL_FROM_ADDRESS}"
    from_name: "HackVeda Marketing"
    daily_limit: 500
    rate_limit: 10

app:
  concurrency: 5
  log_level: INFO
  data_retention_days: 90
  debug: false

scheduler:
  enabled: true
  jobs:
    - name: daily_crawl
      action: crawl
      schedule: "0 9 * * *"  # 9 AM daily
      keywords: ["productivity tools", "saas tools"]
      max_results: 20

monitoring:
  sentry_dsn: "${SENTRY_DSN}"
  prometheus_enabled: true
  health_check_interval: 300
```

### 7. Database Setup

#### PostgreSQL Production Setup

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE hackveda_prod;
CREATE USER hackveda WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE hackveda_prod TO hackveda;
\q

# Configure PostgreSQL
sudo nano /etc/postgresql/14/main/postgresql.conf
# Set: shared_preload_libraries = 'pg_stat_statements'
# Set: max_connections = 100

sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add: host hackveda_prod hackveda 127.0.0.1/32 md5

sudo systemctl restart postgresql
```

#### Database Migration and Backup

```bash
# Initialize database
python src/cli.py db init

# Create backup
pg_dump -U hackveda -h localhost hackveda_prod > backup_$(date +%Y%m%d).sql

# Restore backup
psql -U hackveda -h localhost hackveda_prod < backup_20240101.sql

# Automated backups (crontab)
0 2 * * * /usr/bin/pg_dump -U hackveda hackveda_prod | gzip > /backups/hackveda_$(date +\%Y\%m\%d).sql.gz
```

### 8. Monitoring and Logging

#### Log Management

```bash
# Configure log rotation
sudo tee /etc/logrotate.d/hackveda-crawler > /dev/null <<EOF
/home/hackveda/hackveda-crawler/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 hackveda hackveda
    postrotate
        systemctl reload hackveda-crawler
    endscript
}
EOF
```

#### Health Monitoring

```bash
# Create health check script
tee /home/hackveda/health_check.sh > /dev/null <<EOF
#!/bin/bash
cd /home/hackveda/hackveda-crawler
source venv/bin/activate

# Run health check
if python src/cli.py health; then
    echo "$(date): Health check passed"
else
    echo "$(date): Health check failed"
    # Send alert (email, Slack, etc.)
    systemctl restart hackveda-crawler
fi
EOF

chmod +x /home/hackveda/health_check.sh

# Add to crontab
echo "*/5 * * * * /home/hackveda/health_check.sh >> /var/log/health_check.log 2>&1" | crontab -
```

### 9. Security Hardening

#### Server Security

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Install fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Secure SSH
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
# Set: PasswordAuthentication no
# Set: Port 2222 (change default port)

sudo systemctl restart ssh
```

#### Application Security

```bash
# Set proper file permissions
chmod 600 config.yml
chmod 600 secrets/*
chmod 755 src/
chown -R hackveda:hackveda /home/hackveda/hackveda-crawler

# Environment variables for secrets
export GMAIL_CREDENTIALS_PATH=/app/secrets/credentials.json
export DATABASE_PASSWORD=secure_password

# Use secrets management (AWS Secrets Manager, etc.)
```

### 10. Scaling and Performance

#### Horizontal Scaling

```bash
# Load balancer configuration (Nginx)
upstream hackveda_backend {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://hackveda_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Performance Optimization

```bash
# Database connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Concurrent crawling
CRAWLER_CONCURRENCY=5
CRAWLER_BATCH_SIZE=10

# Caching
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

### 11. Backup and Recovery

#### Automated Backups

```bash
# Database backup script
tee /home/hackveda/backup.sh > /dev/null <<EOF
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U hackveda hackveda_prod | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Application files backup
tar -czf $BACKUP_DIR/app_$DATE.tar.gz \
    /home/hackveda/hackveda-crawler/config.yml \
    /home/hackveda/hackveda-crawler/secrets/ \
    /home/hackveda/hackveda-crawler/data/

# Upload to cloud storage (optional)
# aws s3 cp $BACKUP_DIR/ s3://your-backup-bucket/ --recursive

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
EOF

chmod +x /home/hackveda/backup.sh

# Schedule daily backups
echo "0 3 * * * /home/hackveda/backup.sh" | crontab -
```

### 12. Troubleshooting

#### Common Issues

1. **Database Connection Issues**
```bash
# Check database status
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"

# Check connections
netstat -an | grep 5432
```

2. **Gmail API Issues**
```bash
# Check token validity
python src/cli.py email auth status

# Refresh token
python src/cli.py email auth refresh
```

3. **Memory Issues**
```bash
# Monitor memory usage
free -h
top -p $(pgrep -f hackveda-crawler)

# Adjust memory limits
ulimit -v 2097152  # 2GB virtual memory limit
```

4. **Log Analysis**
```bash
# Check application logs
tail -f logs/crawler.log
grep ERROR logs/*.log

# Check system logs
journalctl -u hackveda-crawler -f
```

### 13. Maintenance

#### Regular Maintenance Tasks

```bash
# Weekly maintenance script
tee /home/hackveda/maintenance.sh > /dev/null <<EOF
#!/bin/bash
cd /home/hackveda/hackveda-crawler
source venv/bin/activate

# Update dependencies
pip install --upgrade -r requirements.txt

# Clean old data
python src/cli.py db cleanup --retention-days 90

# Optimize database
python src/cli.py db optimize

# Generate reports
python src/cli.py export --format csv --output weekly_report.csv

# Health check
python src/cli.py health
EOF

# Schedule weekly maintenance
echo "0 2 * * 0 /home/hackveda/maintenance.sh" | crontab -
```

This deployment guide covers various scenarios from local development to production-scale deployments. Choose the appropriate method based on your requirements and infrastructure.
