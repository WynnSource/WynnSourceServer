from fastapi import APIRouter

from app.core import metadata
from app.core.router import DocedAPIRoute
from app.module.api.schema import ValidationErrorResponse
from app.module.manage.router import ManageRouter
from app.module.pool.router import PoolRouter
from app.schemas.response import StatusResponse

Router = APIRouter(route_class=DocedAPIRoute, prefix="/api/v2", responses={422: {"model": ValidationErrorResponse}})
Router.include_router(ManageRouter)
Router.include_router(PoolRouter)


@Router.get("/test")
@metadata.rate_limit(10, 60)
@metadata.cached(expire=60)
@metadata.permission("api.test")
async def test_endpoint() -> StatusResponse:
    """
    Test endpoint to verify API is working.
    """
    return StatusResponse()
