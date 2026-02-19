import re
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED

from app.config import ADMIN_CONFIG
from app.core.db import get_session
from app.core.log import LOGGER

from .model import Token, User, get_user_by_token, update_user_ip


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


def check_permissions(token: Token, required_permissions: set[str] | None) -> None:
    """
    Check if the token's permissions satisfy the required permissions.
    Raises HTTPException if permissions are insufficient.
    """
    user_permissions = set(token.permissions)
    if not has_permission(required_permissions, user_permissions):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Insufficient permissions")


async def verify_token(user: User):
    token = user.token
    if token.expires_at and token.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="API key has expired")


api_key_scheme = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def get_user(
    request: Request,
    x_real_ip: Annotated[str | None, Header(alias="X-Real-IP", include_in_schema=False)] = None,
    api_key: str = Security(api_key_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if api_key == ADMIN_CONFIG.token and ADMIN_CONFIG.token is not None:
        # Create a dummy token with all permissions for the admin token
        LOGGER.info("Admin token used, granting all permissions")
        return User(
            token=Token(
                token="<admin>",
                permissions=["*"],
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC),
            ),
            score=0,
            common_ips=[],
        )
    else:
        api_key = hash_token(api_key)
        user = await get_user_by_token(session, api_key)

        assert request.client is not None

        if request.client.host == "127.0.0.1":
            LOGGER.warning(f"Token {user.token.token} used from localhost without X-Real-IP header")
        elif x_real_ip is None:
            LOGGER.warning(f"Token {user.token.token} used without X-Real-IP header")
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Cannot determine client IP address")
        await update_user_ip(session, user, x_real_ip or request.client.host)
        if not user:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User not found for token")
        return user


def depends_permission(permission: str | set[str]):
    async def dependency(request: Request, user: User = Depends(get_user), session=Depends(get_session)) -> User:
        if not has_permission(permission, set(user.token.permissions)):
            LOGGER.warning(f"User {user.token.token} does not have required permissions: {permission}")
            LOGGER.debug(f"User {user.token.token} permissions: {user.token.permissions}")
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return user

    return dependency


# Used before custom APIRoute is implemented, kept for reference and potential future use
# async def require_permission(request: Request, user: User = Depends(get_user), session=Depends(get_session)) -> User:

#     # Fetch the required permissions from the endpoint metadata
#     endpoint = request.scope.get("endpoint")
#     metadata = getattr(endpoint, "__metadata__", None)
#     if not isinstance(metadata, EndpointMetadata):
#         LOGGER.error(f"Endpoint {endpoint} does not have metadata or is not an EndpointMetadata instance")
#         raise HTTPException(status_code=500, detail="Internal Server Error: Missing endpoint metadata")
#     required_perms = metadata.permission

#     if not has_permission(required_perms, set(user.token.permissions)):
#         LOGGER.warning(f"User {user.token.token} does not have required permissions: {required_perms}")
#         LOGGER.debug(f"User {user.token.token} permissions: {user.token.permissions}")
#         raise HTTPException(status_code=403, detail="Insufficient permissions")

#     return user


async def get_token(token_str: str, session=Depends(get_session)) -> Token:
    LOGGER.debug(f"Verifying token: {token_str}")
    user = await get_user_by_token(session, token_str)
    await verify_token(user)
    return user.token


def hash_token(token_str: str) -> str:
    if token_str is None:
        return None
    return sha256(token_str.encode()).hexdigest()


def hash_tokens(token_strs: list[str]) -> list[str]:
    return [sha256(t.encode()).hexdigest() for t in token_strs]
