import re
from functools import lru_cache
from typing import Annotated

from app.config.admin import ADMIN_CONFIG
from app.log import logger
from app.models.manage import Permission, Token, get_token
from app.service.db import get_session
from fastapi import Depends, Header, HTTPException


@lru_cache(maxsize=256)
def _compile_pattern(pattern: str) -> re.Pattern:
    """
    Compile user permission pattern (with optional *) into a regex pattern.
    """
    escaped = re.escape(pattern).replace(r"\*", ".*")
    return re.compile(f"^{escaped}$")


def has_permission(required: set[str], user: set[str]) -> bool:
    """
    Check if the user's permissions satisfy the required permissions.
    Only user permissions can contain wildcards (*).
    """
    for req in required:
        # Check for exact match or wildcard match in user permissions
        if not any(
            _compile_pattern(user_perm).fullmatch(req) if "*" in user_perm else user_perm == req for user_perm in user
        ):
            return False
    return True


def require_permission(required_perms: str | set[str]):
    async def check_permission(token: Annotated[str, Header(alias="X-API-KEY")], session=Depends(get_session)) -> Token:
        nonlocal required_perms

        if not token:
            raise HTTPException(status_code=401, detail="Missing API Token")
        if token == ADMIN_CONFIG.token:
            logger.debug("Admin token used, skipping permission check")
            return Token(token="redacted", permissions=[Permission(permission_id="*")])
        user_token = await get_token(session, token)
        if not user_token:
            raise HTTPException(status_code=401, detail="Invalid API Token")

        user_perms = {perm.permission_id for perm in user_token.permissions}

        if isinstance(required_perms, str):
            required_perms = {required_perms}

        if not has_permission(required_perms, user_perms):
            logger.warning(f"User {user_token.token} does not have required permissions: {required_perms}")
            logger.debug(f"User {user_token.token} permissions: {user_perms}")
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return user_token

    return check_permission


async def get_user(token: Annotated[str, Header(alias="X-API-KEY")], session=Depends(get_session)) -> Token | None:
    if token == ADMIN_CONFIG.token:
        logger.debug("Admin token used, skipping permission check")
        return Token(token="redacted", permissions=[Permission(permission_id="*")])
    return await get_token(session, token)


__all__ = [
    "require_permission",
    "get_user",
]
