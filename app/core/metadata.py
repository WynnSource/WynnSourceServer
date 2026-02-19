import dataclasses
from collections.abc import Awaitable, Callable

from app.core.rate_limiter import RateLimitKeyFunc, ip_based_key_func


@dataclasses.dataclass
class CacheConfig:
    expire: int = 60


@dataclasses.dataclass
class RateLimitMetadata:
    limit: int
    period: int
    key_func: RateLimitKeyFunc


@dataclasses.dataclass
class EndpointMetadata:
    """
    Metadata for an API endpoint.
    """

    # Indicates whether the metadata has been processed by the router.
    processed: bool = False

    permission: str | set[str] | None = None
    cache: CacheConfig | None = None
    rate_limit: RateLimitMetadata | None = None


def cached(expire: int = 60):
    """
    Decorator to add cache metadata to an API endpoint.
    """

    def decorator(func: Callable[..., Awaitable]):
        meta = getattr(func, "__metadata__", None)
        if meta is not None:
            if not isinstance(meta, EndpointMetadata):
                raise ValueError(
                    f"Function {func.__name__} already has metadata but is not an EndpointMetadata instance"
                )
            meta = dataclasses.replace(meta, cache=CacheConfig(expire=expire))
        else:
            meta = EndpointMetadata(cache=CacheConfig(expire=expire))
        setattr(func, "__metadata__", meta)
        return func

    return decorator


def permission(permission: str | set[str] | None = None):
    """
    Decorator to add metadata to an API endpoint.
    """

    def decorator(func):
        meta = getattr(func, "__metadata__", None)
        if meta is not None:
            if not isinstance(meta, EndpointMetadata):
                raise ValueError(
                    f"Function {func.__name__} already has metadata but is not an EndpointMetadata instance"
                )
            meta = dataclasses.replace(meta, permission=permission)
        else:
            meta = EndpointMetadata(permission=permission)
        setattr(func, "__metadata__", meta)
        return func

    return decorator


def rate_limit(limit: int, period: int, key_func: RateLimitKeyFunc = ip_based_key_func):
    """
    Decorator to add rate limit metadata to an API endpoint.
    """

    def decorator(func):
        meta = getattr(func, "__metadata__", None)
        if meta is not None:
            if not isinstance(meta, EndpointMetadata):
                raise ValueError(
                    f"Function {func.__name__} already has metadata but is not an EndpointMetadata instance"
                )
            meta = dataclasses.replace(
                meta, rate_limit=RateLimitMetadata(limit=limit, period=period, key_func=key_func)
            )
        else:
            meta = EndpointMetadata(rate_limit=RateLimitMetadata(limit=limit, period=period, key_func=key_func))
        setattr(func, "__metadata__", meta)
        return func

    return decorator


# metadata = MetadataBuilder()

__all__ = ["EndpointMetadata", "cached", "permission", "rate_limit"]
