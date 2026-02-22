from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import DB_CONFIG
from app.core.log import LOGGER

engine: AsyncEngine | None = None
session_maker: async_sessionmaker[AsyncSession]


async def get_dsn() -> str:
    """
    Returns the database connection string based on the configuration.
    """
    if DB_CONFIG.postgres_dsn is None:
        LOGGER.warning("PostgreSQL DSN not provided, exiting application.")
        raise RuntimeError("PostgreSQL DSN is required but not provided.")
    return DB_CONFIG.postgres_dsn.encoded_string()


async def init_db() -> AsyncEngine:
    global engine, session_maker
    dsn = await get_dsn()
    engine = create_async_engine(dsn, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    LOGGER.debug(f"Database engine initialized with DSN: {dsn}")
    return engine


def get_engine() -> AsyncEngine:
    """
    Returns the SQLAlchemy engine. Initializes it if not already done.
    """
    global engine
    if engine is None:
        LOGGER.error("Database engine is not initialized.")
        raise RuntimeError("Database engine is not initialized.")
    return engine


async def close_db():
    """
    Closes the database engine connection.
    """
    global engine
    if engine is not None:
        await engine.dispose()
        LOGGER.debug("Database engine connection closed.")


@asynccontextmanager
async def get_session():
    async with session_maker() as session:
        try:
            LOGGER.debug("Database session started.")
            yield session
            await session.commit()
            LOGGER.debug("Database session committed.")
        except Exception:
            LOGGER.exception("Error occurred during database session, rolling back.")
            await session.rollback()
            raise


async def get_session_fastapi() -> AsyncGenerator[AsyncSession, None]:
    """
    Returns the SQLAlchemy session maker.
    """
    async with get_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session_fastapi)]

__all__ = ["SessionDep", "close_db", "get_engine", "get_session", "init_db"]
