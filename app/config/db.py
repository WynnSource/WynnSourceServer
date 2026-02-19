from typing import Annotated

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings


class DbConfig(BaseSettings):
    postgres_dsn: Annotated[
        PostgresDsn,
        Field(
            description="PostgreSQL connection string (leaving empty will use builtin SQLite database)",
            alias="WCS_DB_POSTGRES_DSN",
        ),
    ] = PostgresDsn("postgresql+asyncpg://user:password@localhost:5432/wcs_db")

    redis_dsn: Annotated[
        RedisDsn | None,
        Field(
            description="Redis connection string (leaving empty will disable Redis caching)",
            alias="WCS_DB_REDIS_DSN",
        ),
    ] = RedisDsn("redis://localhost:6379/0")


DB_CONFIG = DbConfig()

__all__ = [
    "DB_CONFIG",
]
