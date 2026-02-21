from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.security.model import User


class Pool(Base):
    __tablename__ = "pools"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    pool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)

    rotation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    consensus_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    item_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    weight: Mapped[float] = mapped_column(Float, nullable=False)
    is_fuzzy: Mapped[bool] = mapped_column(Boolean, default=False)

    rotation: Mapped["Pool"] = relationship("Pool", back_populates="submissions")
    user: Mapped["User"] = relationship("User")
