from typing import Optional

from app.domain.enums import LootPoolRegion, RaidRegion, Rarity
from app.domain.response import Response
from pydantic import BaseModel, ConfigDict

from .common import ShinyData


class LootPoolPagedData(BaseModel):
    shiny: Optional[ShinyData] = None
    items: dict[Rarity, list[str]]

    model_config = ConfigDict(use_enum_values=True)


class ItemLootPoolData(BaseModel):
    loot: dict[LootPoolRegion, dict[int, LootPoolPagedData]]

    model_config = ConfigDict(use_enum_values=True)


class ItemLootPoolResponse(Response[ItemLootPoolData]):
    """
    Response model for item loot pools.
    """


class RaidLootPoolPagedData(BaseModel):
    items: dict[Rarity, list[str]]

    model_config = ConfigDict(use_enum_values=True)


# Could be used for both aspects and tomes
class RaidLootPoolData(BaseModel):
    loot: dict[RaidRegion, dict[int, RaidLootPoolPagedData]]

    model_config = ConfigDict(use_enum_values=True)


class RaidLootPoolResponse(Response[RaidLootPoolData]):
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
