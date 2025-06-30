from app.core.metadata import EndpointMetadata
from app.domain.constants import __DESCRIPTION__, __NAME__, __VERSION__
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute


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

        for route in app.routes:
            if isinstance(route, APIRoute):
                path = route.path
                method = route.methods.pop().lower()
                endpoint = route.endpoint
                permissions = []

                if hasattr(endpoint, "__metadata__"):
                    meta = getattr(endpoint, "__metadata__")
                    if isinstance(meta, EndpointMetadata) and meta.permission:
                        permissions.append(meta.permission)

                if permissions:
                    desc = openapi_schema["paths"][path][method].get("description", "")
                    perms_str = "\n\n🛡 Required Permission(s): " + ", ".join(f"`{p}`" for p in permissions)
                    openapi_schema["paths"][path][method]["description"] = desc + perms_str

        # Tag groups
        openapi_schema["x-tagGroups"] = [{"name": "v1", "tags": ["management", "pool"]}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return openapi
