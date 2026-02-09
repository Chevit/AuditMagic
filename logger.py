"""Centralized logging configuration for AuditMagic."""
import logging
import os
from datetime import datetime

import os
from pathlib import Path
import sys

def get_app_data_dir():
    """Get platform-specific application data directory."""
    if sys.platform == "win32":
        # Windows: C:\Users\Username\AppData\Local\AuditMagic
        base = os.environ.get('LOCALAPPDATA') or os.path.expanduser("~")
        return os.path.join(base, "AuditMagic")
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/AuditMagic
        return os.path.expanduser("~/Library/Application Support/AuditMagic")
    else:
        # Linux: ~/.local/share/AuditMagic or ~/.audit_magic
        return os.path.expanduser("~/.local/share/AuditMagic")

APP_DATA_DIR = get_app_data_dir()
LOGS_DIR = os.path.join(APP_DATA_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file with timestamp
LOG_FILE = os.path.join(LOGS_DIR, f"audit_magic_{datetime.now().strftime('%Y%m%d')}.log")


def setup_logger(name: str = "AuditMagic") -> logging.Logger:
    """Set up and return a logger instance.

    Args:
        name: Logger name (default: "AuditMagic")

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # File handler - detailed logs
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        # Console handler - important messages only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# Create default logger
logger = setup_logger()
