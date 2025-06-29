from app.domain.response.v1.management import (
    PermissionListData,
    PermissionListResponse,
    TokenListData,
    TokenListResponse,
)
from app.models.manage import (
    Permission,
    Token,
    add_permission_for_token,
    add_token,
    get_token,
    list_tokens,
    remove_permission_for_token,
    remove_token,
)
from app.service.db import get_session
from app.utils.auth_utils import get_user, require_permission
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ManageRouter = APIRouter(prefix="/manage", tags=["management"])


# Permission Management Endpoints
@ManageRouter.get(
    "/perm/{user_token}/list",
    dependencies=[Depends(require_permission("management.permissions.read.any"))],
    summary="Get Permissions for Token",
    description="Get the permissions associated with a specific user token.",
)
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
    dependencies=[Depends(require_permission("management.permissions.write.any"))],
    summary="Add Permission to Token",
    description="Add a permission to a specific user token.",
)
async def add_permission(
    user_token: str,
    permission: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    permission_obj = Permission(permission_id=permission)
    await add_permission_for_token(session, user_token, permission_obj)
    return PermissionListResponse(data=PermissionListData(token=user_token, permissions=[permission]))


@ManageRouter.post(
    "/perm/{user_token}/add",
    dependencies=[Depends(require_permission("management.permissions.write.any"))],
    summary="Add Permission to Token (POST) (Bulk)",
    description="Add permissions to a specific user token using POST method.",
)
async def add_permission_bulk(
    user_token: str,
    permissions: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    permission_objs = [Permission(permission_id=perm) for perm in permissions]
    await add_permission_for_token(session, user_token, permission_objs)
    return PermissionListResponse(data=PermissionListData(token=user_token, permissions=permissions))


@ManageRouter.delete(
    "/perm/{user_token}/revoke",
    dependencies=[Depends(require_permission("management.permissions.write.any"))],
    summary="Revoke Permission from Token",
    description="Revoke a permission from a specific user token.",
)
async def revoke_permission(
    user_token: str,
    permission: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    permission_obj = Permission(permission_id=permission)
    await remove_permission_for_token(session, user_token, permission_obj)
    return PermissionListResponse(data=PermissionListData(token=user_token, permissions=[]))


@ManageRouter.post(
    "/perm/{user_token}/revoke",
    dependencies=[Depends(require_permission("management.permissions.write.any"))],
    summary="Revoke Permission from Token (POST) (Bulk)",
    description="Revoke permissions from a specific user token using POST method.",
)
async def revoke_permission_bulk(
    user_token: str,
    permissions: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> PermissionListResponse:
    permission_objs = [Permission(permission_id=perm) for perm in permissions]
    await remove_permission_for_token(session, user_token, permission_objs)
    return PermissionListResponse(data=PermissionListData(token=user_token, permissions=[]))


# Token Management Endpoints
@ManageRouter.get(
    "/token/list",
    dependencies=[Depends(require_permission("management.tokens.read.any"))],
    summary="List All Tokens",
    description="Get a list of all user tokens.",
)
async def list_all_tokens(
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    tokens = await list_tokens(session)
    return TokenListResponse(data=TokenListData(tokens=[token.token for token in tokens]))


@ManageRouter.put(
    "/token/{user_token}/create",
    dependencies=[Depends(require_permission("management.tokens.write.any"))],
    summary="Create Token",
    description="Create a new user token.",
)
async def create_token(
    user_token: str,
    permission: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    token = Token(token=user_token, permissions=[Permission(permission_id=permission)])
    await add_token(session, token)
    return TokenListResponse(data=TokenListData(tokens=[token.token]))


@ManageRouter.post(
    "/token/{user_token}/create",
    dependencies=[Depends(require_permission("management.tokens.write.any"))],
    summary="Create Token (POST) (Bulk)",
    description="Create new user tokens using POST method.",
)
async def create_token_bulk(
    user_tokens: list[str],
    permissions: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    tokens = [
        Token(token=token, permissions=[Permission(permission_id=perm) for perm in permissions])
        for token in user_tokens
    ]
    await add_token(session, tokens)
    return TokenListResponse(data=TokenListData(tokens=[token.token for token in tokens]))


@ManageRouter.delete(
    "/token/{user_token}/remove",
    dependencies=[Depends(require_permission("management.tokens.write.any"))],
    summary="Remove Token",
    description="Remove a specific user token.",
)
async def delete_token(
    user_token: str,
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    await remove_token(session, user_token)
    return TokenListResponse(data=TokenListData(tokens=[]))


@ManageRouter.post(
    "/token/{user_token}/remove",
    dependencies=[Depends(require_permission("management.tokens.write.any"))],
    summary="Remove Token (POST) (Bulk)",
    description="Remove specific user tokens using POST method.",
)
async def delete_token_bulk(
    user_tokens: list[str],
    session: async_sessionmaker[AsyncSession] = Depends(get_session),
) -> TokenListResponse:
    await remove_token(session, user_tokens)
    return TokenListResponse(data=TokenListData(tokens=[]))
