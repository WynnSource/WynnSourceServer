from redis import asyncio as aioredis

from app.config.db import DB_CONFIG


class RedisClient:
    _instance: aioredis.Redis | None = None

    @classmethod
    async def init(cls):
        if DB_CONFIG.redis_dsn is None:
            raise RuntimeError("Redis DSN is not configured, cannot create Redis client")
        cls._instance = await aioredis.from_url(
            DB_CONFIG.redis_dsn.encoded_string(), encoding="utf-8", decode_responses=True
        )

    @classmethod
    def get_instance(cls) -> aioredis.Redis:
        if cls._instance is None:
            raise RuntimeError("Redis client is not initialized. Call RedisClient.init() first.")
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
