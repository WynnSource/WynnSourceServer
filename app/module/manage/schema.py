from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserInfoRequest(BaseModel):
    token: str
    permissions: list[str]
    expires_at: datetime | None = None


class UserInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    token: str
    permissions: list[str]

    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True

    creation_ip: str
    # A list of common IPs used by this user, ordered from oldest to newest.
    common_ips: list[str]

    score: int
