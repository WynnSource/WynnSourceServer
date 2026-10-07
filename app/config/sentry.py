from pydantic import Field
from pydantic_settings import BaseSettings


class SentryConfig(BaseSettings):
    """
    Sentry configuration.
    """

    dsn: str | None = Field(alias="WCS_SENTRY_DSN", default=None)
    environment: str = Field(alias="WCS_SENTRY_ENVIRONMENT", default="local")
    # Tracing is OpenTelemetry's job; Sentry only profiles. Decided once per
    # process: a sampled process profiles continuously for its whole life.
    profile_session_sample_rate: float = Field(alias="WCS_SENTRY_PROFILE_SESSION_SAMPLE_RATE", default=0.0)


SENTRY_CONFIG = SentryConfig()
__all__ = [
    "SENTRY_CONFIG",
]
