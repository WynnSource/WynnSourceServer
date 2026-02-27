from datetime import datetime

from pydantic import BaseModel, Field


class NewItemSubmission(BaseModel):
    client_timestamp: datetime
    mod_version: str
    items: list[str] = Field(
        description="List of base64-encoded protobuf bytes for items",
        examples=[["aXRlbV9kYXRhXzE=", "aXRlbV9kYXRhXzI="]],
    )


class BetaItemListResponse(BaseModel):
    items: list[str] | list[dict] = Field(
        description="List of items in the beta list, "
        + "format depends on item_return_type query parameter",
        examples=[["aXRlbV9kYXRhXzE=", "aXRlbV9kYXRhXzI="]],
    )
