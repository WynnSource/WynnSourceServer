from app.config import DB_CONFIG
from app.log import logger
from app.models import Base
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

engine: AsyncEngine | None = None
session_maker: async_sessionmaker[AsyncSession] | None = None


async def get_dsn() -> str:
    """
    Returns the database connection string based on the configuration.
    If PostgreSQL DSN is not set, it returns the SQLite DSN.
    """
    if DB_CONFIG.postgres_dsn is None:
        logger.warning("PostgreSQL connection string is not set, using SQLite for testing purposes.")
        return DB_CONFIG.sqlite_dsn
    return DB_CONFIG.postgres_dsn.encoded_string()


async def init_db() -> AsyncEngine:
    global engine, session_maker
    dsn = await get_dsn()
    engine = create_async_engine(dsn, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    logger.debug(f"Database engine initialized with DSN: {dsn}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.debug("Database tables created successfully.")
    return engine


def get_engine() -> AsyncEngine:
    """
    Returns the SQLAlchemy engine. Initializes it if not already done.
    """
    global engine
    if engine is None:
        logger.error("Database engine is not initialized.")
        raise RuntimeError("Database engine is not initialized.")
    return engine


def get_session() -> async_sessionmaker[AsyncSession]:
    """
    Returns the SQLAlchemy session maker.
    """
    global session_maker
    if session_maker is None:
        logger.error("Database session maker is not initialized.")
        raise RuntimeError("Database session maker is not initialized.")
    return session_maker
