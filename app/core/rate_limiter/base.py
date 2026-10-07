import abc
from collections.abc import Callable

from fastapi import Request, Response

from app.core.metrics import RATE_LIMITED, route_template

type RateLimitKeyFunc = Callable[[Request], str]


def ip_based_key_func(request: Request) -> str:
    """
    Default key function that uses the client's IP address for rate limiting.
    If none of the above is available, it falls back to a global limit across all clients.
    """
    ip = request.headers.get("X-Real-IP") or (request.client.host if request.client else "global")
    path = request.url.path
    method = request.method
    return f"rate_limiting:{method}:{path}:{ip}"


def user_based_key_func(request: Request) -> str:
    """
    Key function that uses the authenticated user's ID for rate limiting.
    If the user is not authenticated, it falls back to a global limit across all clients.
    """
    user_id = getattr(request.state, "user_id", None) or "global"
    path = request.url.path
    method = request.method
    return f"rate_limiting:{method}:{path}:{user_id}"


class BaseRateLimiter(abc.ABC):
    limit: int
    period: int
    key_func: RateLimitKeyFunc

    def __init__(self, limit: int, period: int, key_func: RateLimitKeyFunc = ip_based_key_func):
        self.limit = limit
        self.period = period
        self.key_func = key_func

    def record_rejection(self, request: Request) -> None:
        RATE_LIMITED.add(
            1,
            {"route": route_template(request), "key": "user" if self.key_func is user_based_key_func else "ip"},
        )

    @abc.abstractmethod
    async def __call__(self, request: Request, response: Response) -> Response:
        pass
