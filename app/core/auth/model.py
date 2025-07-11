from typing import Sequence

from app.core.db import Base
from sqlalchemy import Column, ForeignKey, Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    Mapped,
    joinedload,
    mapped_column,
    relationship,
)

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
        "Permission", secondary=token_permission_association, back_populates="tokens", lazy="joined"
    )


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    permission_id: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(nullable=True)
    tokens: Mapped[list["Token"]] = relationship(
        "Token", secondary=token_permission_association, back_populates="permissions", lazy="joined"
    )


async def list_tokens(
    async_session: async_sessionmaker[AsyncSession],
) -> Sequence[Token]:
    stmt = select(Token).options(joinedload(Token.permissions))
    async with async_session() as session:
        tokens = (await session.execute(stmt)).unique().scalars().all()
    return tokens


async def add_token(
    async_session: async_sessionmaker[AsyncSession],
    tokens_str: str | list[str],
    permissions_str: str | list[str] = [],
) -> None:
    async with async_session() as session:
        async with session.begin():
            if isinstance(tokens_str, str):
                tokens_str = [tokens_str]
            if isinstance(permissions_str, str):
                permissions_str = [permissions_str] if permissions_str else []

            tokens = [
                Token(
                    token=token_str,
                    permissions=[await get_or_create_permission(async_session, perm) for perm in permissions_str],
                )
                for token_str in tokens_str
            ]

            session.add_all(tokens)


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

        tokens = (await session.execute(stmt)).unique().scalars().all()

        if not tokens:
            raise ValueError(f"Token {token_str} not found")

        await session.delete(tokens)
        await session.commit()


async def get_token(
    async_session: async_sessionmaker[AsyncSession],
    token_str: str,
) -> Token | None:
    stmt = select(Token).where(Token.token == token_str).options(joinedload(Token.permissions))
    async with async_session() as session:
        token = (await session.execute(stmt)).unique().scalar_one_or_none()
    return token


async def add_permission_for_token(
    async_session: async_sessionmaker[AsyncSession],
    token_str: str,
    requested_permissions_str: str | list[str],
) -> Token:
    stmt = select(Token).where(Token.token == token_str)
    async with async_session() as session:
        token = (await session.execute(stmt)).unique().scalar_one_or_none()

        if token is None:
            raise ValueError(f"Token {token_str} not found")

        if isinstance(requested_permissions_str, str):
            requested_permissions_str = [requested_permissions_str]

        for requested_perm_str in requested_permissions_str:
            if any(requested_perm_str == user_perm.permission_id for user_perm in token.permissions):
                continue  # Permission already exists

            permission = await get_or_create_permission(async_session, requested_perm_str)
            token.permissions.append(permission)

        await session.commit()

        return token


async def remove_permission_for_token(
    async_session: async_sessionmaker[AsyncSession],
    token_str: str,
    permissions_str: str | list[str],
) -> Token:
    stmt = select(Token).where(Token.token == token_str)
    async with async_session() as session:
        token = (await session.execute(stmt)).unique().scalar_one_or_none()

        if token is None:
            raise ValueError(f"Token {token_str} not found")

        if isinstance(permissions_str, str):
            permissions_str = [permissions_str]

        for token_perm in token.permissions:
            if token_perm.permission_id in permissions_str:
                token.permissions.remove(token_perm)

        await session.commit()
        return token


async def list_permissions(
    async_session: async_sessionmaker[AsyncSession],
) -> Sequence[Permission]:
    stmt = select(Permission).options(joinedload(Permission.tokens))
    async with async_session() as session:
        permissions = (await session.execute(stmt)).unique().scalars().all()
    return permissions


async def get_permission(
    async_session: async_sessionmaker[AsyncSession],
    permission_id: str,
) -> Permission | None:
    stmt = select(Permission).where(Permission.permission_id == permission_id)
    async with async_session() as session:
        permission = (await session.execute(stmt)).unique().scalar_one_or_none()
    return permission


async def get_or_create_permission(
    async_session: async_sessionmaker[AsyncSession],
    permission_id: str,
) -> Permission:
    permission = await get_permission(async_session, permission_id)
    if permission is None:
        permission = Permission(permission_id=permission_id)
        async with async_session() as session:
            session.add(permission)
            await session.commit()
    return permission
