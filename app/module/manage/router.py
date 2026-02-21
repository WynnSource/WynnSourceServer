from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

import app.core.metadata as metadata
from app.core.db import get_session
from app.core.log import LOGGER
from app.core.router import DocedAPIRoute
from app.core.security.auth import get_user, hash_token, hash_tokens
from app.core.security.model import (
    User,
    get_user_by_tokens,
    list_tokens,
    try_create_user,
    try_delete_token,
)
from app.schemas.response import EMPTY_RESPONSE, WCSResponse

from .schema import TokenInfo, TokenInfoResponse, UserInfoResponse

ManageRouter = APIRouter(route_class=DocedAPIRoute, prefix="/manage", tags=["management"])


@ManageRouter.get("/tokens", summary="List API Tokens")
@metadata.permission("admin.tokens.read")
async def get_tokens(inactive: bool = False, session=Depends(get_session)) -> WCSResponse[list[TokenInfoResponse]]:
    """
    List all API tokens with their permissions.
    """
    tokens = await list_tokens(session, include_inactive=inactive)
    return WCSResponse(data=[TokenInfoResponse.model_validate(token) for token in tokens])


@ManageRouter.post("/tokens", summary="Create API Token")
@metadata.permission(permission="admin.tokens.write")
async def create_token(tokens: list[TokenInfo], session=Depends(get_session)) -> WCSResponse[list[TokenInfoResponse]]:
    """
    Create a new API token with specified permissions and expiration.
    """
    created_tokens: list[TokenInfoResponse] = []
    for token_info in tokens:
        user = await try_create_user(
            session,
            token_str=hash_token(token_info.token),
            permissions=token_info.permissions,
            expires_at=token_info.expires_at,
        )
        created_tokens.append(TokenInfoResponse.model_validate(user.token))

    LOGGER.info(f"Created {len(created_tokens)} new API tokens: {[t.token for t in created_tokens]}")
    return WCSResponse(data=created_tokens)


@ManageRouter.delete("/tokens", summary="Delete API Token")
@metadata.permission(permission="admin.tokens.write")
async def delete_token(tokens: list[str], session=Depends(get_session)) -> WCSResponse[dict]:
    """
    Delete an API token by its token string.
    """
    tokens = hash_tokens(tokens)
    await try_delete_token(session, tokens)
    LOGGER.info(f"Deleted {len(tokens)} API tokens: {tokens}")
    return EMPTY_RESPONSE


@ManageRouter.put("/tokens/permissions", summary="Add Permissions to Token")
@metadata.permission(permission="admin.tokens.write")
async def add_permissions_to_token(
    token_str: list[str], permissions: list[str], session=Depends(get_session)
) -> WCSResponse[list[TokenInfoResponse]]:
    """
    Add permissions to existing API tokens.
    """
    token_strs = hash_tokens(token_str)
    tokens = await list_tokens(session, token_strs, include_inactive=True)

    for token in tokens:
        token.permissions = list(set(token.permissions + permissions))

    updated_token_infos = [TokenInfoResponse.model_validate(token) for token in tokens]
    LOGGER.info(f"Added permissions {permissions} to tokens: {token_strs}")
    return WCSResponse(data=updated_token_infos)


@ManageRouter.delete("/tokens/permissions", summary="Remove Permissions from Token")
@metadata.permission(permission="admin.tokens.write")
async def remove_permissions_from_token(
    token_str: list[str], permissions: list[str], session=Depends(get_session)
) -> WCSResponse[list[TokenInfoResponse]]:
    """
    Remove permissions from existing API tokens.
    """
    token_strs = hash_tokens(token_str)
    tokens = await list_tokens(session, token_strs, include_inactive=True)

    for token in tokens:
        token.permissions = list(set(token.permissions) - set(permissions))

    updated_token_infos = [TokenInfoResponse.model_validate(token) for token in tokens]
    LOGGER.info(f"Removed permissions {permissions} from tokens: {token_strs}")
    return WCSResponse(data=updated_token_infos)


@ManageRouter.get("/tokens/self", summary="Get Self Token Info")
async def get_self_token_info(user: User = Depends(get_user)) -> WCSResponse[TokenInfoResponse]:
    """
    Get information about the API token used in the current request.
    """
    return WCSResponse(data=TokenInfoResponse.model_validate(user.token))


@ManageRouter.get("/user/self", summary="Get Self User Info")
async def get_self_user_info(user: User = Depends(get_user)) -> WCSResponse[UserInfoResponse]:
    """
    Get information about the current user, including permissions and common IPs.
    """
    return WCSResponse(data=UserInfoResponse.model_validate(user))


@ManageRouter.get("/user", summary="Get User Info by Token")
@metadata.permission(permission="admin.tokens.read")
async def get_user_info_by_token(
    token: list[str] = Query(), session=Depends(get_session)
) -> WCSResponse[list[UserInfoResponse]]:
    """
    Get information about a user by their API token.
    """
    tokens = hash_tokens(token)

    users = await get_user_by_tokens(session, tokens)
    return WCSResponse(data=[UserInfoResponse.model_validate(user) for user in users])


@ManageRouter.post("/user/register", summary="Register New User")
@metadata.rate_limit(1, 3600)
async def register_user(
    token: str,
    x_real_ip: Annotated[str | None, Header(alias="X-Real-IP", include_in_schema=False)] = None,
    session=Depends(get_session),
) -> WCSResponse[UserInfoResponse]:
    """
    Register a new user with the given token.
    """
    hashed_token = hash_token(token)
    user = await try_create_user(
        session, token_str=hashed_token, permissions=[], expires_at=None, creation_ip=x_real_ip or "unknown"
    )
    LOGGER.info(f"Registered new user with token: {token}")
    return WCSResponse(data=UserInfoResponse.model_validate(user))
