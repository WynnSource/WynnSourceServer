from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import DateTime, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    Mapped,
    joinedload,
    mapped_column,
    relationship,
)
from sqlalchemy.schema import ForeignKey
from sqlalchemy.types import ARRAY
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.config import USER_CONFIG
from app.core.db import Base
from app.core.log import LOGGER


class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    permissions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=[])
    user: Mapped["User"] = relationship(back_populates="token", uselist=False, cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(ForeignKey("tokens.id"), primary_key=True)
    score: Mapped[int] = mapped_column(default=0)
    # A list of common IPs used by this user, ordered from oldest to newest.
    common_ips: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=[])
    creation_ip: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped["Token"] = relationship(back_populates="user", single_parent=True)


async def get_user_by_token(session: AsyncSession, token_str: str) -> User:
    user = await session.execute(
        select(User)
        .join(Token)
        .where(Token.token == token_str, Token.is_active == True)  # noqa: E712
        .options(joinedload(User.token))
    )
    user = user.scalars().first()
    if user is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return user


async def get_user_by_tokens(session: AsyncSession, token_strs: list[str]) -> list[User]:
    users = await session.execute(
        select(User)
        .join(Token)
        .where(Token.token.in_(token_strs), Token.is_active == True)  # noqa: E712
        .options(joinedload(User.token))
    )
    return list(users.scalars().all())


async def list_tokens(
    session: AsyncSession, token_str: list[str] | None = None, include_inactive: bool = False
) -> list[Token]:
    query = select(Token)
    if token_str is not None:
        query = query.where(Token.token.in_(token_str))
    if not include_inactive:
        query = query.where(Token.is_active == True)  # noqa: E712

    result = await session.execute(query)
    return list(result.scalars().all())


async def try_create_user(
    session: AsyncSession,
    token_str: str,
    permissions: list[str],
    expires_at: datetime | None,
    creation_ip: str = "unknown",
) -> User:
    existing = await session.execute(select(Token).where(Token.token == token_str, Token.is_active == True))  # noqa: E712
    if existing.scalars().first():
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Token already exists")

    new_token = Token(token=token_str, permissions=permissions, expires_at=expires_at, created_at=datetime.now(UTC))
    new_user = User(token=new_token, creation_ip=creation_ip)
    new_token.user = new_user

    session.add(new_token)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user, attribute_names=["token"])
    return new_user


async def try_delete_token(session: AsyncSession, token_str: list[str]) -> None:
    LOGGER.info(f"Attempting to delete tokens: {token_str}")
    token = await session.execute(select(Token).where(Token.token.in_(token_str)))
    tokens = token.scalars().all()
    if tokens:
        for token in tokens:
            await session.delete(token)

    # If no tokens were found, consider it a successful deletion


async def update_user_ip(session: AsyncSession, user: User, ip: str):
    if ip not in user.common_ips:
        if len(user.common_ips) >= USER_CONFIG.max_ip_records:
            user.common_ips.pop(0)
        user.common_ips.append(ip)
    else:
        user.common_ips.remove(ip)
        user.common_ips.append(ip)
