from pydantic import Field
from pydantic_settings import BaseSettings


class SentryConfig(BaseSettings):
    """
    Sentry configuration.
    """

    dsn: str | None = Field(alias="WCS_SENTRY_DSN", default=None)
    environment: str = Field(alias="WCS_SENTRY_ENVIRONMENT", default="local")
    traces_sample_rate: float = Field(alias="WCS_SENTRY_TRACES_SAMPLE_RATE", default=0.1)
    profiles_sample_rate: float = Field(alias="WCS_SENTRY_PROFILES_SAMPLE_RATE", default=0.1)


SENTRY_CONFIG = SentryConfig()
__all__ = [
    "SENTRY_CONFIG",
]
