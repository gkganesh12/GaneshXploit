"""
Command Line Interface for HackVeda Crawler.
Provides CLI commands for crawling, email sending, database management, and more.
"""

import os
import sys
import json
import csv
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import get_config, reload_config
from app.database.db import get_db_manager
from app.crawler.google_serp import GoogleSERPCrawler
from app.crawler.demo_crawler import DemoCrawler
from app.email.gmail_api import GmailService, GmailAuthManager
from app.email.smtp_client import EmailServiceManager
from app.jobs.scheduler import JobScheduler


# Initialize console for rich output
console = Console()


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "crawler.log"),
            logging.StreamHandler()
        ]
    )


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--log-level', default='INFO', help='Logging level')
@click.pass_context
def cli(ctx, config, log_level):
    """HackVeda Crawler - Google Crawler + Gmail Email Sender"""
    ctx.ensure_object(dict)
    
    # Setup logging
    setup_logging(log_level)
    
    # Load configuration
    if config:
        ctx.obj['config'] = reload_config(config)
    else:
        ctx.obj['config'] = get_config()
    
    console.print(Panel.fit(
        "[bold blue]HackVeda Crawler[/bold blue]\n"
        "Google Crawler + Gmail Email Sender for Digital Marketing",
        border_style="blue"
    ))


@cli.group()
def crawl():
    """Crawling commands"""
    pass


@crawl.command()
@click.option('--keywords', '-k', multiple=True, required=True, help='Keywords to crawl')
@click.option('--max-results', '-m', default=10, help='Maximum results per keyword')
@click.option('--session-name', '-s', help='Name for this crawl session')
@click.option('--output', '-o', help='Output CSV file path')
@click.option('--demo', is_flag=True, help='Use demo mode (generates sample data)')
@click.pass_context
def keywords(ctx, keywords, max_results, session_name, output, demo):
    """Crawl Google search results for keywords"""
    
    # Prepare keywords list
    keyword_list = list(keywords)
    
    if not keyword_list:
        return
    
    console.print(f"[green]Crawling {len(keyword_list)} keywords with max {max_results} results each[/green]")
    
    # Initialize crawler
    config = ctx.obj['config']
    if demo:
        console.print("[yellow]Using Demo Mode - Generating sample data[/yellow]")
        crawler = DemoCrawler(config)
    else:
        crawler = GoogleSERPCrawler(config)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Crawling keywords...", total=len(keyword_list))
        
        all_results = []
        
        for keyword in keyword_list:
            progress.update(task, description=f"Crawling: {keyword}")
            
            try:
                results = crawler.crawl_keyword(keyword, max_results)
                all_results.extend(results)
                
                console.print(f"  ✓ {keyword}: {len(results)} results")
                
            except Exception as e:
                console.print(f"  ✗ {keyword}: Error - {e}")
            
            progress.advance(task)
    
    console.print(f"\n[green]Crawling completed! Total results: {len(all_results)}[/green]")
    
    # Store in database
    if all_results:
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            from app.database.db import CrawlSessionRepository, SearchResultRepository
            
            crawl_repo = CrawlSessionRepository(session)
            result_repo = SearchResultRepository(session)
            
            # Create session
            session_name = session_name or f"cli_crawl_{len(keyword_list)}_keywords"
            crawl_session = crawl_repo.create(
                session_name=session_name,
                keywords=keyword_list,
                config={'max_results': max_results, 'source': 'cli'}
            )
            
            # Store results
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
            
            crawl_repo.update_status(crawl_session.id, 'completed')
            crawl_session.total_results = len(all_results)
            
            console.print(f"[green]Results stored in database (Session ID: {crawl_session.id})[/green]")
    
    # Export to CSV if requested
    if output and all_results:
        export_results_to_csv(all_results, output)
        console.print(f"[green]Results exported to: {output}[/green]")


