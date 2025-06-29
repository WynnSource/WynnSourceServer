from typing import Optional

from app.domain.enums.pool import Rarity
from app.domain.response.v1.pool import ShinyData
from pydantic import BaseModel


class CrowdSourceLootPoolData(BaseModel):
    shiny: Optional[ShinyData] = None
    items: dict[Rarity, list[str]]
