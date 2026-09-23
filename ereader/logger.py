import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(config):
    """
    Configures the logging system for the application.
    Logs to both console and a rotating file.
    
    Args:
        config: The Config object containing logging settings.
    """
    # Create logs directory
    if os.name == 'nt':
        log_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / "ereader"
    else:
        log_dir = Path.home() / ".local" / "state" / "ereader"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ereader.log"

    # Define log format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.logging.level.upper(), logging.INFO))

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # File Handler (Rotating: 5MB x 3 backups)
    if config.logging.file_log:
        try:
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=5 * 1024 * 1024, 
                backupCount=3, 
                encoding='utf-8'
            )
            file_handler.setFormatter(log_format)
            logger.addHandler(file_handler)
            logging.info(f"Logging to file initialized: {log_file}")
        except Exception as e:
            # Fallback to console only if file logging fails
            logging.error(f"Failed to initialize file logging: {e}")

    logging.info("Logging system ready.")

__all__ = ["setup_logging"]
