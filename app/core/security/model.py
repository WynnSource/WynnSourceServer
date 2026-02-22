from datetime import datetime

from sqlalchemy import DateTime, String, delete, func, select
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)
from sqlalchemy.types import ARRAY

from app.config import USER_CONFIG
from app.core.db import Base, BaseRepository


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    token: Mapped[str] = mapped_column(nullable=False, index=True, unique=True)
    permissions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=[])

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    creation_ip: Mapped[str] = mapped_column(String, nullable=False)
    # A list of common IPs used by this user, ordered from oldest to newest.
    common_ips: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=[])

    score: Mapped[int] = mapped_column(default=0)


class UserRepository(BaseRepository):
    async def get_user_by_token(self, token_str: str, include_inactive: bool = False) -> User | None:
        query = select(User).where(User.token == token_str)
        if not include_inactive:
            query = query.where(User.is_active == True)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_users_by_tokens(self, token_strs: list[str], include_inactive: bool = False) -> list[User]:
        query = select(User).where(User.token.in_(token_strs))
        if not include_inactive:
            query = query.where(User.is_active == True)  # noqa: E712
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_users(self, include_inactive: bool = False) -> list[User]:
        query = select(User)
        if not include_inactive:
            query = query.where(User.is_active == True)  # noqa: E712
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def save(self, user: User) -> None:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user, attribute_names=["token"])

    async def delete(self, token_strs: list[str]) -> None:
        await self.session.execute(delete(User).where(User.token.in_(token_strs)))
        await self.session.flush()

    async def update_user_ip(self, user: User, ip: str) -> None:
        if ip not in user.common_ips:
            if len(user.common_ips) >= USER_CONFIG.max_ip_records:
                user.common_ips.pop(0)
            user.common_ips.append(ip)
        else:
            user.common_ips.remove(ip)
            user.common_ips.append(ip)
        await self.session.flush()
