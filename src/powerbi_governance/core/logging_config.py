"""
Structured logging configuration using structlog

Configures application-wide logging with structured output support.
Supports both JSON and text formats, with file and console output.
"""

import logging
import logging.config
import logging.handlers
from pathlib import Path
from typing import Optional

import structlog

from .config import Settings


def configure_logging(settings: Settings) -> None:
    """
    Configure structured logging for the application.
    
    Sets up:
    - Structlog for structured logging
    - JSON or text format based on settings
    - File and console handlers
    - Appropriate log level
    
    Args:
        settings: Application settings containing logging configuration
        
    Example:
        >>> from powerbi_governance.core import Settings, configure_logging
        >>> settings = Settings()
        >>> configure_logging(settings)
    """
    log_level = settings.log_level.upper()
    
    # Create logs directory if it doesn't exist
    if settings.log_file_enabled:
        log_dir = Path(settings.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard logging
    logging.config.dictConfig(_get_logging_config(settings))
    
    # Configure structlog
    processors: list = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _get_logging_config(settings: Settings) -> dict:
    """
    Generate logging configuration dictionary.
    
    Args:
        settings: Application settings
        
    Returns:
        Dictionary with logging configuration
    """
    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "level": settings.log_level.upper(),
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
    }
    
    if settings.log_file_enabled:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level.upper(),
            "formatter": "standard",
            "filename": settings.log_file_path,
            "maxBytes": settings.log_max_bytes,
            "backupCount": settings.log_backup_count,
        }
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": handlers,
        "root": {
            "level": settings.log_level.upper(),
            "handlers": list(handlers.keys()),
        },
        "loggers": {
            "powerbi_governance": {
                "level": settings.log_level.upper(),
                "propagate": True,
            },
            "sqlalchemy.engine": {
                "level": "INFO" if not settings.database_echo else "DEBUG",
                "propagate": False,
            },
            "urllib3": {
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    
    return config


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog BoundLogger instance
        
    Example:
        >>> log = get_logger(__name__)
        >>> log.info("application started")
    """
    return structlog.get_logger(name)
