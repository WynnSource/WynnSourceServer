from datetime import time, timedelta

from .schema import LootPoolType

POOL_REFRESH_CONFIG = {
    LootPoolType.ITEM: {
        "interval": timedelta(days=7),
        "anchor": time(0, 0, 0),
    },
    LootPoolType.RAID_ASPECT: {
        "interval": timedelta(hours=24),
        "anchor": time(0, 0, 0),
    },
    LootPoolType.RAID_TOME: {
        "interval": timedelta(hours=24),
        "anchor": time(0, 0, 0),
    },
}

FUZZY_WINDOW = timedelta(minutes=10)

SCORE_CONFIG = {
    "min": -10000,
    "max": 10000,
    # TODO more sophisticated scoring config
}
