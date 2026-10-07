"""
Application metrics. Instruments are created against the global meter, which
forwards to the real provider once ``setup_telemetry`` has run and is a no-op
otherwise.

Attribute values must stay low-cardinality: route templates, enum values and
fixed job names only; never user ids, IPs or tokens.
"""

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from opentelemetry import metrics
from starlette.requests import Request

from app.core.telemetry import TRACER

_meter = metrics.get_meter("wynnsource")

_SECONDS_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120]
_COUNT_BUCKETS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]

SUBMISSIONS = _meter.create_counter(
    "wcs.submissions",
    unit="{submission}",
    description="Submitted entries by module and outcome (accepted, rejected, unchanged).",
)
SUBMISSION_ITEMS = _meter.create_histogram(
    "wcs.submission.items",
    unit="{item}",
    description="Entries per submission request.",
    explicit_bucket_boundaries_advisory=_COUNT_BUCKETS,
)

CONSENSUS_RUNS = _meter.create_counter(
    "wcs.consensus.runs",
    unit="{run}",
    description="Consensus computations by kind and status.",
)
CONSENSUS_DURATION = _meter.create_histogram(
    "wcs.consensus.duration",
    unit="s",
    description="Consensus computation time.",
    explicit_bucket_boundaries_advisory=_SECONDS_BUCKETS,
)
CONSENSUS_PENDING = _meter.create_gauge(
    "wcs.consensus.pending",
    unit="{row}",
    description="Rows flagged needs_recalc when a consensus run started.",
)

JOB_RUNS = _meter.create_counter(
    "wcs.job.runs",
    unit="{run}",
    description="Scheduler job executions by status (ok, error, skipped = another replica holds the lock).",
)
JOB_DURATION = _meter.create_histogram(
    "wcs.job.duration",
    unit="s",
    description="Scheduler job execution time.",
    explicit_bucket_boundaries_advisory=_SECONDS_BUCKETS,
)
JOB_LAST_SUCCESS = _meter.create_gauge(
    "wcs.job.last_success",
    unit="s",
    description="Unix time of the last successful run of a scheduler job.",
)

CACHE_REQUESTS = _meter.create_counter(
    "wcs.cache.requests",
    unit="{request}",
    description="Response cache lookups by route and result (hit, miss).",
)
RATE_LIMITED = _meter.create_counter(
    "wcs.rate_limited",
    unit="{request}",
    description="Requests rejected by the rate limiter, by route and key type (ip, user).",
)


def route_template(request: Request) -> str:
    """The matched route's path template, e.g. ``/api/v2/pool/pools/{pool_type}/{region}``."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


@contextmanager
def consensus_run(kind: str, attributes: dict[str, str] | None = None) -> Iterator[Callable[[int], int]]:
    """
    Span ``consensus <kind>`` plus run/duration metrics around a consensus
    computation. Yields ``record(n)``, to be called with the number of rows
    that were flagged for recalculation; it returns ``n``.
    """
    attrs = {"kind": kind, **(attributes or {})}
    start = time.perf_counter()
    status = "error"
    span_attributes = {f"wcs.{k}": v for k, v in attrs.items()}
    with TRACER.start_as_current_span(f"consensus {kind}", attributes=span_attributes) as span:

        def record(rows: int) -> int:
            span.set_attribute("wcs.rows", rows)
            CONSENSUS_PENDING.set(rows, attrs)
            return rows

        try:
            yield record
            status = "ok"
        finally:
            CONSENSUS_RUNS.add(1, {**attrs, "status": status})
            CONSENSUS_DURATION.record(time.perf_counter() - start, attrs)


__all__ = [
    "CACHE_REQUESTS",
    "CONSENSUS_DURATION",
    "CONSENSUS_PENDING",
    "CONSENSUS_RUNS",
    "JOB_DURATION",
    "JOB_LAST_SUCCESS",
    "JOB_RUNS",
    "RATE_LIMITED",
    "SUBMISSIONS",
    "SUBMISSION_ITEMS",
    "consensus_run",
    "route_template",
]
