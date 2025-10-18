#!/bin/bash

# HackVeda Crawler Demo Script
# This script demonstrates the basic functionality of the crawler

set -e

echo "🚀 HackVeda Crawler Demo"
echo "========================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.10+ to continue."
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    print_error "pip is not installed. Please install pip to continue."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
print_success "Dependencies installed"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs data secrets templates

# Copy example configuration if config doesn't exist
if [ ! -f "config.yml" ]; then
    print_status "Creating configuration file..."
    cp examples/config.example.yml config.yml
    print_warning "Please edit config.yml with your settings before running in production"
fi

# Initialize database
print_status "Initializing database..."
python src/cli.py db init
print_success "Database initialized"

# Run health check
print_status "Running health check..."
python src/cli.py health

echo ""
echo "🎯 Demo Tasks"
echo "============="

# Demo 1: Crawl keywords
print_status "Demo 1: Crawling keywords..."
python src/cli.py crawl keywords \
    --keywords "productivity tools" \
    --keywords "project management" \
    --max-results 5 \
    --session-name "demo_crawl_$(date +%Y%m%d_%H%M%S)" \
    --output "demo_results.csv"

if [ $? -eq 0 ]; then
    print_success "Crawling completed successfully"
    print_status "Results saved to demo_results.csv"
else
    print_error "Crawling failed"
fi

# Demo 2: Show database stats
print_status "Demo 2: Database statistics..."
python src/cli.py db stats

# Demo 3: Test email configuration (if configured)
print_status "Demo 3: Testing email configuration..."
python src/cli.py email test

echo ""
echo "📊 Demo Results"
echo "==============="

# Show crawl results if file exists
if [ -f "demo_results.csv" ]; then
    print_status "Sample crawl results:"
    head -n 6 demo_results.csv | column -t -s ','
    echo ""
    
    # Count total results
    total_results=$(wc -l < demo_results.csv)
    total_results=$((total_results - 1)) # Subtract header
    print_success "Total results crawled: $total_results"
fi

# Show log files
if [ -d "logs" ] && [ "$(ls -A logs)" ]; then
    print_status "Log files created:"
    ls -la logs/
fi

echo ""
echo "🎉 Demo Complete!"
echo "================="
print_success "HackVeda Crawler demo completed successfully"
echo ""
echo "Next steps:"
echo "1. Edit config.yml with your Gmail API credentials"
echo "2. Run 'python src/cli.py auth setup' to configure Gmail authentication"
echo "3. Try crawling with your own keywords"
echo "4. Set up email templates and send test emails"
echo "5. Schedule recurring crawls with the job scheduler"
echo ""
echo "For more information, see README.md"

# Deactivate virtual environment
deactivate
