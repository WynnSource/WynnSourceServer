from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

GAMBIT_COUNT = 4
GAMBIT_SEPARATOR = "|"
GAMBIT_REGION = "global"
GAMBIT_RESET_UTC_HOUR = 17
FUZZY_WINDOW = timedelta(minutes=30)
CONSENSUS_THRESHOLD = 0.6


@dataclass
class GambitRotation:
    start: datetime
    end: datetime


def get_gambit_rotation(time: datetime, shift: int = 0) -> GambitRotation:
    """Get the daily gambit rotation window for the given timestamp.

    Gambits rotate daily at 17:00 UTC (12:00 EST / 13:00 EDT).
    """
    if time.tzinfo is None:
        raise ValueError("The 'time' parameter must be timezone-aware.")

    utc_time = time.astimezone(UTC)

    today_reset = datetime(utc_time.year, utc_time.month, utc_time.day, GAMBIT_RESET_UTC_HOUR, tzinfo=UTC)

    if utc_time < today_reset:
        today_reset -= timedelta(days=1)

    if shift != 0:
        today_reset += timedelta(days=shift)

    next_reset = today_reset + timedelta(days=1)

    return GambitRotation(start=today_reset, end=next_reset)
