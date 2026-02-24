from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.score import Tier

from .schema import PoolType


@dataclass
class PoolRotation:
    start: datetime
    end: datetime


@dataclass
class PoolConfig:
    interval: timedelta
    anchor: datetime

    def get_rotation(self, time: datetime, shift: int = 0) -> PoolRotation:
        if time.tzinfo is None:
            raise ValueError("The 'time' parameter must be timezone-aware.")

        base_cycles = (time - self.anchor) // self.interval
        target_cycles = base_cycles + shift
        start = self.anchor + (self.interval * target_cycles)

        return PoolRotation(start=start, end=start + self.interval)


GLOBAL_RESET_ANCHOR = datetime(2026, 2, 20, 18, 0, 0, tzinfo=UTC)

POOL_REFRESH_CONFIG = {
    PoolType.LR_ITEM: PoolConfig(
        interval=timedelta(days=7),
        anchor=GLOBAL_RESET_ANCHOR,
    ),
    PoolType.RAID_ASPECT: PoolConfig(
        interval=timedelta(days=7),
        anchor=GLOBAL_RESET_ANCHOR,
    ),
    PoolType.RAID_ITEM: PoolConfig(
        interval=timedelta(days=7),
        anchor=GLOBAL_RESET_ANCHOR,
    ),
}


FUZZY_WINDOW = timedelta(minutes=10)

WEIGHT_MAP: dict[Tier | str, float] = {
    Tier.Rookie: 0.1,
    Tier.Assistant: 0.3,
    Tier.Sentinel: 0.8,
    Tier.Elite: 1.5,
    Tier.Admiral: 3.0,
    Tier.Commander: 5.0,
    Tier.Master: 7.5,
    Tier.Grandmaster: 9.0,
    "max": 10.0,
}

CONSENSUS_THRESHOLD = 0.6
