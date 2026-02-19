import abc


class Cache(abc.ABC):
    """
    Abstract base class for cache implementations.
    Cache stores and retrieves raw string values (JSON).
    Serialization/deserialization is the caller's responsibility.
    """

    @abc.abstractmethod
    async def get(self, key: str) -> str | None:
        """Get a raw string value from the cache by key."""
        ...

    @abc.abstractmethod
    async def set(self, key: str, value: str, expire: int) -> None:
        """Set a raw string value in the cache with expiration time in seconds."""
        ...

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from the cache by key."""
        ...
