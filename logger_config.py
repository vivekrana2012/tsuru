"""Centralized logging configuration for Tsuru RSS Feed Manager"""
import logging
import sys

# Shared format configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logging(name: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with consistent formatting
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(level)
        logger.propagate = False  # Prevent duplicate logs
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Formatter with timestamp
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger


def configure_uvicorn_logging():
    """
    Configure uvicorn loggers to use consistent formatting
    Should be called before starting uvicorn server
    """
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        force=True  # Override any existing configuration
    )
    
    # Configure uvicorn's access logger
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.propagate = False  # Prevent duplicate logs
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    uvicorn_access.addHandler(handler)
    
    # Configure uvicorn's error logger
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers = []
    uvicorn_error.propagate = False  # Prevent duplicate logs
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    uvicorn_error.addHandler(handler)
