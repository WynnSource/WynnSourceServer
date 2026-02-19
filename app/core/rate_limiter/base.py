import abc
from collections.abc import Callable

from fastapi import Request, Response

type RateLimitKeyFunc = Callable[[Request], str]


def default_key_func(request: Request) -> str:
    """
    Default key function that uses the client's IP address for rate limiting.
    If none of the above is available, it falls back to a global limit across all clients.
    """
    ip = request.headers.get("X-Real-IP") or (request.client.host if request.client else "global")
    path = request.url.path
    method = request.method
    return f"rate_limiting:{method}:{path}:{ip}"


class BaseRateLimiter(abc.ABC):
    limit: int
    period: int
    key_func: RateLimitKeyFunc

    def __init__(self, limit: int, period: int, key_func: RateLimitKeyFunc = default_key_func):
        self.limit = limit
        self.period = period
        self.key_func = key_func

    @abc.abstractmethod
    async def __call__(self, request: Request, response: Response) -> Response:
        pass
