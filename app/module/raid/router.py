import datetime

from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from app.core import metadata
from app.core.db import SessionDep, get_session
from app.core.rate_limiter import ip_based_key_func, user_based_key_func
from app.core.router import DocedAPIRoute
from app.core.security.auth import UserDep
from app.module.pool.schema import RaidRegion
from app.schemas.enums import ApiTag
from app.schemas.response import EMPTY_RESPONSE, EmptyResponse, WCSResponse

from .config import get_gambit_rotation
from .schema import GambitConsensusEntry, GambitConsensusResponse, GambitSubmissionSchema
from .service import compute_gambit_consensus, get_gambit_consensus
from .service import submit_gambit_data as svc_submit_gambit_data

RaidRouter = APIRouter(route_class=DocedAPIRoute, prefix="/raid", tags=[ApiTag.RAID])


@RaidRouter.get("/gambit/recalc", summary="Force Recalculate Gambit Consensus")
@metadata.permission("raid.recalc")
async def recalculate_gambits() -> EmptyResponse:
    """
    Force recalculate gambit consensus.
    """
    await compute_gambit_consensus()
    return EMPTY_RESPONSE


@RaidRouter.post("/gambit/submit", summary="Submit Gambit Data")
@metadata.rate_limit(limit=30, period=60, key_func=user_based_key_func)
async def submit_gambit_data(data: list[GambitSubmissionSchema], user: UserDep) -> EmptyResponse:
    """
    Submit gambit data for the current rotation.
    Partial submissions are supported (1-4 gambits per region).
    """
    for submission in data:
        try:
            async with get_session() as session:
                await svc_submit_gambit_data(session, submission, user)
        except ValueError:
            continue

    return EMPTY_RESPONSE


@RaidRouter.get("/gambit/{region}", summary="Get Current Gambit Consensus")
@metadata.rate_limit(limit=10, period=60, key_func=ip_based_key_func)
@metadata.cached(expire=120)
async def get_gambit_by_region(
    region: RaidRegion,
    session: SessionDep,
) -> WCSResponse[GambitConsensusResponse]:
    """
    Get gambit consensus data for a raid region.
    """
    try:
        rotation = get_gambit_rotation(datetime.datetime.now(tz=datetime.UTC))
        result = await get_gambit_consensus(session, region, rotation.start)

        if result is None:
            data = GambitConsensusResponse(
                region=region,
                rotation_start=rotation.start,
                rotation_end=rotation.end,
                gambits=[],
                confidence=0.0,
            )
        else:
            pairs, confidence = result
            data = GambitConsensusResponse(
                region=region,
                rotation_start=rotation.start,
                rotation_end=rotation.end,
                gambits=[
                    GambitConsensusEntry(
                        name=name,
                        description=desc,
                        confidence=confidence,
                    )
                    for name, desc in pairs
                ],
                confidence=confidence,
            )

    except ValueError as e:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

    return WCSResponse(data=data)
