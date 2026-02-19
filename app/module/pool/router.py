from fastapi import APIRouter

from app.core import metadata
from app.core.rate_limiter import user_based_key_func
from app.core.router import DocedAPIRoute

PoolRouter = APIRouter(route_class=DocedAPIRoute, prefix="/pool", tags=["pool"])


@PoolRouter.get("/submit", summary="Submit Pool Data")
@metadata.rate_limit(limit=30, period=60, key_func=user_based_key_func)
async def submit_pool_data():
    """
    Endpoint for clients to submit pool data.
    """
    return {"message": "Pool data submitted successfully"}
