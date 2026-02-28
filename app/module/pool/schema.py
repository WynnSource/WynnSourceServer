import enum
from datetime import datetime

from pydantic import BaseModel, Field


class PoolType(enum.StrEnum):
    LR_ITEM = "lr_item_pool"
    RAID_ASPECT = "raid_aspect_pool"
    RAID_ITEM = "raid_item_pool"


class LootPoolRegion(enum.StrEnum):
    SKY = "Sky"
    MOLTEN = "Molten"
    SE = "SE"
    COTL = "Canyon"
    CORKUS = "Corkus"


class Rarity(enum.StrEnum):
    COMMON = "Common"
    UNIQUE = "Unique"
    RARE = "Rare"
    LEGENDARY = "Legendary"
    MYTHIC = "Mythic"
    FABLED = "Fabled"


class RaidRegion(enum.StrEnum):
    TNA = "TNA"
    TCC = "TCC"
    NOL = "NOL"
    NOTG = "NOTG"


VALID_REGIONS: dict[PoolType, type[enum.StrEnum]] = {
    PoolType.LR_ITEM: LootPoolRegion,
    PoolType.RAID_ASPECT: RaidRegion,
    PoolType.RAID_ITEM: RaidRegion,
}


class PoolSubmissionSchema(BaseModel):
    pool_type: PoolType
    region: str = Field(
        description="Region name, must be one of the valid regions for the pool type"
    )
    page: int
    client_timestamp: datetime
    mod_version: str
    items: list[str] = Field(
        description="base64-encoded protobuf bytes for item",
        examples=[["aXRlbV9kYXRhXzE=", "aXRlbV9kYXRhXzI="]],
    )


class PoolConsensusResponse(BaseModel):
    pool_type: PoolType
    region: str = Field(
        description="Region name, must be one of the valid regions for the pool type"
    )
    rotation_start: datetime
    rotation_end: datetime
    page_consensus: list["PageConsensus"]

    class PageConsensus(BaseModel):
        page: int = Field(description="The page number")
        items: list[str] | list[dict] = Field(
            description="Consensus item data for the page, "
            + "format depends on item_return_type query parameter",
            examples=[["aXRlbV9kYXRhXzE=", "aXRlbV9kYXRhXzI="]],
        )
        confidence: float = Field(description="Confidence level, between 0 and 1")
