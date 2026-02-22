from dataclasses import dataclass
from enum import Enum

from apscheduler.triggers.cron import CronTrigger

from app.core.scheduler import SCHEDULER


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
    pass


async def calculate_quality_factor(): ...


async def calculate_activity_factor(): ...
