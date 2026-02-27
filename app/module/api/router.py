from fastapi import APIRouter

from app.core import metadata
from app.core.router import DocedAPIRoute
from app.module.beta.router import BetaRouter
from app.module.manage.router import ManageRouter
from app.module.market.router import MarketRouter
from app.module.pool.router import PoolRouter
from app.schemas.enums import ApiTag, ItemReturnType
from app.schemas.response import StatusResponse, WCSResponse

from .schema import MappingResponse, MappingType, RandomItemResponse, ValidationErrorResponse
from .service import MappingStorage, generate_random_item

Router = APIRouter(
    route_class=DocedAPIRoute, prefix="/api/v2", responses={422: {"model": ValidationErrorResponse}}
)
Router.include_router(ManageRouter)
Router.include_router(PoolRouter)
Router.include_router(MarketRouter)
Router.include_router(BetaRouter)


@Router.get("/test", summary="Test endpoint", tags=[ApiTag.MISC])
@metadata.rate_limit(10, 60)
@metadata.cached(expire=60)
@metadata.permission("api.test")
async def test_endpoint() -> StatusResponse:
    """
    Test endpoint for various features like rate limiting, caching, and permissions.
    """
    return StatusResponse()


@Router.get("/mappings/{mapping_type}", summary="Get ID Mappings", tags=[ApiTag.MISC])
@metadata.rate_limit(10, 60)
@metadata.cached(expire=3600)  # TTL 1 hour, updated by scheduled job
async def get_mappings(mapping_type: MappingType) -> MappingResponse:
    """
    Get ID mappings for a given type.
    """

    storage = MappingStorage().get_instance()
    return MappingResponse.model_validate(await storage.get_mapping(mapping_type), extra="ignore")


@Router.get("/item/random", summary="Get Random Item", tags=[ApiTag.MISC])
@metadata.rate_limit(10, 60)
async def get_random_item(
    item_return_type: ItemReturnType = ItemReturnType.B64,
) -> WCSResponse[RandomItemResponse]:
    """
    Get a random item for testing purposes.
    """
    return WCSResponse(
        data=RandomItemResponse(item=item_return_type.format_item(generate_random_item()))
    )
