from typing import override

from redis.asyncio import Redis

from app.core.db.redis import RedisClient

from .base import Cache


class RedisCache(Cache):
    _redis: Redis | None = None

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = RedisClient.get_instance()
        return self._redis

    @override
    async def get(self, key: str) -> str | None:
        value: str | None = await self.redis.get(key)  # type: ignore[assignment]
        return value

    @override
    async def set(self, key: str, value: str, expire: int) -> None:
        await self.redis.set(key, value, ex=expire)

    @override
    async def delete(self, key: str) -> None:
        await self.redis.delete(key)
