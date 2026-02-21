import enum
from datetime import datetime

from pydantic import BaseModel, Field


class LootPoolType(enum.StrEnum):
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


VALID_REGIONS: dict[LootPoolType, type[enum.StrEnum]] = {
    LootPoolType.ITEM: LootPoolRegion,
    LootPoolType.RAID_ASPECT: RaidRegion,
    LootPoolType.RAID_TOME: RaidRegion,
}


class PoolSubmissionSchema(BaseModel):
    pool_type: LootPoolType
    region: str = Field(description="Region or raid for the loot pool, e.g. 'Sky', 'TNA', etc.")
    page: int
    client_timestamp: datetime
    items: list[str] = Field(description="base64-encoded protobuf bytes for item")
