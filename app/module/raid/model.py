from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.core.db import Base, BaseRepository
from app.core.security.model import User

from .config import GambitRotation


class Gambit(Base):
    __tablename__ = "gambits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    region: Mapped[str] = mapped_column(String(50), nullable=False)

    rotation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    consensus_data: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(tz=UTC)
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    needs_recalc: Mapped[bool] = mapped_column(Boolean, default=True)

    submissions: Mapped[list["GambitSubmission"]] = relationship(
        "GambitSubmission",
        back_populates="gambit",
        cascade="save-update, merge",
    )

    __table_args__ = (UniqueConstraint("region", "rotation_start", name="uq_gambit_key"),)


class GambitSubmission(Base):
    __tablename__ = "gambit_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    gambit_id: Mapped[int | None] = mapped_column(
        ForeignKey("gambits.id", ondelete="CASCADE"), index=True, nullable=True
    )
    gambit: Mapped[Gambit | None] = relationship("Gambit", back_populates="submissions")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    user: Mapped[User] = relationship("User")

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mod_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Each gambit is (name, description), stored as parallel arrays
    gambit_names: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False)
    gambit_descriptions: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False)

    weight: Mapped[float] = mapped_column(Float, nullable=False)


class GambitRepository(BaseRepository):
    async def get_by_key(self, region: str, rotation_start: datetime) -> Gambit | None:
        query = select(Gambit).where(
            Gambit.region == region,
            Gambit.rotation_start == rotation_start,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_gambits(
        self,
        region: str | None = None,
        rotation_start: datetime | None = None,
        needs_recalc: bool | None = None,
        order_by: Literal["rotation_start"] | None = None,
        for_update: bool = False,
    ) -> list[Gambit]:
        query = select(Gambit).options(selectinload(Gambit.submissions))
        if region is not None:
            query = query.where(Gambit.region == region)
        if rotation_start is not None:
            query = query.where(Gambit.rotation_start == rotation_start)
        if needs_recalc is not None:
            query = query.where(Gambit.needs_recalc == needs_recalc)

        if order_by == "rotation_start":
            query = query.order_by(Gambit.rotation_start)

        if for_update:
            query = query.with_for_update()

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def save(self, gambit: Gambit) -> None:
        self.session.add(gambit)
        await self.session.flush()
        await self.session.refresh(gambit)

    async def get_or_create_gambit(self, region: str, rotation: GambitRotation) -> Gambit:
        existing = await self.get_by_key(region=region, rotation_start=rotation.start)
        if existing:
            return existing

        try:
            async with self.session.begin_nested():
                new_gambit = Gambit(
                    region=region,
                    rotation_start=rotation.start,
                    rotation_end=rotation.end,
                )
                await self.save(new_gambit)
                return new_gambit
        except IntegrityError:
            return await self.get_or_create_gambit(region, rotation)


class GambitSubmissionRepository(BaseRepository):
    async def save(self, submission: GambitSubmission) -> None:
        self.session.add(submission)
        await self.session.flush()
        await self.session.refresh(submission)

    async def delete(self, submission: GambitSubmission) -> None:
        await self.session.delete(submission)
        await self.session.flush()

    async def get_user_submission_for_gambit(self, user_id: int, gambit_id: int) -> GambitSubmission | None:
        query = select(GambitSubmission).where(
            GambitSubmission.user_id == user_id,
            GambitSubmission.gambit_id == gambit_id,
        )
        result = await self.session.execute(query)
        return result.scalars().first()
