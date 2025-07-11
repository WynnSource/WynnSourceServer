from typing import Optional

from app.core.auth import (
    Token,
    add_permission_for_token,
    add_token,
    get_token,
    get_user,
    list_tokens,
    remove_permission_for_token,
    remove_token,
    require_permission,
)
from app.core.db import get_session
from app.core.metadata import with_metadata
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .domain.response import (
    PermissionListData,
    PermissionListResponse,
    TokenListData,
    TokenListResponse,
)

ManageRouter = APIRouter(prefix="/manage", tags=["management"])


# Permission Management Endpoints
@ManageRouter.get(
    "/perm/{user_token}/list",
    dependencies=[Depends(require_permission)],
    summary="Get Permissions for Token",
    description="Get the permissions associated with a specific user token.",
)
@with_metadata(permission="management.permissions.read.any")
async def get_permissions(
    user_token: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    """
    Get permissions for a given token.
    :param token: The token to check permissions for.
    :return: A list of permissions associated with the token.
    """

    token = await get_token(session, user_token)
    if not token:
        return PermissionListResponse(data=PermissionListData(token=user_token, permissions=[]))
    permissions = token.permissions
    permissions = [perm.permission_id for perm in permissions]
    return PermissionListResponse(data=PermissionListData(token=user_token, permissions=permissions))


@ManageRouter.get(
    "/perm/list",
    summary="Get Self Permissions",
    description="Get the permissions associated with the current user's token.",
)
async def get_self_permissions(
    token: Token | None = Depends(get_user),
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    if not token:
        return PermissionListResponse(data=PermissionListData(token="", permissions=[]))
    permissions = token.permissions
    permissions = [perm.permission_id for perm in permissions]
    return PermissionListResponse(data=PermissionListData(token=token.token, permissions=permissions))


@ManageRouter.put(
    "/perm/{user_token}/add",
    dependencies=[Depends(require_permission)],
    summary="Add Permission to Token",
    description="Add a permission to a specific user token.",
)
@with_metadata(permission="management.permissions.write.any")
async def add_permission(
    user_token: str,
    permission: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    token = await add_permission_for_token(session, user_token, permission)
    return PermissionListResponse(
        data=PermissionListData(token=user_token, permissions=[perm.permission_id for perm in token.permissions])
    )


@ManageRouter.post(
    "/perm/{user_token}/add",
    dependencies=[Depends(require_permission)],
    summary="Add Permission to Token (POST) (Bulk)",
    description="Add permissions to a specific user token using POST method.",
)
@with_metadata(permission="management.permissions.write.any")
async def add_permission_bulk(
    user_token: str,
    permissions: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    token = await add_permission_for_token(session, user_token, permissions)
    return PermissionListResponse(
        data=PermissionListData(token=user_token, permissions=[perm.permission_id for perm in token.permissions])
    )


@ManageRouter.delete(
    "/perm/{user_token}/revoke",
    dependencies=[Depends(require_permission)],
    summary="Revoke Permission from Token",
    description="Revoke a permission from a specific user token.",
)
@with_metadata(permission="management.permissions.write.any")
async def revoke_permission(
    user_token: str,
    permission: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    token = await remove_permission_for_token(session, user_token, permission)
    return PermissionListResponse(
        data=PermissionListData(token=user_token, permissions=[perm.permission_id for perm in token.permissions])
    )


@ManageRouter.post(
    "/perm/{user_token}/revoke",
    dependencies=[Depends(require_permission)],
    summary="Revoke Permission from Token (POST) (Bulk)",
    description="Revoke permissions from a specific user token using POST method.",
)
@with_metadata(permission="management.permissions.write.any")
async def revoke_permission_bulk(
    user_token: str,
    permissions: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    token = await remove_permission_for_token(session, user_token, permissions)
    return PermissionListResponse(
        data=PermissionListData(token=user_token, permissions=[perm.permission_id for perm in token.permissions])
    )


# Token Management Endpoints
@ManageRouter.get(
    "/token/list",
    dependencies=[Depends(require_permission)],
    summary="List All Tokens",
    description="Get a list of all user tokens.",
)
@with_metadata(permission="management.tokens.read.any")
async def list_all_tokens(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    tokens = await list_tokens(session)
    return TokenListResponse(data=TokenListData(tokens=[token.token for token in tokens]))


@ManageRouter.put(
    "/token/{user_token}/create",
    dependencies=[Depends(require_permission)],
    summary="Create Token",
    description="Create a new user token.",
)
@with_metadata(permission="management.tokens.write.any")
async def create_token(
    user_token: str,
    permission: Optional[str] = None,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    if not permission:
        await add_token(session, user_token, [])
    else:
        await add_token(session, user_token, permission)
    return TokenListResponse(data=TokenListData(tokens=[user_token]))


@ManageRouter.post(
    "/token/{user_token}/create",
    dependencies=[Depends(require_permission)],
    summary="Create Token (POST) (Bulk)",
    description="Create new user tokens using POST method.",
)
@with_metadata(permission="management.tokens.write.any")
async def create_token_bulk(
    user_tokens: list[str],
    permissions: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    await add_token(session, user_tokens, permissions)
    return TokenListResponse(data=TokenListData(tokens=user_tokens))


@ManageRouter.delete(
    "/token/{user_token}/remove",
    dependencies=[Depends(require_permission)],
    summary="Remove Token",
    description="Remove a specific user token.",
)
@with_metadata(permission="management.tokens.write.any")
async def delete_token(
    user_token: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    await remove_token(session, user_token)
    return TokenListResponse(data=TokenListData(tokens=[user_token]))


@ManageRouter.post(
    "/token/{user_token}/remove",
    dependencies=[Depends(require_permission)],
    summary="Remove Token (POST) (Bulk)",
    description="Remove specific user tokens using POST method.",
)
@with_metadata(permission="management.tokens.write.any")
async def delete_token_bulk(
    user_tokens: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    await remove_token(session, user_tokens)
    return TokenListResponse(data=TokenListData(tokens=user_tokens))
