from app.config.db import DB_CONFIG

from .base import BaseRateLimiter as BaseRateLimiter
from .base import RateLimitKeyFunc as RateLimitKeyFunc
from .base import ip_based_key_func as ip_based_key_func
from .base import user_based_key_func as user_based_key_func
from .memory_rate_limiter import MemoryRateLimiter
from .redis_rate_limiter import RedisRateLimiter

# export the only RateLimiter based on config
RateLimiter: type[BaseRateLimiter] = MemoryRateLimiter if DB_CONFIG.redis_dsn is None else RedisRateLimiter

__all__ = [
    "RateLimitKeyFunc",
    "RateLimiter",
    "ip_based_key_func",
    "user_based_key_func",
]
