"""
Email template management and rendering.
Handles Jinja2 templating for personalized email content.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from jinja2.exceptions import TemplateError

from ..config import get_config


class EmailTemplateManager:
    """Manages email templates and rendering."""
    
    def __init__(self, config=None, template_dir: str = None):
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        # Set template directory
        self.template_dir = template_dir or "templates"
        if not os.path.isabs(self.template_dir):
            self.template_dir = os.path.join(os.getcwd(), self.template_dir)
        
        # Create template directory if it doesn't exist
        Path(self.template_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['currency'] = self._currency_filter
        self.env.filters['date_format'] = self._date_filter
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates if they don't exist."""
        default_templates = {
            'outreach.html': self._get_outreach_template(),
            'welcome.html': self._get_welcome_template(),
            'follow_up.html': self._get_follow_up_template(),
            'newsletter.html': self._get_newsletter_template()
        }
        
        for template_name, content in default_templates.items():
            template_path = os.path.join(self.template_dir, template_name)
            if not os.path.exists(template_path):
                try:
                    with open(template_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.logger.info(f"Created default template: {template_name}")
                except Exception as e:
                    self.logger.error(f"Failed to create template {template_name}: {e}")
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Render email template with context data."""
        try:
            # Add .html extension if not present
            if not template_name.endswith('.html'):
                template_name += '.html'
            
            # Load template
            template = self.env.get_template(template_name)
            
            # Add default context variables
            full_context = self._get_default_context()
            full_context.update(context)
            
            # Render template
            html_content = template.render(**full_context)
            
            # Extract subject from template (if present)
            subject = self._extract_subject(html_content, full_context)
            
            # Generate text version
            text_content = self._html_to_text(html_content)
            
            return {
                'subject': subject,
                'html_body': html_content,
                'text_body': text_content,
                'template_name': template_name
            }
            
        except TemplateNotFound:
            raise FileNotFoundError(f"Template not found: {template_name}")
        except TemplateError as e:
            raise ValueError(f"Template rendering error: {e}")
        except Exception as e:
            raise Exception(f"Failed to render template {template_name}: {e}")
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default template context variables."""
        return {
            'company_name': getattr(self.config, 'templates', {}).get('variables', {}).get('company_name', 'HackVeda'),
            'sender_name': getattr(self.config, 'templates', {}).get('variables', {}).get('sender_name', 'Marketing Team'),
            'sender_title': getattr(self.config, 'templates', {}).get('variables', {}).get('sender_title', 'Marketing Manager'),
            'website': getattr(self.config, 'templates', {}).get('variables', {}).get('website', 'https://hackveda.com'),
            'current_year': 2024,
            'unsubscribe_url': '#',  # Should be replaced with actual unsubscribe URL
        }
    
    def _extract_subject(self, html_content: str, context: Dict[str, Any]) -> str:
        """Extract subject from template or generate default."""
        # Look for subject in template comments
        import re
        subject_match = re.search(r'<!--\s*SUBJECT:\s*(.+?)\s*-->', html_content, re.IGNORECASE)
        
        if subject_match:
            subject_template = subject_match.group(1)
            # Render subject template
            subject_tmpl = Template(subject_template)
            return subject_tmpl.render(**context)
        
        # Default subject based on template name and context
        template_name = context.get('template_name', 'email')
        company_name = context.get('company_name', 'HackVeda')
        
        if 'outreach' in template_name.lower():
            return f"Partnership Opportunity with {company_name}"
        elif 'welcome' in template_name.lower():
            return f"Welcome to {company_name}!"
        elif 'follow_up' in template_name.lower():
            return f"Following up on our conversation"
        else:
            return f"Message from {company_name}"
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except ImportError:
            # Fallback: simple HTML tag removal
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
    
    def _currency_filter(self, value: float, currency: str = 'USD') -> str:
        """Format currency values."""
        if currency.upper() == 'USD':
            return f"${value:,.2f}"
        else:
            return f"{value:,.2f} {currency}"
    
    def _date_filter(self, value, format: str = '%B %d, %Y') -> str:
        """Format date values."""
        if hasattr(value, 'strftime'):
            return value.strftime(format)
        return str(value)
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        templates = []
        try:
            for file in os.listdir(self.template_dir):
                if file.endswith('.html'):
                    templates.append(file)
        except Exception as e:
            self.logger.error(f"Failed to list templates: {e}")
        
        return sorted(templates)
    
    def validate_template(self, template_name: str, sample_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate template by rendering with sample data."""
        sample_context = sample_context or {
            'recipient_name': 'John Doe',
            'company': 'Example Corp',
            'product': 'Test Product'
        }
        
        try:
            result = self.render_template(template_name, sample_context)
            return {
                'valid': True,
                'rendered_successfully': True,
                'subject_length': len(result['subject']),
                'html_length': len(result['html_body']),
                'text_length': len(result['text_body'])
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _get_outreach_template(self) -> str:
        """Get default outreach email template."""
        return """
<!-- SUBJECT: Partnership Opportunity with {{ company_name }} -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Partnership Opportunity</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f8f9fa; padding: 20px; text-align: center; }
        .content { padding: 20px 0; }
        .footer { background: #f8f9fa; padding: 15px; font-size: 12px; color: #666; }
        .cta-button { display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ company_name }}</h1>
        </div>
        
        <div class="content">
            <p>Hi {% if recipient_name %}{{ recipient_name }}{% else %}there{% endif %},</p>
            
            <p>I hope this email finds you well. I'm {{ sender_name }}, {{ sender_title }} at {{ company_name }}.</p>
            
            <p>I came across {% if company %}{{ company }}{% else %}your website{% endif %} and was impressed by {% if product %}your {{ product }}{% else %}your work{% endif %}. I believe there could be a great opportunity for collaboration between our organizations.</p>
            
            <p>{{ company_name }} specializes in helping businesses like yours achieve better results through innovative solutions. I'd love to discuss how we might work together to:</p>
            
            <ul>
                <li>Increase your online visibility and reach</li>
                <li>Generate more qualified leads</li>
                <li>Improve your conversion rates</li>
            </ul>
            
            <p>Would you be interested in a brief 15-minute call to explore potential synergies? I'm confident we can provide value to {% if company %}{{ company }}{% else %}your business{% endif %}.</p>
            
            <p style="text-align: center;">
                <a href="mailto:{{ sender_email }}?subject=Re: Partnership Opportunity" class="cta-button">Let's Connect</a>
            </p>
            
            <p>Best regards,<br>
            {{ sender_name }}<br>
            {{ sender_title }}<br>
            {{ company_name }}</p>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. All rights reserved.</p>
            <p><a href="{{ unsubscribe_url }}">Unsubscribe</a> | <a href="{{ website }}">Visit our website</a></p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _get_welcome_template(self) -> str:
        """Get default welcome email template."""
        return """
<!-- SUBJECT: Welcome to {{ company_name }}! -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #28a745; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px 0; }
        .footer { background: #f8f9fa; padding: 15px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {{ company_name }}!</h1>
        </div>
        
        <div class="content">
            <p>Hi {{ recipient_name | default('there') }},</p>
            
            <p>Welcome to {{ company_name }}! We're thrilled to have you join our community.</p>
            
            <p>Here's what you can expect from us:</p>
            <ul>
                <li>Regular updates on industry trends</li>
                <li>Exclusive insights and tips</li>
                <li>Early access to new features and products</li>
            </ul>
            
            <p>If you have any questions, feel free to reach out to our team.</p>
            
            <p>Best regards,<br>
            The {{ company_name }} Team</p>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. All rights reserved.</p>
            <p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _get_follow_up_template(self) -> str:
        """Get default follow-up email template."""
        return """
<!-- SUBJECT: Following up on our conversation -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Follow Up</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .content { padding: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <p>Hi {{ recipient_name | default('there') }},</p>
            
            <p>I wanted to follow up on my previous email regarding the partnership opportunity between {{ company_name }} and {% if company %}{{ company }}{% else %}your organization{% endif %}.</p>
            
            <p>I understand you're likely busy, but I believe this collaboration could bring significant value to both our organizations.</p>
            
            <p>Would you have 10 minutes this week for a quick call to discuss the potential benefits?</p>
            
            <p>Looking forward to hearing from you.</p>
            
            <p>Best regards,<br>
            {{ sender_name }}<br>
            {{ company_name }}</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _get_newsletter_template(self) -> str:
        """Get default newsletter template."""
        return """
<!-- SUBJECT: {{ newsletter_title | default('Newsletter from ' + company_name) }} -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px 0; }
        .article { margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }
        .footer { background: #f8f9fa; padding: 15px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ newsletter_title | default('Newsletter') }}</h1>
            <p>{{ newsletter_date | date_format }}</p>
        </div>
        
        <div class="content">
            <p>Hi {{ recipient_name | default('Subscriber') }},</p>
            
            <p>Here are the latest updates from {{ company_name }}:</p>
            
            {% if articles %}
                {% for article in articles %}
                <div class="article">
                    <h3>{{ article.title }}</h3>
                    <p>{{ article.summary }}</p>
                    {% if article.url %}
                    <p><a href="{{ article.url }}">Read more →</a></p>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
            <div class="article">
                <h3>Sample Article Title</h3>
                <p>This is a sample newsletter article. Replace this with your actual content.</p>
            </div>
            {% endif %}
            
            <p>Thank you for being part of our community!</p>
            
            <p>Best regards,<br>
            The {{ company_name }} Team</p>
        </div>
        
        <div class="footer">
            <p>© {{ current_year }} {{ company_name }}. All rights reserved.</p>
            <p><a href="{{ unsubscribe_url }}">Unsubscribe</a> | <a href="{{ website }}">Visit our website</a></p>
        </div>
    </div>
</body>
</html>
        """.strip()
