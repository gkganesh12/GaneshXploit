"""
Configuration management for HackVeda Crawler.
Handles loading and validation of configuration from YAML files and environment variables.
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CrawlerConfig:
    """Crawler configuration settings."""
    mode: str = "light"  # light | browser
    user_agent: str = "HackVedaBot/1.0"
    delay_min: int = 2
    delay_max: int = 6
    max_results: int = 10
    respect_robots_txt: bool = True
    timeout: int = 30
    max_retries: int = 3


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str = "sqlite:///data/crawler.db"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False


@dataclass
class GmailConfig:
    """Gmail API configuration settings."""
    credentials_path: str = "secrets/credentials.json"
    token_path: str = "secrets/token.json"
    from_address: str = ""
    from_name: str = ""
    daily_limit: int = 500
    rate_limit: int = 10  # emails per minute


@dataclass
class EmailConfig:
    """Email configuration settings."""
    provider: str = "sendgrid"  # sendgrid | gmail_api | smtp
    gmail: GmailConfig = field(default_factory=GmailConfig)
    
    # SendGrid settings
    sendgrid_api_key: str = ""
    from_email: str = ""
    from_name: str = "HackVeda Crawler"
    
    # SMTP settings (fallback)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True


@dataclass
class AppConfig:
    """Application configuration settings."""
    concurrency: int = 3
    log_level: str = "INFO"
    data_retention_days: int = 90


@dataclass
class Config:
    """Main configuration class."""
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    app: AppConfig = field(default_factory=AppConfig)


class ConfigManager:
    """Configuration manager for loading and validating settings."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[Config] = None
    
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        possible_paths = [
            "config.yml",
            "config.yaml",
            "examples/config.example.yml",
            os.path.expanduser("~/.hackveda/config.yml"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Return default path if none found
        return "config.yml"
    
    def load_config(self) -> Config:
        """Load configuration from file and environment variables."""
        if self._config is not None:
            return self._config
        
        # Load from YAML file
        config_data = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Create config objects
        self._config = self._create_config_from_dict(config_data)
        return self._config
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            'DATABASE_URL': ['database', 'url'],
            'GMAIL_FROM_ADDRESS': ['email', 'gmail', 'from_address'],
            'GMAIL_FROM_NAME': ['email', 'gmail', 'from_name'],
            'CRAWLER_USER_AGENT': ['crawler', 'user_agent'],
            'LOG_LEVEL': ['app', 'log_level'],
            'CONCURRENCY': ['app', 'concurrency'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate to the nested dictionary
                current = config_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert value to appropriate type
                if env_var in ['CONCURRENCY']:
                    value = int(value)
                elif env_var in ['LOG_LEVEL']:
                    value = value.upper()
                
                current[config_path[-1]] = value
        
        return config_data
    
    def _create_config_from_dict(self, data: Dict[str, Any]) -> Config:
        """Create Config object from dictionary data."""
        # Create crawler config
        crawler_data = data.get('crawler', {})
        crawler_config = CrawlerConfig(
            mode=crawler_data.get('mode', 'light'),
            user_agent=crawler_data.get('user_agent', 'HackVedaBot/1.0'),
            delay_min=crawler_data.get('delay_min', 2),
            delay_max=crawler_data.get('delay_max', 6),
            max_results=crawler_data.get('max_results', 10),
            respect_robots_txt=crawler_data.get('respect_robots_txt', True),
            timeout=crawler_data.get('timeout', 30),
            max_retries=crawler_data.get('max_retries', 3),
        )
        
        # Create database config
        db_data = data.get('database', {})
        database_config = DatabaseConfig(
            url=db_data.get('url', 'sqlite:///data/crawler.db'),
            pool_size=db_data.get('pool_size', 10),
            max_overflow=db_data.get('max_overflow', 20),
            echo=db_data.get('echo', False),
        )
        
        # Create email config
        email_data = data.get('email', {})
        gmail_data = email_data.get('gmail', {})
        gmail_config = GmailConfig(
            credentials_path=gmail_data.get('credentials_path', 'secrets/credentials.json'),
            token_path=gmail_data.get('token_path', 'secrets/token.json'),
            from_address=gmail_data.get('from_address', ''),
            from_name=gmail_data.get('from_name', ''),
            daily_limit=gmail_data.get('daily_limit', 500),
            rate_limit=gmail_data.get('rate_limit', 10),
        )
        # Override with environment variables
        import os
        email_config = EmailConfig(
            provider=os.getenv('EMAIL_PROVIDER', email_data.get('provider', 'sendgrid')),
            gmail=gmail_config,
            sendgrid_api_key=os.getenv('SENDGRID_API_KEY', email_data.get('sendgrid_api_key', '')),
            from_email=os.getenv('FROM_EMAIL', email_data.get('from_email', '')),
            from_name=os.getenv('FROM_NAME', email_data.get('from_name', 'HackVeda Crawler')),
            smtp_host=os.getenv('SMTP_HOST', email_data.get('smtp_host', 'smtp.gmail.com')),
            smtp_port=int(os.getenv('SMTP_PORT', email_data.get('smtp_port', 587))),
            smtp_username=os.getenv('SMTP_USERNAME', email_data.get('smtp_username', '')),
            smtp_password=os.getenv('SMTP_PASSWORD', email_data.get('smtp_password', '')),
            smtp_use_tls=os.getenv('SMTP_USE_TLS', str(email_data.get('smtp_use_tls', True))).lower() == 'true',
        )
        
        # Create app config
        app_data = data.get('app', {})
        app_config = AppConfig(
            concurrency=app_data.get('concurrency', 3),
            log_level=app_data.get('log_level', 'INFO'),
            data_retention_days=app_data.get('data_retention_days', 90),
        )
        
        return Config(
            crawler=crawler_config,
            database=database_config,
            email=email_config,
            app=app_config,
        )
    
    def validate_config(self, config: Config) -> bool:
        """Validate configuration settings."""
        errors = []
        
        # Validate crawler config
        if config.crawler.mode not in ['light', 'browser']:
            errors.append("crawler.mode must be 'light' or 'browser'")
        
        if config.crawler.delay_min < 0 or config.crawler.delay_max < config.crawler.delay_min:
            errors.append("Invalid delay configuration")
        
        # Validate email config
        if config.email.provider not in ['sendgrid', 'gmail_api', 'smtp']:
            errors.append("email.provider must be 'sendgrid', 'gmail_api' or 'smtp'")
        
        if config.email.provider == 'gmail_api':
            if not config.email.gmail.from_address:
                errors.append("gmail.from_address is required for Gmail API")
        
        # Validate app config
        if config.app.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            errors.append("Invalid log level")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return True
    
    def get_config(self) -> Config:
        """Get validated configuration."""
        config = self.load_config()
        self.validate_config(config)
        return config


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the global configuration."""
    return config_manager.get_config()


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file."""
    global config_manager
    config_manager = ConfigManager(config_path)
    return config_manager.get_config()
