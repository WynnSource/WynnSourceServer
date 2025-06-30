from typing import Optional

from app.domain.enums import LootPoolType, Rarity
from pydantic import BaseModel

from .common import ShinyData


class CrowdSourceLootPoolData(BaseModel):
    type: LootPoolType
    location: str
    page: int
    shiny: Optional[ShinyData] = None
    items: dict[Rarity, list[str]]
