from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import metadata
from app.core.db import get_session
from app.core.rate_limiter import user_based_key_func
from app.core.router import DocedAPIRoute

from .schema import PoolSubmissionSchema
from .service import submit_pool_data

PoolRouter = APIRouter(route_class=DocedAPIRoute, prefix="/pool", tags=["pool"])


@PoolRouter.post("/submit", summary="Submit Pool Data")
@metadata.rate_limit(limit=30, period=60, key_func=user_based_key_func)
async def handle_pool_data_submission(data: PoolSubmissionSchema, session: AsyncSession = Depends(get_session)):
    """
    Endpoint for clients to submit pool data.
    """
    return await submit_pool_data(session, data)
