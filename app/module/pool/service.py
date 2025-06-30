from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.db import get_session
from app.domain.enums import LootPoolType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .domain.request import CrowdSourceLootPoolData
from .model import LootPoolData, add_loot_pools, get_loot_pools


def get_current_rotation_date():
    # Get the last Friday, 7:00:00 PM GMT
    return int(get_current_rotation_datetime().timestamp())  # Convert to seconds


def get_current_rotation_datetime() -> datetime:
    now = datetime.now(timezone.utc)
    last_friday = now - timedelta(days=(now.weekday() + 2) % 7)
    last_friday = last_friday.replace(hour=19, minute=0, second=0, microsecond=0)
    return last_friday


async def crowdsource_loot_pool(
    type: LootPoolType,
    location: str,
    page: int,
    item_data: CrowdSourceLootPoolData,
    session: async_sessionmaker[AsyncSession],
) -> None:
    # Use the simplest update logic for the time being
    pool = await get_loot_pools(session, get_current_rotation_date())
    if pool is None:
        # Create a new pool if it doesn't exist
        pool = LootPoolData(
            starting_date=get_current_rotation_date(),
            lr_item_pool={"loot": {}},
            raid_aspect_pool={"loot": {}},
            raid_tome_pool={"loot": {}},
        )
    items = item_data.model_dump(exclude_none=True, exclude_unset=True, include={"shiny", "items"})
    match type:
        case LootPoolType.ITEM:
            if not pool.lr_item_pool["loot"].get(location):
                pool.lr_item_pool["loot"][location] = {}
            pool.lr_item_pool["loot"][location][page] = rotation_strategy(
                previous=pool.lr_item_pool["loot"].get(location, {}).get(page, {}),
                now=items,
            )
        case LootPoolType.RAID_ASPECT:
            if not pool.raid_aspect_pool["loot"].get(location):
                pool.raid_aspect_pool["loot"][location] = {}
            pool.raid_aspect_pool["loot"][location][page] = rotation_strategy(
                previous=pool.raid_aspect_pool["loot"].get(location, {}).get(page, {}),
                now=items,
            )
        case LootPoolType.RAID_TOME:
            if not pool.raid_tome_pool["loot"].get(location):
                pool.raid_tome_pool["loot"][location] = {}
            pool.raid_tome_pool["loot"][location][page] = rotation_strategy(
                previous=pool.raid_tome_pool["loot"].get(location, {}).get(page, {}),
                now=items,
            )

    await add_loot_pools(get_session(), pool)


def rotation_strategy(
    previous: dict[str, Any],
    now: dict[str, Any],
) -> dict[str, Any]:
    """
    Update the loot pool with the given type, location, page, and items.
    This function is used to update the loot pool data for different types of loot.
    """
    # TODO Implement a more complex rotation strategy if needed
    if datetime.now(timezone.utc) - timedelta(hours=3) > get_current_rotation_datetime():
        # Grace period of 3 hours after the rotation
        # The new data might still be old
        previous.update(now)
    else:
        # The new data is fresh
        previous.update(now)
    return now


__all__ = [
    "get_current_rotation_date",
    "crowdsource_loot_pool",
]
