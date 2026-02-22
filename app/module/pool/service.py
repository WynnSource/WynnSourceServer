import base64
import datetime
from collections import defaultdict

from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.scheduler import SCHEDULER
from app.core.score import Tier
from app.core.security.model import User
from wynnsource import WynnSourceItem

from .config import CONSENSUS_THRESHOLD, FUZZY_WINDOW, POOL_REFRESH_CONFIG, WEIGHT_MAP
from .model import PoolRepository, PoolSubmission, PoolSubmissionRepository
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
        user=user,
        client_timestamp=data.client_timestamp,
        item_data=items_decoded,
        weight=calculate_submission_weight(user, fuzzy),
        fuzzy=fuzzy,
        mod_version=data.mod_version,
    )

    #  user can have one submission of each pool for each rotation
    existingSubmission = await submissionRepo.get_user_submission_for_rotation(user.id, pool.id)

    if existingSubmission is not None:
        # if the new submission is different from the existing one, we replace it
        # the existing one still stay in the user's submission history
        if existingSubmission.item_data != submission.item_data:
            existingSubmission.item_data = submission.item_data
            existingSubmission.client_timestamp = submission.client_timestamp
            existingSubmission.weight = submission.weight
            existingSubmission.mod_version = submission.mod_version
            pool.needs_recalc = True
    else:
        submission.rotation = pool
        pool.submission_count += 1
        pool.needs_recalc = True
        await submissionRepo.save(submission)


def calculate_submission_weight(user: User, fuzzy: bool = False) -> float:
    if user.score < 0:
        # For users with negative scores, we directly map (-10000, 0) to (0.01, 0.1) on a logarithmic scale
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
    misfire_grace_time=60,  # Allow a 1-minute grace period for missed executions
    coalesce=True,  # Coalesce multiple missed executions into one
)
async def compute_pool_consensus():
    for pool_type in PoolType:
        await compute_pool_consensus_for_pool(pool_type)


async def compute_pool_consensus_for_pool(pool_type: PoolType):
    async with get_session() as session:
        # Step 1: Fetch all active pools that need consensus computation
        poolRepo = PoolRepository(session)
        active_pools = await poolRepo.list_pools(
            pool_type=pool_type,
            rotation_start=POOL_REFRESH_CONFIG[pool_type].get_rotation(datetime.datetime.now(tz=datetime.UTC)).start,
            needs_recalc=True,
        )
        # The active pools should only differ in (region, page)

        # Step 2: For each pool, compute consensus and update the pool record
        for pool in active_pools:
            submissions = pool.submissions

            item_weights: dict[bytes, float] = defaultdict(float)

            for submission in submissions:
                for item_data in submission.item_data:
                    item_weights[item_data] += submission.weight

            if not item_weights:
                pool.consensus_data = []
                pool.confidence = 0.0
                pool.needs_recalc = False
                continue

            highest_weight = max(item_weights.values())

            if highest_weight <= 0:
                pool.consensus_data = list(item_weights.keys())
                pool.confidence = 0.0
                pool.needs_recalc = False
                continue

            threshold = highest_weight * CONSENSUS_THRESHOLD

            consensus_items = []
            consensus_weights = []

            for item, weight in item_weights.items():
                if weight >= threshold:
                    consensus_items.append(item)
                    consensus_weights.append(weight)

            pool.consensus_data = consensus_items
            confidence = (
                sum(consensus_weights) / (highest_weight * len(consensus_weights)) if consensus_weights else 0.0
            )
            pool.confidence = round(confidence, 4)
            pool.needs_recalc = False


type ConsensusByPage = dict[int, tuple[list[bytes], float]]


async def get_pool_consensus(
    session: AsyncSession, pool_type: PoolType, region: LootPoolRegion | RaidRegion, rotation_start: datetime.datetime
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
