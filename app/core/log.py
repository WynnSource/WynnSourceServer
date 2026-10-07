import inspect
import logging
import sys
import traceback

import loguru
import orjson
from opentelemetry import trace

from app.config import LOG_CONFIG
from app.utils.redact import redact_url

LOGGER = loguru.logger


def _add_trace_context(record: "loguru.Record") -> None:
    """Attach the active span, so Grafana can jump from a trace to its log lines."""
    ctx = trace.get_current_span().get_span_context()
    if ctx.is_valid:
        trace_id, span_id = trace.format_trace_id(ctx.trace_id), trace.format_span_id(ctx.span_id)
        record["extra"].update(trace_id=trace_id, span_id=span_id, trace=f" trace_id={trace_id} span_id={span_id}")
    else:
        record["extra"]["trace"] = ""


def _json_sink(message: "loguru.Message") -> None:
    record = message.record
    entry: dict[str, object] = {
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
    }
    # trace_id / span_id and anything bound with LOGGER.bind(); "trace" is the text-format suffix.
    entry.update((k, v) for k, v in record["extra"].items() if k != "trace")
    if exc := record["exception"]:
        entry["exception"] = "".join(traceback.format_exception(exc.type, exc.value, exc.traceback))
    sys.stdout.write(orjson.dumps(entry, default=str).decode() + "\n")
    sys.stdout.flush()


LOGGER.remove()
LOGGER.configure(patcher=_add_trace_context)
if LOG_CONFIG.json_output:
    logger_id = LOGGER.add(_json_sink, level=LOG_CONFIG.level, diagnose=False)
else:
    logger_id = LOGGER.add(sys.stdout, level=LOG_CONFIG.level, diagnose=False, format=LOG_CONFIG.format)


def _access_fields(record: logging.LogRecord) -> dict[str, object] | None:
    """
    Fields of a uvicorn access record, logged as ``'%s - "%s %s HTTP/%s" %d'``
    with args (client, method, target, version, status).
    """
    if record.name != "uvicorn.access" or not isinstance(record.args, tuple) or len(record.args) != 5:
        return None
    client, method, target, version, status = record.args
    return {
        "client_address": client,
        "http_method": method,
        # Same rule as the spans: manage endpoints carry user tokens in the query.
        "http_target": redact_url(str(target)),
        "http_version": version,
        "status_code": status,
    }


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

        logger, message = LOGGER, None
        if fields := _access_fields(record):
            logger = LOGGER.bind(**fields)
            message = (
                f'{fields["client_address"]} - "{fields["http_method"]} {fields["http_target"]} '
                f'HTTP/{fields["http_version"]}" {fields["status_code"]}'
            )
        logger.opt(depth=depth, exception=record.exc_info).log(level, message or record.getMessage())


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