@crawl.command()
@click.argument('session_id', type=int)
def status(session_id):
    """Check status of a crawl session"""
    
    db_manager = get_db_manager()
    
    with db_manager.get_session() as session:
        from app.database.models import CrawlSession
        
        crawl_session = session.query(CrawlSession).filter(
            CrawlSession.id == session_id
        ).first()
        
        if not crawl_session:
            console.print(f"[red]Crawl session not found: {session_id}[/red]")
            return
        
        # Create status table
        table = Table(title=f"Crawl Session {session_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Name", crawl_session.session_name)
        table.add_row("Status", crawl_session.status)
        table.add_row("Keywords", ", ".join(crawl_session.keywords))
        table.add_row("Start Time", str(crawl_session.start_time))
        table.add_row("End Time", str(crawl_session.end_time) if crawl_session.end_time else "N/A")
        table.add_row("Total Results", str(crawl_session.total_results))
        
        if crawl_session.error_message:
            table.add_row("Error", crawl_session.error_message)
        
        console.print(table)


@cli.group()
def email():
    """Email commands"""
    pass


@email.group()
def auth():
    """Gmail authentication commands"""
    pass


@auth.command()
@click.pass_context
def setup(ctx):
    """Setup Gmail OAuth2 authentication"""
    
    config = ctx.obj['config']
    
    console.print("[yellow]Setting up Gmail OAuth2 authentication...[/yellow]")
    
    # Check if credentials file exists
    creds_path = config.email.gmail.credentials_path
    if not os.path.exists(creds_path):
        console.print(f"[red]Error: Credentials file not found: {creds_path}[/red]")
        console.print("\n[yellow]Please follow these steps:[/yellow]")
        console.print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        console.print("2. Create a new project or select existing one")
        console.print("3. Enable Gmail API")
        console.print("4. Create OAuth2 credentials (Desktop application)")
        console.print(f"5. Download credentials.json to {creds_path}")
        return
    
    try:
        auth_manager = GmailAuthManager(config)
        creds = auth_manager.get_credentials()
        
        if creds and creds.valid:
            console.print("[green]✓ Gmail authentication setup successful![/green]")
            
            # Test connection
            gmail_service = GmailService(config)
            if gmail_service.test_connection():
                console.print("[green]✓ Gmail API connection test passed![/green]")
            else:
                console.print("[yellow]⚠ Gmail API connection test failed[/yellow]")
        else:
            console.print("[red]✗ Failed to setup Gmail authentication[/red]")
    
    except Exception as e:
        console.print(f"[red]Error setting up Gmail authentication: {e}[/red]")


