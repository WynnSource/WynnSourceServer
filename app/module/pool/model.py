from app.core.db import Base
from app.domain.enums import LootPoolType
from sqlalchemy import JSON, BigInteger, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)


class LootPoolData(Base):
    """
    Data model for loot pools.
    """

    __tablename__ = "loot_pools"

    id: Mapped[int] = mapped_column(primary_key=True)
    starting_date: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    lr_item_pool: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    raid_aspect_pool: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    raid_tome_pool: Mapped[dict] = mapped_column(JSON, nullable=False, default={})


async def add_loot_pools(
    async_session: async_sessionmaker[AsyncSession],
    loot_pool_data: LootPoolData,
) -> None:
    async with async_session() as session:
        async with session.begin():
            stmt = select(LootPoolData).where(LootPoolData.starting_date == loot_pool_data.starting_date)
            result = (await session.execute(stmt)).unique().scalar_one_or_none()
            if result:
                # Update existing record
                result.lr_item_pool = loot_pool_data.lr_item_pool
                result.raid_aspect_pool = loot_pool_data.raid_aspect_pool
                result.raid_tome_pool = loot_pool_data.raid_tome_pool
            else:
                # Add new record
                session.add(loot_pool_data)
            await session.commit()


async def get_loot_pools(
    async_session: async_sessionmaker[AsyncSession],
    rotation_date: int,
) -> LootPoolData | None:
    async with async_session() as session:
        stmt = select(LootPoolData).where(LootPoolData.starting_date == rotation_date)
        result = (await session.execute(stmt)).unique().scalar_one_or_none()
        return result


async def update_loot_pools(
    async_session: async_sessionmaker[AsyncSession],
    loot_pool_type: LootPoolType,
    loot_pool_data: dict,
    rotation_date: int,
) -> None:
    async with async_session() as session:
        async with session.begin():
            match loot_pool_type:
                case LootPoolType.ITEM:
                    stmt = select(LootPoolData).where(LootPoolData.starting_date == rotation_date)
                    result = (await session.execute(stmt)).unique().scalar_one_or_none()
                    if result:
                        result.lr_item_pool = loot_pool_data
                case LootPoolType.RAID_ASPECT:
                    stmt = select(LootPoolData).where(LootPoolData.starting_date == rotation_date)
                    result = (await session.execute(stmt)).unique().scalar_one_or_none()
                    if result:
                        result.raid_aspect_pool = loot_pool_data
                case LootPoolType.RAID_TOME:
                    stmt = select(LootPoolData).where(LootPoolData.starting_date == rotation_date)
                    result = (await session.execute(stmt)).unique().scalar_one_or_none()
                    if result:
                        result.raid_tome_pool = loot_pool_data
            await session.commit()


async def purge_loot_pools(
    async_session: async_sessionmaker[AsyncSession],
    rotation_date: int,
) -> None:
    async with async_session() as session:
        async with session.begin():
            stmt = select(LootPoolData).where(LootPoolData.starting_date == rotation_date)
            result = (await session.execute(stmt)).unique().scalars().all()
            for loot_pool in result:
                await session.delete(loot_pool)
            await session.commit()


__all__ = [
    "LootPoolData",
    "add_loot_pools",
    "get_loot_pools",
    "update_loot_pools",
    "purge_loot_pools",
]
