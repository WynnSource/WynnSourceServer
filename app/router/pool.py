from typing import Any

from app.domain.enums.pool import LootPoolType
from app.domain.request.v1.pool import CrowdSourceLootPoolData
from app.domain.response.v1.pool import (
    ItemLootPoolData,
    ItemLootPoolResponse,
    RaidLootPoolData,
    RaidLootPoolResponse,
)
from app.domain.response.v1.response import V1Response
from app.models.pool import get_loot_pools, purge_loot_pools, update_loot_pools
from app.service.db import get_session
from app.service.pool import crowdsource_loot_pool, get_current_rotation_date
from app.utils.auth_utils import require_permission
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

PoolRouter = APIRouter(prefix="/pool", tags=["pool"])


@PoolRouter.get(
    "/item/list",
    summary="Get Item Loot Pools",
    description="Get the loot pools for items, including shiny items and their rarities.",
    dependencies=[Depends(require_permission("pool.item.read"))],
)
async def get_item_loot_pools(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> ItemLootPoolResponse:
    loot_pool_data = await get_loot_pools(session, get_current_rotation_date())
    if loot_pool_data is None:
        return ItemLootPoolResponse(data=ItemLootPoolData(loot={}))
    return ItemLootPoolResponse(data=ItemLootPoolData(**loot_pool_data.lr_item_pool))


@PoolRouter.get(
    "/raid/aspect/list",
    summary="Get Raid Aspect Loot Pools",
    description="Get the loot pools for raid aspects.",
    dependencies=[Depends(require_permission("pool.raid.aspect.read"))],
)
async def get_raid_aspect_loot_pools(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> RaidLootPoolResponse:
    loot_pool_data = await get_loot_pools(session, get_current_rotation_date())
    if loot_pool_data is None:
        return RaidLootPoolResponse(data=RaidLootPoolData(loot={}))
    return RaidLootPoolResponse(data=RaidLootPoolData(**loot_pool_data.raid_aspect_pool))


@PoolRouter.get(
    "/raid/tome/list",
    summary="Get Raid Tome Loot Pools",
    description="Get the loot pools for raid tomes.",
    dependencies=[Depends(require_permission("pool.raid.tome.read"))],
)
async def get_raid_tome_loot_pools(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> RaidLootPoolResponse:
    loot_pool_data = await get_loot_pools(session, get_current_rotation_date())
    if loot_pool_data is None:
        return RaidLootPoolResponse(data=RaidLootPoolData(loot={}))
    return RaidLootPoolResponse(data=RaidLootPoolData(**loot_pool_data.raid_tome_pool))


@PoolRouter.post(
    "/{type}/{location}/{page}",
    summary="Crowdsource Loot Pool",
    description="Upload Crowdsource data for the loot pool for a specific location and page.",
    dependencies=[Depends(require_permission("pool.item.crowdsource"))],
)
async def crowdsource_item_loot_pool(
    type: LootPoolType,
    location: str,
    page: int,
    items: CrowdSourceLootPoolData,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> V1Response:
    await crowdsource_loot_pool(type, location, page, items, session)
    return V1Response.from_dict(data={"type": type, "location": location, "page": page, "items": items})


@PoolRouter.delete(
    "/clear",
    summary="Purge Current Loot Pool",
    description="Purge the current loot pool.",
    dependencies=[Depends(require_permission("pool.item.write"))],
)
async def purge_item_loot_pool(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> V1Response:
    await purge_loot_pools(session, get_current_rotation_date())
    return V1Response.from_message(
        message=f"Purged current loot pool for date {get_current_rotation_date()}",
    )


@PoolRouter.post(
    "/{type}/update",
    summary="Update Loot Pool",
    description="Manual update the loot pool for a specific type.",
    dependencies=[Depends(require_permission("pool.item.write"))],
)
async def update_loot_pool(
    type: LootPoolType,
    loot_pool_data: dict[str, Any],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> V1Response:
    await update_loot_pools(session, type, loot_pool_data, get_current_rotation_date())
    return V1Response.from_message(
        message=f"Updated loot pool for type {type} with data: {loot_pool_data}",
    )
