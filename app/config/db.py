from typing import Annotated

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings


class DbConfig(BaseSettings):
    postgres_host: Annotated[str, Field(alias="POSTGRES_HOST")] = "localhost"
    postgres_port: Annotated[int, Field(alias="POSTGRES_PORT")] = 5432
    postgres_user: Annotated[str, Field(alias="POSTGRES_USER")] = "postgres"
    postgres_password: Annotated[str, Field(alias="POSTGRES_PASSWORD")] = "postgres"
    postgres_db: Annotated[str, Field(alias="POSTGRES_DB")] = "wcs_db"

    redis_host: Annotated[str, Field(alias="REDIS_HOST")] = "localhost"
    redis_port: Annotated[int, Field(alias="REDIS_PORT")] = 6379

    @computed_field
    @property
    def postgres_dsn(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    @computed_field
    @property
    def redis_dsn(self) -> RedisDsn:
        return RedisDsn.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            path="0",
        )


DB_CONFIG = DbConfig()

__all__ = [
    "DB_CONFIG",
]
