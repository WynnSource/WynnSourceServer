from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.staticfiles import StaticFiles
from scalar_fastapi import AgentScalarConfig, OpenAPISource, get_scalar_api_reference

from app.config import DB_CONFIG
from app.core.db import RedisClient, close_db, init_db
from app.core.openapi import custom_openapi
from app.core.scheduler import SCHEDULER
from app.module.api.exception_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.module.api.router import Router
from app.schemas.constants import __DESCRIPTION__, __NAME__, __VERSION__
from app.schemas.response import STATUS_RESPONSE, StatusResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application.
    """
    try:
        SCHEDULER.start()
        await init_db()
        if DB_CONFIG.redis_dsn is not None:
            await RedisClient.init()
        yield
    finally:
        SCHEDULER.shutdown(wait=False)
        await close_db()
        if DB_CONFIG.redis_dsn is not None:
            await RedisClient.close()


app = FastAPI(
    title=__NAME__,
    description=__DESCRIPTION__,
    version=__VERSION__,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    license_info={
        "name": "GNU Affero General Public License v3.0 (AGPL-v3)",
        "identifier": "AGPL-3.0-or-later",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html",
    },
)

app.include_router(Router)
app.exception_handler(HTTPException)(http_exception_handler)
app.exception_handler(RequestValidationError)(validation_exception_handler)
app.exception_handler(ResponseValidationError)(validation_exception_handler)
app.exception_handler(Exception)(generic_exception_handler)
app.openapi = custom_openapi(app)


@app.get("/")
async def read_root() -> StatusResponse:
    return STATUS_RESPONSE


@app.get("/docs", include_in_schema=False)
@app.get("/doc", include_in_schema=False)
async def scalar_ui():
    return get_scalar_api_reference(
        title=f"{__NAME__} API Documentation",
        sources=[
            OpenAPISource(
                slug="wynnsource-api",
                url=app.openapi_url,
            )
        ],
        agent=AgentScalarConfig(disabled=True),
        scalar_favicon_url="./static/favicon.ico",
        default_open_all_tags=True,
        authentication={
            "preferredSecurityScheme": "APIKeyHeader",
        },
    )


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="debug",
    )
