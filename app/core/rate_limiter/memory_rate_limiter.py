import math
import time

from fastapi import HTTPException, Request, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from .base import BaseRateLimiter, RateLimitKeyFunc, ip_based_key_func


class MemoryRateLimiter(BaseRateLimiter):
    current_window: int
    current_counts: dict[str, int]
    previous_counts: dict[str, int]

    def __init__(self, times: int, seconds: int, key_func: RateLimitKeyFunc = ip_based_key_func):
        super().__init__(times, seconds, key_func)
        self.current_window = 0
        self.current_counts = {}
        self.previous_counts = {}

    def _rotate(self, window: int):
        if window == self.current_window:
            return
        if window == self.current_window + 1:
            self.previous_counts = self.current_counts
        else:
            self.previous_counts = {}
        self.current_counts = {}
        self.current_window = window

    async def __call__(self, request: Request, response: Response) -> Response:
        key = self.key_func(request)
        now = time.time()
        window = int(now // self.period)
        elapsed_ratio = (now % self.period) / self.period

        self._rotate(window)

        prev = self.previous_counts.get(key, 0)
        curr = self.current_counts.get(key, 0)
        estimated = prev * (1 - elapsed_ratio) + curr

        reset_after = self.period - (now % self.period)

        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Reset"] = str(math.ceil(reset_after))

        if estimated >= self.limit:
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = str(math.ceil(reset_after))
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

        self.current_counts[key] = curr + 1
        remaining = self.limit - math.ceil(prev * (1 - elapsed_ratio) + curr + 1)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response
