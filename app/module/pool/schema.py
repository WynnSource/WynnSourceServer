import enum
from datetime import datetime

from pydantic import BaseModel, Field


class PoolType(enum.StrEnum):
    ITEM = "lr_item_pool"
    RAID_ASPECT = "raid_aspect_pool"
    RAID_TOME = "raid_tome_pool"


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
    PoolType.ITEM: LootPoolRegion,
    PoolType.RAID_ASPECT: RaidRegion,
    PoolType.RAID_TOME: RaidRegion,
}


class PoolSubmissionSchema(BaseModel):
    pool_type: PoolType
    region: LootPoolRegion | RaidRegion
    page: int
    client_timestamp: datetime
    mod_version: str
    items: list[str] = Field(
        description="base64-encoded protobuf bytes for item",
        json_schema_extra={"example": ["aXRlbV9kYXRhXzE=", "aXRlbV9kYXRhXzI="]},
    )


class PoolConsensusResponse(BaseModel):
    pool_type: PoolType
    region: LootPoolRegion | RaidRegion
    page_consensus: list["PageConsensus"]

    class PageConsensus(BaseModel):
        page: int = Field(description="The page number")
        items: list[str] = Field(
            description="Consensus item data (protobuf bytes in base64 encoding)",
            json_schema_extra={"example": ["aXRlbV9kYXRhXzE=", "aXRlbV9kYXRhXzI="]},
        )
        confidence: float = Field(description="Confidence level, between 0 and 1")
