import os
import uuid
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import DropAggregation, View
from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import TELEMETRY_CONFIG
from app.schemas.constants import __VERSION__
from app.utils.redact import redact_query, redact_url

TRACER = trace.get_tracer("wynnsource")

# Health probes would otherwise produce a root trace every few seconds.
_EXCLUDED_URLS = "/healthz,/readyz"

# Process-level runtime metrics only; host metrics come from node-exporter.
_SYSTEM_METRICS: dict[str, list[str] | None] = {
    "process.cpu.time": ["user", "system"],
    "process.memory.usage": None,
    "process.memory.virtual": None,
    "process.thread.count": None,
    "cpython.gc.collections": None,
}

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None


def _server_request_hook(span: Span, scope: dict[str, Any]) -> None:
    if not span.is_recording() or not scope.get("query_string"):
        return
    attributes = getattr(span, "attributes", None) or {}
    for key in ("http.target", "http.url", "url.full"):
        if isinstance(value := attributes.get(key), str):
            span.set_attribute(key, redact_url(value))
    if isinstance(value := attributes.get("url.query"), str):
        span.set_attribute("url.query", redact_query(value))


def _resource() -> Resource:
    # Resource.create() merges OTEL_RESOURCE_ATTRIBUTES and OTEL_SERVICE_NAME on top of these.
    resource = Resource.create({SERVICE_NAME: "wynnsource-server", SERVICE_VERSION: __VERSION__})
    if SERVICE_INSTANCE_ID not in resource.attributes:
        # Every replica pushes its own cumulative counters; without a unique
        # instance id two pods would overwrite each other's series.
        resource = resource.merge(Resource({SERVICE_INSTANCE_ID: str(uuid.uuid4())}))
    return resource


def setup_telemetry(app: FastAPI) -> bool:
    """
    Configure OpenTelemetry tracing and metrics, exported over OTLP/HTTP to
    ``OTEL_EXPORTER_OTLP_ENDPOINT``. No-op when the endpoint is unset.

    The sampler is the SDK default (``OTEL_TRACES_SAMPLER``, default
    ``parentbased_always_on``): requests follow the caller's decision, jobs
    and other root spans are always recorded.
    """
    global _tracer_provider, _meter_provider
    if not TELEMETRY_CONFIG.enabled:
        return False

    # Stable HTTP semantic conventions (http.route, url.path, ...), matching Traefik's spans.
    os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")

    resource = _resource()

    _tracer_provider = TracerProvider(resource=resource)
    _tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(_tracer_provider)

    _meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
        # HTTP RED metrics come from Tempo span metrics and Traefik.
        views=[View(instrument_name="http.server.*", aggregation=DropAggregation())],
    )
    metrics.set_meter_provider(_meter_provider)

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=_EXCLUDED_URLS,
        server_request_hook=_server_request_hook,
        exclude_spans=["receive", "send"],
    )
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    SystemMetricsInstrumentor(config=_SYSTEM_METRICS).instrument()
    return True


def instrument_engine(engine: AsyncEngine) -> None:
    if _tracer_provider is None:
        return
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, enable_commenter=False)


def shutdown_telemetry() -> None:
    """Flush pending spans and metrics; called on shutdown so rolling updates don't lose the last batch."""
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
    if _meter_provider is not None:
        _meter_provider.shutdown()


__all__ = [
    "TRACER",
    "instrument_engine",
    "setup_telemetry",
    "shutdown_telemetry",
]
