import datetime
import os
import socket
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.base import BaseTrigger
from opentelemetry.instrumentation.utils import suppress_instrumentation
from opentelemetry.trace import Status, StatusCode

from app.core.db.redis import RedisClient
from app.core.log import LOGGER
from app.core.metrics import JOB_DURATION, JOB_LAST_SUCCESS, JOB_RUNS
from app.core.sentry import sentry_enabled
from app.core.telemetry import TRACER

SCHEDULER = AsyncIOScheduler()

# Identifies the lock holder; the pod name in Kubernetes.
_HOLDER = os.environ.get("K8S_POD_NAME") or socket.gethostname()


async def _acquire_lock(key: str, ttl: datetime.timedelta) -> bool:
    """
    Claim ``key`` for ``ttl`` across replicas. The lock is never released early:
    interval triggers are anchored to each replica's start time, so their fire
    times are offset; releasing after the run would let the other replica run
    the same period again. A TTL just under the period gives one run per period.
    Fails open (runs the job) if Redis is unreachable.
    """
    try:
        # The lock is bookkeeping, not part of the job's trace.
        with suppress_instrumentation():
            acquired = await RedisClient.get_instance().set(
                f"wcs:job-lock:{key}", _HOLDER, nx=True, px=int(ttl.total_seconds() * 1000)
            )
    except Exception as e:
        LOGGER.warning(f"Job lock {key} unavailable, running without it: {e}")
        return True
    return bool(acquired)


def instrument_job[**P, R](
    job: str,
    fn: Callable[P, Awaitable[R]],
    *,
    lock_ttl: datetime.timedelta | None = None,
    lock_key: str | None = None,
) -> Callable[P, Awaitable[R | None]]:
    """
    Wrap a scheduler job: optional cross-replica lock, a root span ``job <job>``,
    run/duration/last-success metrics, and Sentry capture of failures.

    Jobs that only touch process-local state (in-memory caches, registering
    local jobs) must run on every replica and take no lock.
    """
    attributes = {"job": job}

    @wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        if lock_ttl is not None and not await _acquire_lock(lock_key or job, lock_ttl):
            JOB_RUNS.add(1, {**attributes, "status": "skipped"})
            return None

        start = time.perf_counter()
        with TRACER.start_as_current_span(
            f"job {job}", attributes={"wcs.job": job}, record_exception=False, set_status_on_exception=False
        ) as span:
            try:
                result = await fn(*args, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, type(e).__name__))
                JOB_RUNS.add(1, {**attributes, "status": "error"})
                if sentry_enabled():
                    import sentry_sdk as sentry

                    sentry.capture_exception(e)
                raise
            finally:
                JOB_DURATION.record(time.perf_counter() - start, attributes)

        JOB_RUNS.add(1, {**attributes, "status": "ok"})
        JOB_LAST_SUCCESS.set(time.time(), attributes)
        return result

    return wrapper


def scheduled_job[**P, R](
    trigger: BaseTrigger,
    *,
    id: str,
    lock_ttl: datetime.timedelta | None = None,
    **job_kwargs: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Register an instrumented job and return the original function unchanged,
    so direct callers (e.g. the manual recalc endpoints) bypass the lock.
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        SCHEDULER.add_job(instrument_job(id, fn, lock_ttl=lock_ttl), trigger, id=id, **job_kwargs)
        return fn

    return decorator


__all__ = ["SCHEDULER", "instrument_job", "scheduled_job"]
