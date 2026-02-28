from pydantic_settings import BaseSettings
from pydantic import computed_field, PostgresDsn, RedisDsn

class DbConfig(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "user"
    postgres_password: str = "password"
    postgres_db: str = "wcs_db"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: str = "0"
    redis_enabled: bool = True

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
    def redis_dsn(self) -> RedisDsn | None:
        if not self.redis_enabled:
            return None
        return RedisDsn.build(
            scheme="redis",
            password=self.redis_password,
            host=self.redis_host,
            port=self.redis_port,
            path=self.redis_db,
        )

cfg = DbConfig()
print(cfg.postgres_dsn)
print(cfg.redis_dsn)
