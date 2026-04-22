import base64
import datetime
from collections import defaultdict

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.log import LOGGER
from app.core.scheduler import SCHEDULER
from app.core.score import Tier
from app.core.security.model import User
from wynnsource import WynnSourceItem

from .config import CONSENSUS_THRESHOLD, FUZZY_WINDOW, POOL_REFRESH_CONFIG, WEIGHT_MAP
from .model import Pool, PoolRepository, PoolSubmission, PoolSubmissionRepository
from .schema import VALID_REGIONS, LootPoolRegion, PoolSubmissionSchema, PoolType, RaidRegion


async def submit_pool_data(session: AsyncSession, data: PoolSubmissionSchema, user: User):
    # validation
    #  pool id check
    if data.region not in VALID_REGIONS[data.pool_type]:
        raise ValueError(f"Invalid region {data.region} for pool type {data.pool_type}")

    # client timestamp check (we allow skew up to 10 minutes)
    now = datetime.datetime.now(tz=datetime.UTC)
    if abs(now - data.client_timestamp) > datetime.timedelta(minutes=10):
        raise ValueError("Client timestamp is too far from server time")

    #  items check and decoding
    items_decoded: list[bytes] = []
    for item in data.items:
        try:
            decoded = base64.b64decode(item)
            tmp = WynnSourceItem.FromString(decoded)  # noqa: F841
            # we just want to make sure it can is a valid item
            items_decoded.append(decoded)
        except Exception:
            LOGGER.debug(
                f"Invalid item {item} in submission from user"
                + f"{user.id} for pool {data.pool_type}:{data.region}:{data.page}"
            )
            continue  # we silently skip invalid items

    if not items_decoded:
        raise ValueError("No valid items provided in the submission")

    poolRepo = PoolRepository(session)
    submissionRepo = PoolSubmissionRepository(session)

    pool = await poolRepo.get_or_create_pool(
        pool_type=data.pool_type,
        region=data.region,
        page=data.page,
        rotation=POOL_REFRESH_CONFIG[data.pool_type].get_rotation(data.client_timestamp),
    )

    # no pool binded to submission yet
    fuzzy = (
        abs(pool.rotation_start - data.client_timestamp) < FUZZY_WINDOW
        or abs(pool.rotation_end - data.client_timestamp) < FUZZY_WINDOW
    )
    submission = PoolSubmission(
        user_id=user.id,
        client_timestamp=data.client_timestamp,
        item_data=items_decoded,
        weight=calculate_submission_weight(user, fuzzy),
        fuzzy=fuzzy,
        mod_version=data.mod_version,
    )

    #  user can have one submission of each pool for each rotation
    existingSubmission = await submissionRepo.get_user_submission_for_rotation(user.id, pool.id)

    is_first_of_rotation = existingSubmission is None

    if existingSubmission is not None:
        # we delete it infavor of the new submission
        await submissionRepo.delete(existingSubmission)

    submission.rotation = pool
    await submissionRepo.save(submission)

    # Force UPDATE via SQL so recalc's FOR UPDATE lock serializes us, and the
    # flag flip is guaranteed to hit the DB even when the loaded value was
    # already True (ORM dirty tracking would skip the write).
    await session.execute(sql_update(Pool).where(Pool.id == pool.id).values(needs_recalc=True))

    if is_first_of_rotation:
        _schedule_instant_pool_recalc(data.pool_type, data.region, data.page, pool.rotation_start)


def _schedule_instant_pool_recalc(
    pool_type: PoolType, region: str, page: int, rotation_start: datetime.datetime
) -> None:
    """Schedule a one-off recalc for a specific pool on first-of-rotation submission.

    Debounced by job id: concurrent first-submissions to the same pool coalesce.
    Delayed by 2s so the triggering transaction commits before recalc reads.
    """
    run_date = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=2)
    SCHEDULER.add_job(
        compute_pool_consensus_for_pool,
        args=[pool_type, region, page],
        trigger=DateTrigger(run_date=run_date),
        id=f"instant_recalc:pool:{pool_type.value}:{region}:{page}:{rotation_start.isoformat()}",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
        max_instances=1,
    )


def calculate_submission_weight(user: User, fuzzy: bool = False) -> float:
    if user.score < 0:
        # For users with negative scores,
        #  we directly map (-10000, 0) to (0.01, 0.1) on a logarithmic scale
        return max(0.0001, min(0.1, 0.1 * (10 ** (user.score / 10000))))
    else:
        tier = Tier.get_by_score(user.score)
        weight_range = WEIGHT_MAP[tier]
        next_tier = tier.next()
        next_weight_range = WEIGHT_MAP[next_tier] if next_tier else WEIGHT_MAP["max"]

        weight = weight_range + (next_weight_range - weight_range) * (
            (user.score - tier.score_range.min) / (tier.score_range.max - tier.score_range.min)
        )
        return weight * (0.5 if fuzzy else 1.0)