@auth.command()
@click.pass_context
def status(ctx):
    """Check Gmail authentication status"""
    
    config = ctx.obj['config']
    auth_manager = GmailAuthManager(config)
    
    status_info = auth_manager.check_credentials_status()
    
    table = Table(title="Gmail Authentication Status")
    table.add_column("Property", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("Credentials File", "✓" if status_info['has_credentials_file'] else "✗")
    table.add_row("Token File", "✓" if status_info['has_token_file'] else "✗")
    table.add_row("Valid Credentials", "✓" if status_info['is_valid'] else "✗")
    
    if status_info.get('expires_at'):
        table.add_row("Expires At", status_info['expires_at'])
    
    if status_info.get('error'):
        table.add_row("Error", status_info['error'])
    
    console.print(table)


@email.command()
@click.option('--to', required=True, help='Recipient email address')
@click.option('--subject', default='Test Email from HackVeda Crawler', help='Email subject')
@click.option('--template', help='Template name to use')
@click.option('--context', help='JSON context for template rendering')
@click.pass_context
def send(ctx, to, subject, template, context):
    """Send a test email"""
    
    config = ctx.obj['config']
    
    try:
        email_service = EmailServiceManager(config)
        
        if template:
            # Send templated email
            template_context = {}
            if context:
                template_context = json.loads(context)
            
            # Add default context
            template_context.setdefault('recipient_name', to.split('@')[0])
            template_context.setdefault('company', 'Your Company')
            
            from app.email.gmail_api import GmailService
            gmail_service = GmailService(config)
            
            result = gmail_service.send_templated_email(
                to_address=to,
                template_name=template,
                context=template_context
            )
        else:
            # Send simple email
            body = f"""
This is a test email from HackVeda Crawler.

If you received this email, your email configuration is working correctly.

Best regards,
HackVeda Crawler Team
            """.strip()
            
            result = email_service.send_email(
                to_address=to,
                subject=subject,
                body=body
            )
        
        if result['success']:
            console.print(f"[green]✓ Email sent successfully to {to}[/green]")
            if result.get('message_id'):
                console.print(f"Message ID: {result['message_id']}")
        else:
            console.print(f"[red]✗ Failed to send email: {result.get('error')}[/red]")
    
    except Exception as e:
        console.print(f"[red]Error sending email: {e}[/red]")


@email.command()
@click.pass_context
def test(ctx):
    """Test email service configuration"""
    
    config = ctx.obj['config']
    email_service = EmailServiceManager(config)
    
    console.print("[yellow]Testing email services...[/yellow]")
    
    results = email_service.test_services()
    
    table = Table(title="Email Service Test Results")
    table.add_column("Service", style="cyan")
    table.add_column("Available", style="yellow")
    table.add_column("Working", style="green")
    table.add_column("Error", style="red")
    
    for service, info in results.items():
        available = "✓" if info['available'] else "✗"
        working = "✓" if info['working'] else "✗"
        error = info.get('error', '')
        
        table.add_row(service.upper(), available, working, error)
    
    console.print(table)


@cli.group()
def db():
    """Database commands"""
    pass


@db.command()
@click.pass_context
def init(ctx):
    """Initialize database tables"""
    
    try:
        db_manager = get_db_manager()
        db_manager.init_database()
        console.print("[green]✓ Database initialized successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")


@db.command()
@click.pass_context
def stats(ctx):
    """Show database statistics"""
    
    try:
        db_manager = get_db_manager()
        stats = db_manager.get_stats()
        
        table = Table(title="Database Statistics")
        table.add_column("Table", style="cyan")
        table.add_column("Count", style="green")
        
        for key, value in stats.items():
            if isinstance(value, int):
                table.add_row(key.replace('_', ' ').title(), str(value))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting database stats: {e}[/red]")


@db.command()
@click.confirmation_option(prompt='Are you sure you want to cleanup old data?')
@click.option('--retention-days', default=90, help='Data retention period in days')
@click.pass_context
def cleanup(ctx, retention_days):
    """Clean up old data"""
    
    try:
        db_manager = get_db_manager()
        db_manager.cleanup_old_data(retention_days)
        console.print(f"[green]✓ Cleaned up data older than {retention_days} days[/green]")
    except Exception as e:
        console.print(f"[red]Error cleaning up database: {e}[/red]")


@cli.group()
def export():
    """Export commands"""
    pass


@export.command()
@click.option('--session-id', type=int, help='Specific crawl session to export')
@click.option('--output', '-o', required=True, help='Output CSV file')
@click.option('--format', 'export_format', default='csv', help='Export format (csv)')
@click.pass_context
def results(ctx, session_id, output, export_format):
    """Export crawl results to CSV"""
    
    db_manager = get_db_manager()
    
    with db_manager.get_session() as session:
        from app.database.models import SearchResult
        
        query = session.query(SearchResult)
        
        if session_id:
            query = query.filter(SearchResult.crawl_session_id == session_id)
        
        results = query.all()
        
        if not results:
            console.print("[yellow]No results found to export[/yellow]")
            return
        
        # Export to CSV
        with open(output, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'title', 'url', 'snippet', 'domain', 'rank',
                'source_keyword', 'crawl_timestamp', 'response_time'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow({
                    'id': result.id,
                    'title': result.title,
                    'url': result.url,
                    'snippet': result.snippet,
                    'domain': result.domain,
                    'rank': result.rank,
                    'source_keyword': result.source_keyword,
                    'crawl_timestamp': result.crawl_timestamp.isoformat(),
                    'response_time': result.response_time
                })
        
        console.print(f"[green]✓ Exported {len(results)} results to {output}[/green]")


@cli.group()
def scheduler():
    """Job scheduler commands"""
    pass


@scheduler.command()
@click.pass_context
def start(ctx):
    """Start the job scheduler"""
    
    config = ctx.obj['config']
    job_scheduler = JobScheduler(config)
    
    console.print("[yellow]Starting job scheduler...[/yellow]")
    
    try:
        job_scheduler.start()
        console.print("[green]✓ Job scheduler started successfully[/green]")
        
        # Keep running
        console.print("[blue]Press Ctrl+C to stop the scheduler[/blue]")
        
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping scheduler...[/yellow]")
            job_scheduler.stop()
            console.print("[green]✓ Scheduler stopped[/green]")
    
    except Exception as e:
        console.print(f"[red]Error starting scheduler: {e}[/red]")


@scheduler.command()
@click.pass_context
def status(ctx):
    """Show scheduler status"""
    
    config = ctx.obj['config']
    job_scheduler = JobScheduler(config)
    
    status_info = job_scheduler.get_job_status()
    
    console.print(f"[cyan]Scheduler Running:[/cyan] {status_info['scheduler_running']}")
    console.print(f"[cyan]Total Jobs:[/cyan] {status_info['total_jobs']}")
    
    if status_info['jobs']:
        table = Table(title="Scheduled Jobs")
        table.add_column("Job ID", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Next Run", style="green")
        table.add_column("Trigger", style="blue")
        
        for job in status_info['jobs']:
            table.add_row(
                job['id'],
                job['name'],
                job['next_run'] or 'N/A',
                job['trigger']
            )
        
        console.print(table)


@cli.command()
@click.pass_context
def health(ctx):
    """Check system health"""
    
    config = ctx.obj['config']
    
    console.print("[yellow]Checking system health...[/yellow]")
    
    health_status = {}
    
    # Database health
    try:
        db_manager = get_db_manager()
        health_status['database'] = db_manager.health_check()
    except Exception as e:
        health_status['database'] = False
        health_status['database_error'] = str(e)
    
    # Email service health
    try:
        email_service = EmailServiceManager(config)
        email_results = email_service.test_services()
        health_status['gmail_api'] = email_results['gmail_api']['working']
        health_status['smtp'] = email_results['smtp']['working']
    except Exception as e:
        health_status['email_error'] = str(e)
    
    # Create health table
    table = Table(title="System Health Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Database
    db_status = "✓ Healthy" if health_status.get('database') else "✗ Unhealthy"
    db_details = health_status.get('database_error', '')
    table.add_row("Database", db_status, db_details)
    
    # Gmail API
    gmail_status = "✓ Working" if health_status.get('gmail_api') else "✗ Not Working"
    table.add_row("Gmail API", gmail_status, "")
    
    # SMTP
    smtp_status = "✓ Working" if health_status.get('smtp') else "✗ Not Working"
    table.add_row("SMTP", smtp_status, "")
    
    console.print(table)
    
    # Overall status
    overall_healthy = health_status.get('database', False)
    if overall_healthy:
        console.print("[green]✓ System is healthy[/green]")
    else:
        console.print("[red]✗ System has issues[/red]")


def export_results_to_csv(results, output_file):
    """Export search results to CSV file."""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'title', 'url', 'snippet', 'domain', 'rank',
            'source_keyword', 'crawl_timestamp', 'response_time'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'title': result.title,
                'url': result.url,
                'snippet': result.snippet,
                'domain': result.domain,
                'rank': result.rank,
                'source_keyword': result.result_metadata.get('keyword', ''),
                'crawl_timestamp': result.crawl_timestamp.isoformat(),
                'response_time': result.response_time
            })


if __name__ == '__main__':
    cli()
