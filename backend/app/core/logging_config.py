"""
Application-wide logging configuration.
Writes structured logs to console and to a rotating file so issues can be
diagnosed in production without attaching a debugger.
"""
import logging
import logging.handlers
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("sales_bi_platform")
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = Path(settings.LOG_DIR) / "app.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()
