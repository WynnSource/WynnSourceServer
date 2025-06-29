from typing import Annotated, Optional

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DbConfig(BaseSettings):
    postgres_dsn: Annotated[
        Optional[PostgresDsn],
        Field(
            description="PostgreSQL connection string (leaving empty will use builtin SQLite database)",
            alias="POSTGRES_DSN",
        ),
    ] = None
    sqlite_dsn: str = Field(
        default="sqlite+aiosqlite:///./wcs.sqlite3",
        description="SQLite connection string (Do not use this in production, only for testing purposes)",
    )

    model_config = SettingsConfigDict(env_prefix="WCS_DB_")


DB_CONFIG = DbConfig()
