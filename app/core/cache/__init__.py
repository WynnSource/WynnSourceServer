import hashlib
import typing
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, overload

import orjson as json
from fastapi import Request, Response
from pydantic import BaseModel, TypeAdapter

from app.config import DB_CONFIG
from app.core.log import LOGGER
from app.schemas.constants import INJECTED_NAMESPACE

from .base import Cache
from .dummy_cache import DummyCache
from .redis_cache import RedisCache

_cache: Cache = DummyCache() if DB_CONFIG.redis_dsn is None else RedisCache()


def _build_cache_key(request: Request) -> str:
    key_parts = f"{request.method}:{request.url.path}:{hashlib.md5(str(request.query_params).encode()).hexdigest()}"
    return f"cache:{key_parts}"


def _serialize(value: Any, model: type | None = None) -> str:
    if model is not None and issubclass(model, BaseModel):
        adapter = TypeAdapter(model)
        return adapter.dump_json(value).decode()
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    return json.dumps(value).decode()


def _deserialize[R](raw: str, model: type[R]) -> R:
    if issubclass(model, BaseModel):
        return model.model_validate_json(raw)
    return json.loads(raw)


def _extract_from_args[T](args: tuple[object, ...], kwargs: dict[str, object], name: str, cls: type[T]) -> T | None:
    """Extract a value of the given type from function args/kwargs."""
    value = kwargs.get(name)
    if isinstance(value, cls):
        return value
    return next((arg for arg in args if isinstance(arg, cls)), None)


@overload
def cached[**P, R](func: Callable[P, Awaitable[R]], /) -> Callable[P, Awaitable[R]]: ...
@overload
def cached[**P, R](*, expire: int = 60) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]: ...


def cached[**P, R](
    func: Callable[P, Awaitable[R]] | None = None,
    /,
    *,
    expire: int = 60,
) -> Callable[P, Awaitable[R]] | Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Cache decorator for async FastAPI endpoint handlers.

    Supports two usage patterns::

        @cached
        async def handler(...): ...

        @cached(expire=120)
        async def handler(...): ...

    The decorator extracts ``Request`` / ``Response`` from function arguments
    to build cache keys and set ``X-Cache`` headers. If no ``Request`` is
    found in the arguments, caching is skipped and the function is called
    directly.

    :param expire: Cache expiration time in seconds (default: 60)
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        return_type: type[R] | None = typing.get_type_hints(fn).get("return", None)

        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = _extract_from_args(args, kwargs, "request", Request) or _extract_from_args(
                args, kwargs, f"{INJECTED_NAMESPACE}request", Request
            )
            response = _extract_from_args(args, kwargs, "response", Response) or _extract_from_args(
                args, kwargs, f"{INJECTED_NAMESPACE}response", Response
            )

            if request is None:
                LOGGER.warning(f"No Request found in arguments of {fn.__name__}, skipping cache")
                return await fn(*args, **kwargs)

            cache_key = _build_cache_key(request)

            raw = await _cache.get(cache_key)
            if raw is not None:
                if response:
                    response.headers["X-Cache"] = "HIT"
                if return_type is not None:
                    return _deserialize(raw, return_type)
                return json.loads(raw)  # type: ignore[return-value]

            if response:
                response.headers["X-Cache"] = "MISS"

            try:
                result = await fn(*args, **kwargs)
            except Exception:
                # If the function raises an exception, don't cache it
                raise

            try:
                serialized = _serialize(result, model=return_type)
                await _cache.set(cache_key, serialized, expire=expire)
            except (TypeError, ValueError):
                LOGGER.warning(f"Failed to serialize cache value for key {cache_key}, skipping cache")

            return result

        return wrapper

    if func is not None:
        return decorator(func)

    return decorator


__all__ = [
    "Cache",
    "cached",
]
