from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SERVER_TZ = ZoneInfo("America/New_York")

GAMBIT_COUNT = 4
GAMBIT_SEPARATOR = "|"
GAMBIT_REGION = "global"
FUZZY_WINDOW = timedelta(minutes=30)
CONSENSUS_THRESHOLD = 0.6


@dataclass
class GambitRotation:
    start: datetime
    end: datetime


def get_gambit_rotation(time: datetime, shift: int = 0) -> GambitRotation:
    """Get the daily gambit rotation window for the given timestamp.

    Gambits rotate daily at EST/EDT noon (12:00 America/New_York).
    """
    if time.tzinfo is None:
        raise ValueError("The 'time' parameter must be timezone-aware.")

    local_time = time.astimezone(SERVER_TZ)

    # Today's reset at noon EST
    today_reset = datetime.combine(local_time.date(), datetime.min.time(), tzinfo=SERVER_TZ)
    today_reset += timedelta(hours=12)

    if local_time < today_reset:
        today_reset -= timedelta(days=1)

    if shift != 0:
        today_reset += timedelta(days=shift)

    next_reset = today_reset + timedelta(days=1)

    return GambitRotation(start=today_reset, end=next_reset)
