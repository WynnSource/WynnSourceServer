from typing import Any

from app.core.auth import require_permission
from app.core.db import get_session
from app.core.metadata import with_metadata
from app.domain.enums import LootPoolType
from app.domain.response import Response
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .domain.request import CrowdSourceLootPoolData
from .domain.response import (
    ItemLootPoolData,
    ItemLootPoolResponse,
    RaidLootPoolData,
    RaidLootPoolResponse,
)
from .model import get_loot_pools, purge_loot_pools, update_loot_pools
from .service import crowdsource_loot_pool, get_current_rotation_date

PoolRouter = APIRouter(prefix="/pool", tags=["pool"])


@PoolRouter.get(
    "/item/list",
    summary="Get Item Loot Pools",
    description="Get the loot pools for items, including shiny items and their rarities.",
    dependencies=[Depends(require_permission)],
)
@with_metadata(permission="pool.item.read")
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
    dependencies=[Depends(require_permission)],
)
@with_metadata(permission="pool.raid.aspect.read")
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
    dependencies=[Depends(require_permission)],
)
@with_metadata(permission="pool.raid.tome.read")
async def get_raid_tome_loot_pools(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> RaidLootPoolResponse:
    loot_pool_data = await get_loot_pools(session, get_current_rotation_date())
    if loot_pool_data is None:
        return RaidLootPoolResponse(data=RaidLootPoolData(loot={}))
    return RaidLootPoolResponse(data=RaidLootPoolData(**loot_pool_data.raid_tome_pool))


@PoolRouter.post(
    "/crowdsource",
    summary="Crowdsource Loot Pool",
    description="Upload Crowdsource data for the loot pool for a specific location and page.",
    dependencies=[Depends(require_permission)],
)
@with_metadata(permission="pool.item.crowdsource")
async def crowdsource_item_loot_pool(
    items: list[CrowdSourceLootPoolData],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> Response:
    for item in items:
        await crowdsource_loot_pool(item.type, item.location, item.page, item, session)
    return Response.from_message(
        message=f"Successfully crowdsourced {len(items)} pages for loot pool.",
    )


@PoolRouter.delete(
    "/clear",
    summary="Purge Current Loot Pool",
    description="Purge the current loot pool.",
    dependencies=[Depends(require_permission)],
)
@with_metadata(permission="pool.item.write")
async def purge_item_loot_pool(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> Response:
    await purge_loot_pools(session, get_current_rotation_date())
    return Response.from_message(
        message=f"Purged current loot pool for date {get_current_rotation_date()}",
    )


@PoolRouter.post(
    "/{type}/update",
    summary="Update Loot Pool",
    description="Manual update the loot pool for a specific type.",
    dependencies=[Depends(require_permission)],
)
@with_metadata(permission="pool.item.write")
async def update_loot_pool(
    type: LootPoolType,
    loot_pool_data: dict[str, Any],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> Response:
    await update_loot_pools(session, type, loot_pool_data, get_current_rotation_date())
    return Response.from_message(
        message=f"Updated loot pool for type {type} with data: {loot_pool_data}",
    )
