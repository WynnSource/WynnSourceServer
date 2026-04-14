from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.sentry import sentry_enabled

SCHEDULER = AsyncIOScheduler()

if sentry_enabled():
    import sentry_sdk as sentry

    def sentry_listener(event: JobExecutionEvent):
        sentry.capture_exception(event.exception)

    SCHEDULER.add_listener(sentry_listener, EVENT_JOB_ERROR)


__all__ = ["SCHEDULER"]