@SCHEDULER.scheduled_job(
    IntervalTrigger(minutes=20),
    id="compute_pool_consensus",
    misfire_grace_time=60,
    coalesce=True,  # Coalesce multiple missed executions into one
)
async def compute_pool_consensus() -> int:
    total = 0
    for pool_type in PoolType:
        total += await compute_pool_consensus_for_pool(pool_type)
    return total


BOOST_INTERVAL = datetime.timedelta(minutes=2)
BOOST_LEAD = datetime.timedelta(minutes=30)
BOOST_TAIL = datetime.timedelta(minutes=30)


def _boost_job_id(pool_type: PoolType) -> str:
    return f"compute_pool_consensus_boost:{pool_type.value}"


@SCHEDULER.scheduled_job(
    CronTrigger(hour=0, minute=5),
    id="schedule_pool_boosts",
    misfire_grace_time=600,
    coalesce=True,
)
async def schedule_pool_boosts() -> None:
    for pool_type in PoolType:
        await _schedule_boost_for_pool(pool_type)


async def _schedule_boost_for_pool(pool_type: PoolType) -> None:
    config = POOL_REFRESH_CONFIG[pool_type]
    now = datetime.datetime.now(datetime.UTC)
    rotation = config.get_rotation(now)

    prev_tail_end = rotation.start + BOOST_TAIL
    if now < prev_tail_end:
        reset_at = rotation.start
    else:
        reset_at = rotation.end

    boost_start = reset_at - BOOST_LEAD
    boost_end = reset_at + BOOST_TAIL

    SCHEDULER.add_job(
        compute_pool_consensus_for_pool,
        args=[pool_type],
        trigger=IntervalTrigger(
            minutes=int(BOOST_INTERVAL.total_seconds() // 60),
            start_date=max(boost_start, now),
            end_date=boost_end,
        ),
        id=_boost_job_id(pool_type),
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
        max_instances=1,
    )


async def compute_pool_consensus_for_pool(
    pool_type: PoolType,
    region: str | None = None,
    page: int | None = None,
) -> int:
    async with get_session() as session:
        # Step 1: Fetch all active pools that need consensus computation
        poolRepo = PoolRepository(session)
        active_pools = await poolRepo.list_pools(
            pool_type=pool_type,
            region=region,
            page=page,
            rotation_start=POOL_REFRESH_CONFIG[pool_type].get_rotation(datetime.datetime.now(tz=datetime.UTC)).start,
            needs_recalc=True,
            for_update=True,
        )
        # The active pools should only differ in (region, page)

        # Step 2: For each pool, compute consensus and update the pool record
        for pool in active_pools:
            submissions = pool.submissions

            item_weights: dict[tuple[bytes, int], float] = defaultdict(float)

            for submission in submissions:
                local_counts = defaultdict(int)

                for item_data in submission.item_data:
                    local_counts[item_data] += 1
                    occurrence = local_counts[item_data]

                    item_weights[(item_data, occurrence)] += submission.weight

            if not item_weights:
                pool.consensus_data = []
                pool.confidence = 0.0
                pool.needs_recalc = False
                continue

            highest_weight = max(item_weights.values())

            if highest_weight <= 0:
                pool.consensus_data = []
                pool.confidence = 0.0
                pool.needs_recalc = False
                continue

            threshold = highest_weight * CONSENSUS_THRESHOLD

            consensus_items = []
            consensus_weights = []

            for (item, _), weight in item_weights.items():
                if weight >= threshold:
                    consensus_items.append(item)
                    consensus_weights.append(weight)

            pool.consensus_data = consensus_items
            confidence = (
                sum(consensus_weights) / (highest_weight * len(consensus_weights)) if consensus_weights else 0.0
            )
            pool.confidence = round(confidence, 4)
            pool.needs_recalc = False

        return len(active_pools)


type ConsensusByPage = dict[int, tuple[list[bytes], float]]


async def get_pool_consensus(
    session: AsyncSession,
    pool_type: PoolType,
    region: LootPoolRegion | RaidRegion,
    rotation_start: datetime.datetime,
) -> ConsensusByPage:

    if region not in VALID_REGIONS[pool_type]:
        raise ValueError(f"Invalid region {region} for pool type {pool_type}")

    poolRepo = PoolRepository(session)

    pool = await poolRepo.list_pools(pool_type=pool_type, region=region, rotation_start=rotation_start, order_by="page")
    if not pool:
        return {}

    consensus_by_page: ConsensusByPage = {}
    for p in pool:
        consensus_by_page[p.page] = p.consensus_data, p.confidence

    return consensus_by_page
