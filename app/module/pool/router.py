import datetime

from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from app.core import metadata
from app.core.db import SessionDep, get_session
from app.core.rate_limiter import ip_based_key_func, user_based_key_func
from app.core.router import DocedAPIRoute
from app.core.security.auth import UserDep
from app.schemas.enums import ApiTag, ItemReturnType
from app.schemas.response import EMPTY_RESPONSE, EmptyResponse, WCSResponse

from .config import POOL_REFRESH_CONFIG
from .schema import LootPoolRegion, PoolConsensusResponse, PoolSubmissionSchema, PoolType, RaidRegion
from .service import compute_pool_consensus, get_pool_consensus
from .service import submit_pool_data as svc_submit_pool_data

PoolRouter = APIRouter(route_class=DocedAPIRoute, prefix="/pool", tags=[ApiTag.POOL])


@PoolRouter.post("/submit", summary="Submit Pool Data")
@metadata.rate_limit(limit=30, period=60, key_func=user_based_key_func)
async def submit_pool_data(data: list[PoolSubmissionSchema], user: UserDep) -> EmptyResponse:
    """
    Endpoint for clients to submit pool data.
    """
    for submission in data:
        try:
            # We want to process each submission in a different sessions to avoid one bad submission breaking others
            async with get_session() as session:
                await svc_submit_pool_data(session, submission, user)
        except ValueError:
            continue

    return EMPTY_RESPONSE


@PoolRouter.get("/pools/{pool_type}/{region}", summary="Get Current Pool by Type and Region")
@metadata.rate_limit(limit=10, period=60, key_func=ip_based_key_func)
@metadata.cached(expire=120)
async def get_pools_by_type_and_region(
    pool_type: PoolType,
    region: LootPoolRegion | RaidRegion,
    session: SessionDep,
    item_return_type: ItemReturnType = ItemReturnType.B64,
) -> WCSResponse[PoolConsensusResponse]:
    """
    Get pools by type and region.
    """
    try:
        consensus_by_page = await get_pool_consensus(
            session,
            pool_type,
            region,
            rotation_start=POOL_REFRESH_CONFIG[pool_type].get_rotation(datetime.datetime.now(tz=datetime.UTC)).start,
        )

        if not consensus_by_page:
            data = PoolConsensusResponse(pool_type=pool_type, region=region, page_consensus=[])
        else:
            page_consensus = []
            for page, (items, confidence) in consensus_by_page.items():
                page_consensus.append(
                    PoolConsensusResponse.PageConsensus(
                        page=page,
                        items=item_return_type.format_items(items),
                        confidence=confidence,
                    )
                )

            data = PoolConsensusResponse(pool_type=pool_type, region=region, page_consensus=page_consensus)

    except ValueError as e:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

    return WCSResponse(data=data)


@PoolRouter.get("/pools/recalc", summary="Force Recalculate Pool Consensus")
@metadata.permission("pool.recalc")
async def recalculate_pools() -> EmptyResponse:
    """
    Force recalculate pool consensus. This is useful for admins to fix any issues with the consensus calculation.
    """

    await compute_pool_consensus()
    return EMPTY_RESPONSE
