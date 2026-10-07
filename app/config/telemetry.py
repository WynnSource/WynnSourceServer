from pydantic import Field
from pydantic_settings import BaseSettings


class TelemetryConfig(BaseSettings):
    """
    OpenTelemetry switch. Everything else (service name, resource attributes,
    sampler, export interval) comes from the standard ``OTEL_*`` variables,
    which the SDK reads itself.
    """

    otlp_endpoint: str | None = Field(alias="OTEL_EXPORTER_OTLP_ENDPOINT", default=None)
    sdk_disabled: bool = Field(alias="OTEL_SDK_DISABLED", default=False)

    @property
    def enabled(self) -> bool:
        return self.otlp_endpoint is not None and not self.sdk_disabled


TELEMETRY_CONFIG = TelemetryConfig()
__all__ = [
    "TELEMETRY_CONFIG",
]
