import inspect
import logging
import sys

import loguru

logger = loguru.logger


class LoguruHandler(logging.Handler):
    """Redirects logging messages to Loguru's logger."""

    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


default_format: str = "<g>{time:YY-MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>{name}:{line}</u></c> | {message}"

logger.remove()
logger_id = logger.add(
    sys.stdout,
    level=0,
    diagnose=False,
    format=default_format,
)

__all__ = ["logger"]
