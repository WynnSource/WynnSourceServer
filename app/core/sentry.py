import logging

import sentry_sdk as sentry
from fastapi import HTTPException
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration
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
        traces_sample_rate=SENTRY_CONFIG.traces_sample_rate,
        profiles_sample_rate=SENTRY_CONFIG.profiles_sample_rate,
        send_default_pii=False,
        before_send=filter_http_exception,
        integrations=[
            AsyncioIntegration(),
            LoguruIntegration(event_level=logging.CRITICAL),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
    )
    return True


__all__ = [
    "init_sentry",
    "sentry_enabled",
]
