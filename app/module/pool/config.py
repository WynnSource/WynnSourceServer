from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.score import Tier

from .schema import PoolType

SERVER_TZ = ZoneInfo("America/New_York")


@dataclass
class PoolRotation:
    start: datetime
    end: datetime


@dataclass
class PoolConfig:
    weekday: int
    winter_utc_hour: int
    summer_utc_hour: int

    def _is_dst(self, d: date) -> bool:
        noon = datetime.combine(d, datetime.min.time().replace(hour=12), tzinfo=SERVER_TZ)
        return bool(noon.dst())

    def _get_exact_reset_time(self, d: date) -> datetime:
        hour = self.summer_utc_hour if self._is_dst(d) else self.winter_utc_hour
        return datetime(d.year, d.month, d.day, hour, tzinfo=UTC)

    def get_rotation(self, time: datetime, shift: int = 0) -> PoolRotation:
        if time.tzinfo is None:
            raise ValueError("The 'time' parameter must be timezone-aware.")

        local_time = time.astimezone(SERVER_TZ)

        days_since_target = (local_time.weekday() - self.weekday) % 7
        candidate_date = local_time.date() - timedelta(days=days_since_target)

        current_reset = self._get_exact_reset_time(candidate_date)

        if time < current_reset:
            candidate_date -= timedelta(days=7)
            current_reset = self._get_exact_reset_time(candidate_date)

        if shift != 0:
            candidate_date += timedelta(days=7 * shift)
            current_reset = self._get_exact_reset_time(candidate_date)

        next_reset = self._get_exact_reset_time(candidate_date + timedelta(days=7))

        return PoolRotation(start=current_reset, end=next_reset)


POOL_REFRESH_CONFIG = {
    PoolType.LR_ITEM: PoolConfig(weekday=4, winter_utc_hour=19, summer_utc_hour=18),
    PoolType.RAID_ASPECT: PoolConfig(weekday=4, winter_utc_hour=18, summer_utc_hour=17),
    PoolType.RAID_ITEM: PoolConfig(weekday=4, winter_utc_hour=18, summer_utc_hour=17),
}

FUZZY_WINDOW = timedelta(minutes=90)

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
