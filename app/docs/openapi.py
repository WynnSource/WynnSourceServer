from app.domain.constants import __DESCRIPTION__, __NAME__, __VERSION__
from fastapi.openapi.utils import get_openapi


def custom_openapi(app):
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

        # Tag groups
        openapi_schema["x-tagGroups"] = [{"name": "v1", "tags": ["management", "pool"]}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return openapi
