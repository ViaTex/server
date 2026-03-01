import logging
import structlog
from structlog.processors import (
    TimeStamper,
    StackInfoRenderer,
    format_exc_info,
    UnicodeDecoder,
)
from structlog.stdlib import add_log_level, add_logger_name


def setup_logging():
    """Configure structlog for JSON-formatted contextual logging"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )
    
    structlog.configure(
        processors=[
            add_log_level,
            add_logger_name,
            TimeStamper(fmt="iso"),
            StackInfoRenderer(),
            format_exc_info,
            UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a logger instance"""
    return structlog.get_logger(name)
