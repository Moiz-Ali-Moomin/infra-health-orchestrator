import logging
import sys
import contextvars
from app.config import settings

# Global context variables for non-repudiation tracking
principal_id_ctx = contextvars.ContextVar("principal_id", default="anonymous")
correlation_id_ctx = contextvars.ContextVar("correlation_id", default="-")

class ContextFilter(logging.Filter):
    """Injects async contextvars into the log record."""
    def filter(self, record):
        record.principal = principal_id_ctx.get()
        record.correlation = correlation_id_ctx.get()
        return True

def setup_logger(name: str) -> logging.Logger:
    """
    Configures and returns a structured logger for the application.
    Outputs to stdout for containerized environments.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if not logger.handlers:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # Inject context filter
        logger.addFilter(ContextFilter())

        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [user:%(principal)s] [tx:%(correlation)s] [%(name)s] : %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
    return logger
