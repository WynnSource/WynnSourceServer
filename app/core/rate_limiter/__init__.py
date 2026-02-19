from app.config.db import DB_CONFIG
from app.core.rate_limiter.base import BaseRateLimiter as BaseRateLimiter

from .memory_rate_limiter import MemoryRateLimiter
from .redis_rate_limiter import RedisRateLimiter

# export the only RateLimiter based on config
RateLimiter: type[BaseRateLimiter] = MemoryRateLimiter if DB_CONFIG.redis_dsn is None else RedisRateLimiter

__all__ = [
    "RateLimiter",
]
