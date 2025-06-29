from typing import Sequence

from sqlalchemy import Column, ForeignKey, Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    Mapped,
    joinedload,
    mapped_column,
    relationship,
)

from app.models.base import Base

token_permission_association = Table(
    "token_permission_association",
    Base.metadata,
    Column("token_id", ForeignKey("tokens.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)


class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(nullable=False, index=True, unique=True)
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=token_permission_association, back_populates="tokens"
    )


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    permission_id: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(nullable=True)
    tokens: Mapped[list["Token"]] = relationship(
        "Token", secondary=token_permission_association, back_populates="permissions"
    )


async def list_tokens(
    async_session: async_sessionmaker[AsyncSession],
) -> Sequence[Token]:
    stmt = select(Token).options(joinedload(Token.permissions))
    async with async_session() as session:
        result = (await session.execute(stmt)).unique().scalars().all()
    return result


async def add_token(
    async_session: async_sessionmaker[AsyncSession],
    token: Token | list[Token],
) -> None:
    async with async_session() as session:
        async with session.begin():
            if isinstance(token, list):
                session.add_all(token)
            else:
                session.add(token)


async def remove_token(
    async_session: async_sessionmaker[AsyncSession],
    token_str: str | list[str],
) -> None:
    stmt = select(Token).where(Token.token == token_str)
    async with async_session() as session:
        if isinstance(token_str, list):
            stmt = select(Token).where(Token.token.in_(token_str))
        else:
            stmt = select(Token).where(Token.token == token_str)

        result = (await session.execute(stmt)).unique().scalars().all()

        if not result:
            raise ValueError(f"Token {token_str} not found")

        await session.delete(result)
        await session.commit()


async def get_token(
    async_session: async_sessionmaker[AsyncSession],
    token_str: str,
) -> Token | None:
    stmt = select(Token).where(Token.token == token_str).options(joinedload(Token.permissions))
    async with async_session() as session:
        result = (await session.execute(stmt)).unique().scalar_one_or_none()
    return result


async def add_permission_for_token(
    async_session: async_sessionmaker[AsyncSession],
    token_str: str,
    permission: Permission | list[Permission],
) -> None:
    stmt = select(Token).where(Token.token == token_str)
    async with async_session() as session:
        result = (await session.execute(stmt)).unique().scalar_one_or_none()

        if result is None:
            raise ValueError(f"Token {token_str} not found")

        if permission in result.permissions:
            return  # Permission already exists

        if isinstance(permission, list):
            result.permissions.extend(perm for perm in permission if perm not in result.permissions)
        else:
            result.permissions.append(permission)

        await session.commit()


async def remove_permission_for_token(
    async_session: async_sessionmaker[AsyncSession],
    token_str: str,
    permission: Permission | list[Permission],
) -> None:
    stmt = select(Token).where(Token.token == token_str)
    async with async_session() as session:
        result = (await session.execute(stmt)).unique().scalar_one_or_none()

        if result is None:
            raise ValueError(f"Token {token_str} not found")

        if permission not in result.permissions:
            return  # Permission does not exist

        if isinstance(permission, list):
            for perm in permission:
                result.permissions.remove(perm)
        else:
            result.permissions.remove(permission)

        await session.commit()


__all__ = [
    "Token",
    "Permission",
    "add_token",
    "get_token",
    "list_tokens",
    "remove_token",
    "remove_permission_for_token",
    "add_permission_for_token",
]
