from fastapi import APIRouter

from app.core.router import DocedAPIRoute
from app.schemas.enums import ApiTag

MarketRouter = APIRouter(route_class=DocedAPIRoute, prefix="/market", tags=[ApiTag.MARKET])
