from fastapi import APIRouter

from app.core import metadata
from app.core.db import SessionDep
from app.core.router import DocedAPIRoute
from app.module.beta.schema import BetaItemListResponse, NewItemSubmission
from app.module.beta.service import get_beta_items, handle_item_submission
from app.schemas.enums import ItemReturnType
from app.schemas.enums.tag import ApiTag
from app.schemas.response import EmptyResponse, WCSResponse

BetaRouter = APIRouter(route_class=DocedAPIRoute, prefix="/beta", tags=[ApiTag.BETA])


@BetaRouter.get("/items", summary="List Beta Items")
@metadata.rate_limit(limit=10, period=60)
@metadata.cached(expire=300)
async def list_beta_items(
    session: SessionDep,
    item_return_type: ItemReturnType = ItemReturnType.B64,
) -> WCSResponse[BetaItemListResponse]:
    """
    List all items in the beta list.
    """
    return WCSResponse(
        data=BetaItemListResponse(
            items=item_return_type.format_items(await get_beta_items(session))
        )
    )


@BetaRouter.post("/items", summary="Submit new Beta Item")
@metadata.rate_limit(limit=30, period=60)
async def submit_beta_item(items: NewItemSubmission, session: SessionDep) -> EmptyResponse:
    """
    Submit new items to be added to the beta list.
    """
    await handle_item_submission(items, session)
    return EmptyResponse()
