import re
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED

from app.config import ADMIN_CONFIG
from app.core.db import SessionDep
from app.core.log import LOGGER

from .model import User, UserRepository


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


async def verify_user(user: User):
    if user.expires_at and user.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="API key has expired")


api_key_scheme = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def get_user(
    request: Request,
    session: SessionDep,
    api_key: Annotated[str | None, Security(api_key_scheme)] = None,
    x_real_ip: Annotated[str | None, Header(alias="X-Real-IP", include_in_schema=False)] = None,
) -> User:
    if api_key == ADMIN_CONFIG.token and ADMIN_CONFIG.token is not None:
        # Create a dummy token with all permissions for the admin token
        LOGGER.info("Admin token used, granting all permissions")
        return User(
            id=-1,
            token="<admin>",
            permissions=["*"],
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC),
            is_active=True,
            creation_ip="unknown",
            common_ips=[],
            score=0,
        )
    else:
        if api_key is None:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="missing API key")

        userRepo = UserRepository(session)
        api_key = hash_token(api_key)
        user = await userRepo.get_user_by_token(api_key)

        if not user:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User not found for token")

        assert request.client is not None

        if request.client.host == "127.0.0.1":
            LOGGER.warning(f"Token {user.token} used from localhost without X-Real-IP header")
        elif x_real_ip is None:
            LOGGER.warning(f"Token {user.token} used without X-Real-IP header")
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Cannot determine client IP address")

        await userRepo.update_user_ip(user, x_real_ip or request.client.host)

        await verify_user(user)

        request.state.user_id = user.id  # Store user ID in request state for later use (e.g. rate limiting)
        return user


UserDep = Annotated[User, Depends(get_user)]
IpDep = Annotated[str, Header(alias="X-Real-IP", include_in_schema=False)]


def depends_permission(permission: str | set[str]):
    async def dependency(user: UserDep) -> User:
        if not has_permission(permission, set(user.permissions)):
            LOGGER.debug(f"User {user.token} does not have required permissions: {permission}")
            LOGGER.debug(f"User {user.token} permissions: {user.permissions}")
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


@lru_cache(maxsize=1024)
def hash_token(token_str: str) -> str:
    return sha256(token_str.encode()).hexdigest()


def hash_tokens(token_strs: list[str]) -> list[str]:
    return [hash_token(t) for t in token_strs]


__all__ = ["UserDep", "depends_permission", "get_user", "hash_token", "hash_tokens"]
