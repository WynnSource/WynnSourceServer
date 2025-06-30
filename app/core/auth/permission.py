import re
from functools import lru_cache
from typing import Annotated

from app.config import ADMIN_CONFIG
from app.core.db import get_session
from app.core.metadata import EndpointMetadata
from app.log import LOGGER
from fastapi import Depends, Header, HTTPException, Request

from .model import Permission, Token, get_token


@lru_cache(maxsize=256)
def _compile_pattern(pattern: str) -> re.Pattern:
    """
    Compile user permission pattern (with optional *) into a regex pattern.
    """
    escaped = re.escape(pattern).replace(r"\*", ".*")
    return re.compile(f"^{escaped}$")


def has_permission(required: str | set[str] | None, user: set[str]) -> bool:
    """
    Check if the user's permissions satisfy the required permissions.
    Only user permissions can contain wildcards (*).
    """
    if required is None:
        return True

    if isinstance(required, str):
        required = {required}

    for req in required:
        # Check for exact match or wildcard match in user permissions
        if not any(
            _compile_pattern(user_perm).fullmatch(req) if "*" in user_perm else user_perm == req for user_perm in user
        ):
            return False
    return True


async def require_permission(
    request: Request, token: Annotated[str, Header(alias="X-API-KEY")], session=Depends(get_session)
) -> Token:
    if not token:
        LOGGER.error("Missing API Token in request headers")
        raise HTTPException(status_code=401, detail="Missing API Token")

    if token == ADMIN_CONFIG.token:
        LOGGER.debug("Admin token used, skipping permission check")
        return Token(token="redacted", permissions=[Permission(permission_id="*")])

    # Fetch the required permissions from the endpoint metadata
    endpoint = request.scope.get("endpoint")
    metadata = getattr(endpoint, "__metadata__", None)
    if not isinstance(metadata, EndpointMetadata):
        LOGGER.error(f"Endpoint {endpoint} does not have metadata or is not an EndpointMetadata instance")
        raise HTTPException(status_code=500, detail="Internal Server Error: Missing endpoint metadata")
    required_perms = metadata.permission

    # Fetch the user permissions from database
    user_token = await get_token(session, token)
    if not user_token:
        LOGGER.warning(f"Invalid API Token: {token}")
        raise HTTPException(status_code=401, detail="Invalid API Token")
    user_perms = {perm.permission_id for perm in user_token.permissions}

    if not has_permission(required_perms, user_perms):
        LOGGER.warning(f"User {user_token.token} does not have required permissions: {required_perms}")
        LOGGER.debug(f"User {user_token.token} permissions: {user_perms}")
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return user_token
