import datetime

from pydantic import BaseModel, ConfigDict


class TokenInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: str
    permissions: list[str]
    expires_at: datetime.datetime | None


class TokenInfoResponse(TokenInfo):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime.datetime


class UserInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: TokenInfoResponse
    score: int
    common_ips: list[str]
