import datetime
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from apscheduler.triggers.cron import CronTrigger

from app.core.scheduler import SCHEDULER

if TYPE_CHECKING:
    from app.module.pool.model import Pool

# Scoring configuration
QUALITY_WEIGHT = 0.7
ACTIVITY_WEIGHT = 0.3
ACTIVITY_THRESHOLD = 0.5
SCORE_MIN = -10000
SCORE_MAX = 10000


@dataclass
class ScoreRange:
    min: int
    max: int


class Tier(Enum):
    Infamous = (
        -10000,
        -9501,
        100,
        "The absolute enemy of WynnSource, universally recognized for unparalleled toxicity.",
    )
    Nemesis = (
        -9500,
        -7001,
        75,
        "A master of disruption, carrying a dark legacy of hostility toward the community.",
    )
    Corruptor = (
        -7000,
        -3501,
        60,
        "A commander of chaos, systematically polluting the WynnSource database.",
    )
    Defiler = (-3500, -1501, 45, "A major detriment to the community, leaving a trail of harmful contributions.")
    Saboteur = (-1500, -601, 30, "A notorious contributor who actively diminishes the quality of WynnSource.")
    Vandal = (-600, -201, 20, "A disruptive member known for repeatedly ignoring submission guidelines.")
    Outcast = (-200, -51, 10, "A user whose frequent low-quality submissions have alienated the community.")
    Troublemaker = (-50, -1, 10, "A newcomer who has stumbled by submitting unhelpful content.")

    Rookie = (0, 50, 20, "The newcomer to the WynnSource community.")
    Assistant = (51, 200, 15, "A regular contributor who has shown dedication.")
    Sentinel = (201, 600, 12, "A vigilant guardian of quality, standing watch over the integrity of our data.")
    Elite = (601, 1500, 9, "A battle-tested veteran whose submissions are considered the gold standard.")
    Admiral = (1501, 3500, 6, "A visionary leader, safely navigating the community through oceans of information.")
    Commander = (3501, 7000, 4, "A seasoned tactician whose exceptional directives steer the course of WynnSource.")
    Master = (7001, 9500, 2, "A legendary scholar whose vast wisdom forms the very foundation of the community.")
    Grandmaster = (
        9501,
        10000,
        2,
        "A living myth; their unparalleled legacy will echo through WynnSource forever.",
    )

    def __init__(self, min_score: int, max_score: int, daily_base: int, description: str):
        self.score_range = ScoreRange(min_score, max_score)
        self.daily_base = daily_base
        self.description = description

    @classmethod
    def get_by_score(cls, score: int) -> "Tier":
        for tier in cls:
            if tier.score_range.min <= score <= tier.score_range.max:
                return tier
        raise ValueError(f"Score {score} is out of bounds for all tiers.")

    def next(self) -> "Tier | None":
        members = list(Tier)
        index = members.index(self)
        if index < len(members) - 1:
            return members[index + 1]
        return None

    def previous(self) -> "Tier | None":
        members = list(Tier)
        index = members.index(self)
        if index > 0:
            return members[index - 1]
        return None

    def score_to_next_tier(self, score: int) -> int:
        next_tier = self.next()
        if next_tier is None:
            return 0  # Already at max tier
        return next_tier.score_range.min - score


@SCHEDULER.scheduled_job(
    CronTrigger(hour=0, minute=0),  # Run daily at midnight
    id="update_user_scores",
    misfire_grace_time=60,
    coalesce=True,
)
async def update_user_scores():
    # Lazy imports to avoid circular dependency (pool/config.py imports Tier)
    from app.core.db import get_session
    from app.core.log import LOGGER
    from app.core.security.model import UserRepository
    from app.module.pool.config import POOL_REFRESH_CONFIG
    from app.module.pool.model import PoolRepository
    from app.module.pool.schema import PoolType

    async with get_session() as session:
        # 1. Fetch all current rotation pools across all pool types
        all_current_pools: list[Pool] = []
        now = datetime.datetime.now(tz=datetime.UTC)
        for pool_type in PoolType:
            rotation = POOL_REFRESH_CONFIG[pool_type].get_rotation(now)
            pool_repo = PoolRepository(session)
            pools = await pool_repo.list_pools(
                pool_type=pool_type,
                rotation_start=rotation.start,
            )
            all_current_pools.extend(pools)

        if not all_current_pools:
            LOGGER.info("No active pools for current rotation, skipping score update")
            return

        # 2. Collect all unique user_ids who submitted to any current pool
        user_ids: set[int] = set()
        for pool in all_current_pools:
            for sub in pool.submissions:
                user_ids.add(sub.user_id)

        if not user_ids:
            LOGGER.info("No submissions found for current rotation, skipping score update")
            return

        # 3. Load users
        user_repo = UserRepository(session)
        users = await user_repo.get_users_by_ids(list(user_ids))

        # 4. Calculate and apply score deltas
        for user in users:
            quality = calculate_quality_factor(user.id, all_current_pools)
            activity = calculate_activity_factor(user.id, all_current_pools)

            tier = Tier.get_by_score(user.score)
            delta = tier.daily_base * (quality * QUALITY_WEIGHT + activity * ACTIVITY_WEIGHT)
            delta = round(delta)
            delta = max(-tier.daily_base, min(tier.daily_base, delta))

            new_score = max(SCORE_MIN, min(SCORE_MAX, user.score + delta))
            user.score = new_score

            LOGGER.debug(
                f"User {user.id}: quality={quality:.3f}, activity={activity:.3f}, delta={delta}, new_score={new_score}"
            )

        LOGGER.info(f"Updated scores for {len(users)} users")


def calculate_quality_factor(user_id: int, pools: list["Pool"]) -> float:
    """Compare user submissions against consensus. Returns [-1.0, 1.0]."""
    pool_qualities: list[float] = []

    for pool in pools:
        if not pool.consensus_data or pool.confidence <= 0:
            continue

        user_sub = None
        for sub in pool.submissions:
            if sub.user_id == user_id:
                user_sub = sub
                break

        if user_sub is None:
            continue

        user_items = Counter(user_sub.item_data)
        consensus_items = Counter(pool.consensus_data)

        all_keys = set(user_items.keys()) | set(consensus_items.keys())
        if not all_keys:
            continue

        intersection = sum(min(user_items[k], consensus_items[k]) for k in all_keys)
        union = sum(max(user_items[k], consensus_items[k]) for k in all_keys)

        similarity = intersection / union if union > 0 else 0.0
        pool_quality = (2.0 * similarity - 1.0) * pool.confidence
        pool_qualities.append(pool_quality)

    if not pool_qualities:
        return 0.0

    return sum(pool_qualities) / len(pool_qualities)


def calculate_activity_factor(user_id: int, pools: list["Pool"]) -> float:
    """Measure participation breadth. Returns [0.0, 1.0]."""
    total_pools = len(pools)
    if total_pools == 0:
        return 0.0

    user_pools = sum(1 for pool in pools if any(sub.user_id == user_id for sub in pool.submissions))

    ratio = user_pools / total_pools
    return min(1.0, ratio / ACTIVITY_THRESHOLD)
