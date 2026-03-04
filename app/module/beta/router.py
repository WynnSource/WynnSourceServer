from fastapi import APIRouter, Body

from app.core import metadata
from app.core.db import SessionDep
from app.core.router import DocedAPIRoute
from app.schemas.enums import ItemReturnType
from app.schemas.enums.tag import ApiTag
from app.schemas.response import EmptyResponse, WCSResponse

from .schema import BetaItemListResponse, ItemPatchSubmission, NewItemSubmission
from .service import (
    get_beta_items,
    get_beta_items_by_name,
    handle_clear_beta_items,
    handle_delete_beta_items,
    handle_item_submission,
    handle_patch_submission,
)

BetaRouter = APIRouter(route_class=DocedAPIRoute, prefix="/beta", tags=[ApiTag.BETA])


@BetaRouter.get("/items", summary="List Beta Items")
@metadata.rate_limit(limit=10, period=60)
@metadata.cached(expire=30)
async def list_beta_items(
    session: SessionDep,
    item_return_type: ItemReturnType = ItemReturnType.B64,
) -> WCSResponse[BetaItemListResponse]:
    """
    List all items in the beta list.
    """
    return WCSResponse(data=BetaItemListResponse(items=item_return_type.format_items(await get_beta_items(session))))


@BetaRouter.post("/items/filter", summary="List Beta Items Filtered")
@metadata.rate_limit(limit=10, period=60)
@metadata.cached(expire=30)
async def list_beta_items_filtered(
    session: SessionDep,
    names: list[str] = Body(default_factory=list, description="Optional list of item names to filter by"),
    item_return_type: ItemReturnType = ItemReturnType.B64,
) -> WCSResponse[BetaItemListResponse]:
    """
    List items in the beta list.
    If `names` query parameter is non-empty, only items with matching names will be returned.
    """
    return WCSResponse(
        data=BetaItemListResponse(items=item_return_type.format_items(await get_beta_items_by_name(session, names)))
    )


@BetaRouter.post("/items", summary="Submit new Beta Item")
@metadata.rate_limit(limit=300, period=60)
async def submit_beta_item(items: NewItemSubmission, session: SessionDep) -> EmptyResponse:
    """
    Submit new items to be added to the beta list.
    """
    await handle_item_submission(items, session)
    return EmptyResponse()


@BetaRouter.post("/items/patch", summary="Patch existing Beta Items")
@metadata.rate_limit(limit=300, period=60)
async def patch_beta_items(submission: ItemPatchSubmission, session: SessionDep) -> EmptyResponse:
    """
    Patch existing items in the beta list. Only fields specified in the submission will be updated.
    """
    await handle_patch_submission(submission, session)
    return EmptyResponse()


@BetaRouter.delete("/items", summary="Delete Beta Items")
@metadata.permission("beta.items.write")
async def delete_beta_items(items: list[str], session: SessionDep) -> EmptyResponse:
    """
    Delete items from the beta list by name.
    """
    await handle_delete_beta_items(items, session)
    return EmptyResponse()


@BetaRouter.delete("/items/clear", summary="Clear Beta Items")
@metadata.permission("beta.items.write")
async def clear_beta_items(session: SessionDep) -> EmptyResponse:
    """
    Clear all items from the beta list.
    """
    await handle_clear_beta_items(session)
    return EmptyResponse()
