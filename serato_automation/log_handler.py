# Serato Playlist Automation
# Logging module - file-based debug logging
#
# Generates serato_debug.log next to main.py for easy access.
# The user can open this file and send the contents for debugging.

import os
import sys
import logging


def get_log_file_path() -> str:
    """Return the path for the debug log file (next to main.py)."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        # If inside serato_automation/, go up one level
        if os.path.basename(base) == 'serato_automation':
            base = os.path.dirname(base)
    return os.path.join(base, "serato_debug.log")


def setup_logging() -> logging.Logger:
    """Configure file + console logging. Returns the root 'serato' logger."""
    logger = logging.getLogger('serato')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    log_path = get_log_file_path()

    # File handler: DEBUG level, captures EVERYTHING
    fh = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)-5s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(fh)

    # Console handler: INFO level (visible in start.bat window)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('[%(levelname)-5s] %(message)s'))
    logger.addHandler(ch)

    logger.info("=" * 60)
    logger.info("Serato Playlist Automation - Log di debug")
    logger.info("File log: %s", log_path)
    logger.info("=" * 60)

    return logger
