from datetime import datetime
from typing import Literal

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.core.db import Base, BaseRepository
from app.core.security.model import User
from app.module.pool.schema import PoolType

from .config import PoolRotation


class Pool(Base):
    __tablename__ = "pools"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    pool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)

    rotation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    consensus_data: Mapped[list[bytes]] = mapped_column(ARRAY(LargeBinary), nullable=False, default=[])
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    submission_count: Mapped[int] = mapped_column(Integer, default=0)

    needs_recalc: Mapped[bool] = mapped_column(Boolean, default=True)

    submissions: Mapped[list["PoolSubmission"]] = relationship(
        "PoolSubmission",
        back_populates="rotation",
        cascade="save-update, merge",
    )

    __table_args__ = (UniqueConstraint("pool_type", "region", "page", "rotation_start", name="uq_pool_rotation_key"),)


class PoolSubmission(Base):
    __tablename__ = "pool_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    rotation_id: Mapped[int | None] = mapped_column(
        ForeignKey("pools.id", ondelete="CASCADE"), index=True, nullable=True
    )
    rotation: Mapped[Pool | None] = relationship("Pool", back_populates="submissions")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    user: Mapped[User] = relationship("User")

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mod_version: Mapped[str] = mapped_column(String(50), nullable=False)
    fuzzy: Mapped[bool] = mapped_column(Boolean, default=False)

    item_data: Mapped[list[bytes]] = mapped_column(ARRAY(LargeBinary), nullable=False)

    weight: Mapped[float] = mapped_column(Float, nullable=False)


class PoolRepository(BaseRepository):
    async def get_by_key(self, pool_type: PoolType, region: str, page: int, rotation_start: datetime) -> Pool | None:
        query = select(Pool).where(
            Pool.pool_type == pool_type.value,
            Pool.region == region,
            Pool.page == page,
            Pool.rotation_start == rotation_start,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_pools(
        self,
        pool_type: PoolType | None = None,
        region: str | None = None,
        page: int | None = None,
        rotation_start: datetime | None = None,
        needs_recalc: bool | None = None,
        order_by: Literal["rotation_start", "page"] | None = None,
    ) -> list[Pool]:
        query = select(Pool).options(selectinload(Pool.submissions))
        if pool_type is not None:
            query = query.where(Pool.pool_type == pool_type.value)
        if region is not None:
            query = query.where(Pool.region == region)
        if page is not None:
            query = query.where(Pool.page == page)
        if rotation_start:
            query = query.where(Pool.rotation_start == rotation_start)
        if needs_recalc is not None:
            query = query.where(Pool.needs_recalc == needs_recalc)

        if order_by == "rotation_start":
            query = query.order_by(Pool.rotation_start)
        elif order_by == "page":
            query = query.order_by(Pool.page)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def save(self, pool: Pool) -> None:
        self.session.add(pool)
        await self.session.flush()
        await self.session.refresh(pool)

    async def delete(self, pool: Pool) -> None:
        await self.session.delete(pool)
        await self.session.flush()

    async def get_or_create_pool(self, pool_type: PoolType, region: str, page: int, rotation: PoolRotation) -> Pool:
        existing_pool = await self.get_by_key(
            pool_type=pool_type,
            region=region,
            page=page,
            rotation_start=rotation.start,
        )
        if existing_pool:
            return existing_pool

        try:
            async with self.session.begin_nested():
                new_pool = Pool(
                    pool_type=pool_type.value,
                    region=region,
                    page=page,
                    rotation_start=rotation.start,
                    rotation_end=rotation.end,
                )
                await self.save(new_pool)
                return new_pool
        except IntegrityError:
            return await self.get_or_create_pool(pool_type, region, page, rotation)


class PoolSubmissionRepository(BaseRepository):
    async def save(self, submission: PoolSubmission) -> None:
        self.session.add(submission)
        await self.session.flush()
        await self.session.refresh(submission)

    async def delete(self, submission: PoolSubmission) -> None:
        await self.session.delete(submission)
        await self.session.flush()

    async def list_submissions_for_rotation(self, rotation_id: int) -> list[PoolSubmission]:
        query = select(PoolSubmission).where(PoolSubmission.rotation_id == rotation_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_submission_for_rotation(self, user_id: int, rotation_id: int) -> PoolSubmission | None:
        query = select(PoolSubmission).where(
            PoolSubmission.user_id == user_id,
            PoolSubmission.rotation_id == rotation_id,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_submissions_by_user(self, user_id: int) -> list[PoolSubmission]:
        query = select(PoolSubmission).where(PoolSubmission.user_id == user_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())
