import datetime
from typing import Self

from pydantic import BaseModel

from app.core.security.model import Token, User


class TokenInfo(BaseModel):
    token: str
    permissions: list[str]
    expires_at: datetime.datetime | None

    @classmethod
    def from_orm(cls, obj: Token) -> Self:
        return cls(
            token=obj.token,
            permissions=obj.permissions,
            expires_at=obj.expires_at,
        )


class TokenInfoResponse(TokenInfo):
    created_at: datetime.datetime

    @classmethod
    def from_orm(cls, obj: Token) -> Self:
        return cls(
            token=obj.token,
            permissions=obj.permissions,
            expires_at=obj.expires_at,
            created_at=obj.created_at,
        )


class UserInfoResponse(BaseModel):
    token: TokenInfoResponse
    score: int
    common_ips: list[str]

    @classmethod
    def from_orm(cls, obj: User) -> Self:
        return cls(
            token=TokenInfoResponse.from_orm(obj.token),
            score=obj.score,
            common_ips=obj.common_ips,
        )
