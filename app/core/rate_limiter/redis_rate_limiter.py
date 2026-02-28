import math
import time

from fastapi import HTTPException, Request, Response
from redis.asyncio.client import Redis
from redis.commands.core import AsyncScript
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core.db.redis import RedisClient

from .base import BaseRateLimiter, RateLimitKeyFunc, ip_based_key_func

LUA_SLIDING_WINDOW = """
local key_prefix = KEYS[1]
local limit = tonumber(ARGV[1])
local window_size = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local current_window = math.floor(now / window_size)
local elapsed_ratio = (now % window_size) / window_size

local curr_key = key_prefix .. ":" .. current_window
local prev_key = key_prefix .. ":" .. (current_window - 1)

local prev_count = tonumber(redis.call("GET", prev_key) or "0")
local curr_count = tonumber(redis.call("GET", curr_key) or "0")
local estimated = prev_count * (1 - elapsed_ratio) + curr_count

if estimated >= limit then
    local reset_after = math.ceil(window_size - (now % window_size))
    return {-1, reset_after}
end

curr_count = redis.call("INCR", curr_key)
if curr_count == 1 then
    redis.call("EXPIRE", curr_key, window_size * 2)
end

estimated = prev_count * (1 - elapsed_ratio) + curr_count
local remaining = math.max(0, math.floor(limit - estimated))
local reset_after = math.ceil(window_size - (now % window_size))
return {remaining, reset_after}
"""


class RedisRateLimiter(BaseRateLimiter):
    _redis: Redis | None = None
    _script: AsyncScript | None = None

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = RedisClient.get_instance()
        return self._redis

    @property
    def script(self) -> AsyncScript:
        if self._script is None:
            self._script = self.redis.register_script(LUA_SLIDING_WINDOW)
        return self._script

    def __init__(self, times: int, seconds: int, key_func: RateLimitKeyFunc = ip_based_key_func):
        super().__init__(times, seconds, key_func)

    async def __call__(self, request: Request, response: Response) -> Response:

        key = self.key_func(request)

        now = time.time()
        result = await self.script(keys=[key], args=[self.limit, self.period, now])
        remaining, reset_after = int(result[0]), int(result[1])

        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Reset"] = str(reset_after)

        if remaining < 0:
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = str(reset_after)
            raise HTTPException(
                HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Reset": str(math.ceil(reset_after)),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(math.ceil(reset_after)),
                },
            )

        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
