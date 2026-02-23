import logging
import sys
from app.config import settings

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

        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] : %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
    return logger
