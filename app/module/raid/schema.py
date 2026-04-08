from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.module.pool.schema import RaidRegion

from .config import GAMBIT_COUNT


class GambitEntry(BaseModel):
    name: str = Field(description="Gambit name", max_length=255)
    description: str = Field(description="Gambit description", max_length=255)


class GambitSubmissionSchema(BaseModel):
    region: RaidRegion
    client_timestamp: datetime
    mod_version: str
    gambits: list[GambitEntry] = Field(
        description="List of gambits (partial submission allowed, up to 4)",
        min_length=1,
        max_length=GAMBIT_COUNT,
    )

    @model_validator(mode="after")
    def check_no_duplicate_names(self) -> "GambitSubmissionSchema":
        names = [g.name for g in self.gambits]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate gambit names are not allowed")
        return self


class GambitConsensusEntry(BaseModel):
    name: str
    description: str
    confidence: float = Field(description="Confidence for this gambit entry")


class GambitConsensusResponse(BaseModel):
    region: str
    rotation_start: datetime
    rotation_end: datetime
    gambits: list[GambitConsensusEntry]
    confidence: float = Field(description="Overall confidence level")
