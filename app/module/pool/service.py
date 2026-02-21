from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scheduler import SCHEDULER
from app.module.pool.schema import PoolSubmissionSchema


async def submit_pool_data(session: AsyncSession, data: PoolSubmissionSchema):
    # TODO: Implement logic to save the submitted pool data to the database and trigger any necessary processing.
    pass


@SCHEDULER.scheduled_job(
    IntervalTrigger(minutes=20),
    id="compute_pool_consensus",
    misfire_grace_time=60,  # Allow a 1-minute grace period for missed executions
    coalesce=True,  # Coalesce multiple missed executions into one
)
def compute_pool_consensus():
    # TODO: Implement logic to compute consensus data for active pools based on recent submissions
    pass
