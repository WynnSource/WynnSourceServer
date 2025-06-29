from typing import Optional

from app.domain.enums.pool import LootPoolRegion, RaidRegion, Rarity
from app.domain.response.v1.response import V1Response
from pydantic import BaseModel, ConfigDict


class ShinyData(BaseModel):
    item: str
    tracker: str


class LootPoolPagedData(BaseModel):
    shiny: Optional[ShinyData] = None
    items: dict[Rarity, list[str]]

    model_config = ConfigDict(use_enum_values=True)


class ItemLootPoolData(BaseModel):
    loot: dict[LootPoolRegion, dict[int, LootPoolPagedData]]

    model_config = ConfigDict(use_enum_values=True)


class ItemLootPoolResponse(V1Response[ItemLootPoolData]):
    """
    Response model for item loot pools.
    """


# Could be used for both aspects and tomes
class RaidLootPoolData(BaseModel):
    loot: dict[RaidRegion, dict[int, dict[Rarity, list[str]]]]

    model_config = ConfigDict(use_enum_values=True)


class RaidLootPoolResponse(V1Response[RaidLootPoolData]):
    """
    Response model for raid loot pools.
    """


__all__ = [
    "ShinyData",
    "LootPoolPagedData",
    "ItemLootPoolData",
    "ItemLootPoolResponse",
    "RaidLootPoolData",
    "RaidLootPoolResponse",
]
