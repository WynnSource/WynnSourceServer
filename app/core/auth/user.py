from typing import Annotated

from app.config import ADMIN_CONFIG
from app.core.db import get_session
from app.log import LOGGER
from fastapi import Depends, Header

from .model import Permission, Token, get_token


async def get_user(token: Annotated[str, Header(alias="X-API-KEY")], session=Depends(get_session)) -> Token | None:
    if token == ADMIN_CONFIG.token:
        LOGGER.debug("Admin token used, skipping permission check")
        return Token(token="redacted", permissions=[Permission(permission_id="*")])
    return await get_token(session, token)
