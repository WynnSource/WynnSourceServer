import inspect
import logging
import sys

import loguru

from app.config import LOG_CONFIG

LOGGER = loguru.logger

LOGGER.remove()
logger_id = LOGGER.add(
    sys.stdout,
    level=LOG_CONFIG.level,
    diagnose=False,
    format=LOG_CONFIG.format,
)


class LoguruHandler(logging.Handler):
    """Redirects logging messages to Loguru's logger."""

    def emit(self, record: logging.LogRecord):
        try:
            level = LOGGER.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        LOGGER.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    logging_root = logging.getLogger()
    logging_root.setLevel(0)
    logging_root.handlers = []

    logging_root.addHandler(LoguruHandler())

    # Remove handlers from all existing loggers to prevent duplicate logs
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


setup_logging()


__all__ = ["LOGGER"]
