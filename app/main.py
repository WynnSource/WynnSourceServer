from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError, ResponseValidationError

from app.core.db import init_db
from app.docs.openapi import custom_openapi
from app.domain.constants import __DESCRIPTION__, __NAME__, __VERSION__
from app.domain.response import STATUS_RESPONSE, StatusResponse
from app.module.api import V1Router, v1_exception_handler, v1_validation_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Initializes the scheduler and sets it up to run in the background.
    """
    scheduler = AsyncIOScheduler()
    scheduler.start()
    await init_db()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=__NAME__,
    description=__DESCRIPTION__,
    version=__VERSION__,
    docs_url=None,
    redoc_url="/docs",
    lifespan=lifespan,
)
app.include_router(V1Router)
app.exception_handler(HTTPException)(v1_exception_handler)
app.exception_handler(RequestValidationError)(v1_validation_exception_handler)
app.exception_handler(ResponseValidationError)(v1_validation_exception_handler)
app.openapi = custom_openapi(app)


@app.get("/")
async def read_root() -> StatusResponse:
    return STATUS_RESPONSE


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="debug",
    )
