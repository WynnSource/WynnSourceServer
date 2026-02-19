from typing import override

from .base import Cache


class DummyCache(Cache):
    """
    A no-op cache implementation used when Redis is not configured.
    All get operations return None, set/delete operations are silently ignored.
    """

    @override
    async def get(self, key: str) -> str | None:
        pass

    @override
    async def set(self, key: str, value: str, expire: int) -> None:
        pass

    @override
    async def delete(self, key: str) -> None:
        pass
