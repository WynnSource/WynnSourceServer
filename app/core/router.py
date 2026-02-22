import inspect
from collections.abc import Callable, Sequence
from enum import Enum
from functools import wraps
from typing import Any

from fastapi import Depends, Request, Response, params
from fastapi.routing import APIRoute

from app.core.cache import cached
from app.core.metadata import EndpointMetadata
from app.core.openapi import CACHE_DOCS, RATE_LIMIT_DOCS
from app.core.rate_limiter import RateLimiter, user_based_key_func
from app.core.security.auth import depends_permission, get_user
from app.schemas.constants import INJECTED_NAMESPACE
from app.utils.time_utils import format_time


class DocedAPIRoute(APIRoute):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        dependencies: Sequence[params.Depends] | None = None,
        responses: dict[int | str, dict[str, Any]] | None = None,
        description: str | None = None,
        tags: list[str | Enum] | None = None,
        **kwargs,
    ):

        # meta related processing
        meta: EndpointMetadata = getattr(endpoint, "__metadata__", EndpointMetadata())

        if meta.processed:
            super().__init__(
                path,
                endpoint,
                dependencies=dependencies,
                responses=responses,
                description=description,
                tags=tags,
                **kwargs,
            )
            return

        meta.processed = True

        responses = responses or {}
        dependencies = list(dependencies or [])

        # Inject caching
        if meta.cache:
            endpoint = cached(expire=meta.cache.expire)(self.inject_sig(endpoint))

            for status_code, doc in CACHE_DOCS.items():
                if status_code not in responses:
                    responses[status_code] = {}

                if "headers" not in responses[status_code]:
                    responses[status_code]["headers"] = {}
                responses[status_code]["headers"].update(doc["headers"])

                if "description" in doc and "description" not in responses[status_code]:
                    responses[status_code]["description"] = doc["description"]

            description = self.add_description(
                f"⌛ This response is cached for `{meta.cache.expire}` seconds.", description, endpoint
            )

        # Add permission info to description and inject permission dependency
        if meta.permission:
            description = self.add_description(
                "🛡️ Required Permission(s): "
                + ", ".join(
                    f"`{p}`" for p in (meta.permission if isinstance(meta.permission, set) else {meta.permission})
                ),
                description,
                endpoint,
            )

            dependencies = [*list(dependencies or []), Depends(depends_permission(meta.permission))]

        # Add rate limit docs and inject rate limit dependency
        if meta.rate_limit:
            for status_code, doc in RATE_LIMIT_DOCS.items():
                if status_code not in responses:
                    responses[status_code] = {}

                if "headers" not in responses[status_code]:
                    responses[status_code]["headers"] = {}
                responses[status_code]["headers"].update(doc["headers"])

                if "description" in doc and "description" not in responses[status_code]:
                    responses[status_code]["description"] = doc["description"]

            description = self.add_description(
                f"⏱️ Rate Limited: `{meta.rate_limit.limit}` requests per `{format_time(meta.rate_limit.period)}` "
                + f" based on {'user' if meta.rate_limit.key_func == user_based_key_func else 'IP'}.",
                description,
                endpoint,
            )

            if meta.rate_limit.key_func == user_based_key_func:
                self.add_dependency(Depends(get_user), dependencies)  # Ensure user is loaded

            self.add_dependency(
                Depends(RateLimiter(meta.rate_limit.limit, meta.rate_limit.period, meta.rate_limit.key_func)),
                dependencies,
            )

        super().__init__(
            path,
            endpoint,
            dependencies=dependencies,
            responses=responses,
            description=description,
            tags=tags,
            **kwargs,
        )

    def add_description(self, text: str, description: str | None, endpoint: Callable[..., Any]) -> str:
        description = description or inspect.cleandoc(endpoint.__doc__ or "")
        if description:
            description += "\n\n"
        description += text
        return description

    def inject_sig(self, endpoint: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(endpoint)
        has_request = any(p.annotation is Request for p in sig.parameters.values())
        has_response = any(p.annotation is Response for p in sig.parameters.values())

        @wraps(endpoint)
        async def injected_endpoint(*args, **kwargs):
            fn_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            return await endpoint(*args, **fn_kwargs)

        if not has_request or not has_response:
            new_params = list(sig.parameters.values())
            if not has_request:
                new_params.append(
                    inspect.Parameter(
                        f"{INJECTED_NAMESPACE}request", inspect.Parameter.KEYWORD_ONLY, annotation=Request
                    )
                )
            if not has_response:
                new_params.append(
                    inspect.Parameter(
                        f"{INJECTED_NAMESPACE}response", inspect.Parameter.KEYWORD_ONLY, annotation=Response
                    )
                )
            setattr(injected_endpoint, "__signature__", sig.replace(parameters=new_params))
        return injected_endpoint

    def add_dependency(self, dependency: params.Depends, dependencies: list[params.Depends]) -> None:
        if dependency not in dependencies:
            dependencies.append(dependency)


__all__ = ["DocedAPIRoute"]
