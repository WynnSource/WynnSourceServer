from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.schemas.constants import __DESCRIPTION__, __NAME__, __VERSION__


def custom_openapi(app: FastAPI):
    def openapi():
        nonlocal app

        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=__NAME__,
            version=__VERSION__,
            summary=f"{__NAME__} API Documentation",
            description=__DESCRIPTION__,
            routes=app.routes,
        )

        openapi_schema["x-tagGroups"] = [{"name": "v2", "tags": ["management", "pool"]}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return openapi


RATE_LIMIT_DOCS = {
    200: {
        "headers": {
            "X-RateLimit-Limit": {"schema": {"type": "integer"}, "description": "Requests allowed per window"},
            "X-RateLimit-Remaining": {"schema": {"type": "integer"}, "description": "Requests remaining"},
            "X-RateLimit-Reset": {"schema": {"type": "integer"}, "description": "Seconds until reset"},
        },
    },
    429: {
        "description": "Too Many Requests",
        "headers": {
            "X-RateLimit-Limit": {"schema": {"type": "integer"}, "description": "Requests allowed per window"},
            "X-RateLimit-Remaining": {"schema": {"type": "integer"}, "description": "Requests remaining"},
            "X-RateLimit-Reset": {"schema": {"type": "integer"}, "description": "Seconds until reset"},
            "X-Retry-After": {"schema": {"type": "integer"}, "description": "Seconds until you can retry"},
        },
    },
}

CACHE_DOCS = {
    200: {
        "headers": {
            "X-Cache": {"schema": {"type": "string", "enum": ["HIT", "MISS"]}, "description": "Cache status"},
        }
    }
}
