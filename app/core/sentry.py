import logging

import sentry_sdk as sentry
import sentry_sdk.profiler as sentry_profiler
from fastapi import HTTPException
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration
from sentry_sdk.integrations.otlp import OTLPIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event, Hint

from app.config import SENTRY_CONFIG
from app.schemas.constants import __VERSION__


def sentry_enabled() -> bool:
    return SENTRY_CONFIG.dsn is not None


def filter_http_exception(event: Event, hint: Hint) -> Event | None:
    _exc_type, exc_value, _traceback = hint.get("exc_info", (None, None, None))

    if isinstance(exc_value, HTTPException):
        if exc_value.status_code < 500:
            return None

    return event


def init_sentry() -> bool:
    if not SENTRY_CONFIG.dsn:
        return False
    sentry.init(
        dsn=SENTRY_CONFIG.dsn,
        environment=SENTRY_CONFIG.environment,
        release=__VERSION__,
        # No traces_sample_rate: tracing is OpenTelemetry's. Errors and logs
        # carry the active OTel trace id through OTLPIntegration.
        profile_session_sample_rate=SENTRY_CONFIG.profile_session_sample_rate,
        profile_lifecycle="manual",
        send_default_pii=False,
        before_send=filter_http_exception,
        integrations=[
            AsyncioIntegration(),
            LoguruIntegration(event_level=logging.CRITICAL),
            SqlalchemyIntegration(),
            RedisIntegration(),
            # Spans are exported by app.core.telemetry, and the default
            # Sentry propagator only speaks sentry-trace, which would break
            # continuation of Cloudflare's W3C traceparent.
            OTLPIntegration(setup_otlp_traces_exporter=False, setup_propagator=False),
        ],
        disabled_integrations=[LoggingIntegration()],
        enable_logs=True,
    )
    return True


def start_profiling() -> None:
    """Start continuous profiling; a no-op unless this process was sampled by profile_session_sample_rate."""
    if sentry_enabled():
        sentry_profiler.start_profiler()


def stop_profiling() -> None:
    if sentry_enabled():
        sentry_profiler.stop_profiler()


__all__ = [
    "init_sentry",
    "sentry_enabled",
    "start_profiling",
    "stop_profiling",
]
