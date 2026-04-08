from fastapi import APIRouter, Query

import app.core.metadata as metadata
from app.core.db import SessionDep
from app.core.log import LOGGER
from app.core.router import DocedAPIRoute
from app.core.security.auth import IpDep, UserDep, hash_token, hash_tokens
from app.core.security.model import User, UserRepository
from app.schemas.enums import ApiTag
from app.schemas.response import EMPTY_RESPONSE, WCSResponse

from .schema import UserInfoRequest, UserInfoResponse

ManageRouter = APIRouter(route_class=DocedAPIRoute, prefix="/manage", tags=[ApiTag.MANAGEMENT])


@ManageRouter.get("/user", summary="Get User Info by Token")
@metadata.permission(permission="admin.users.read")
async def get_user_info_by_token(
    session: SessionDep,
    token: list[str] = Query(),
) -> WCSResponse[list[UserInfoResponse]]:
    """
    Get information about a user by their token.
    """
    userRepo = UserRepository(session)
    tokens = hash_tokens(token)

    users = await userRepo.get_users_by_tokens(tokens)
    return WCSResponse(data=[UserInfoResponse.model_validate(user) for user in users])


@ManageRouter.get("/user/all", summary="List Users")
@metadata.permission("admin.users.read")
async def get_users(
    session: SessionDep,
    inactive: bool = False,
) -> WCSResponse[list[UserInfoResponse]]:
    """
    List all users with their permissions.
    """
    userRepo = UserRepository(session)
    users = await userRepo.list_users(include_inactive=inactive)
    return WCSResponse(data=[UserInfoResponse.model_validate(user) for user in users])


@ManageRouter.get("/user/self", summary="Get Self User Info")
async def get_self_user_info(user: UserDep) -> WCSResponse[UserInfoResponse]:
    """
    Get information about the current user, including permissions and common IPs.
    """
    return WCSResponse(data=UserInfoResponse.model_validate(user))


@ManageRouter.post("/user/register", summary="Register New User")
@metadata.rate_limit(1, 3600)
async def register_user(
    token: str,
    session: SessionDep,
    ip: IpDep = "unknown",
) -> WCSResponse[UserInfoResponse]:
    """
    Register a new user with the given token.
    """
    userRepo = UserRepository(session)
    user = User(
        token=hash_token(token),
        is_active=True,
        permissions=[],
        creation_ip=ip,
    )
    await userRepo.save(user)
    LOGGER.info(f"Registered new user with token: {token}")
    return WCSResponse(data=UserInfoResponse.model_validate(user))


@ManageRouter.post("/user/create", summary="Create New Users")
@metadata.permission(permission="admin.users.write")
async def create_user(
    tokens: list[UserInfoRequest], session: SessionDep, ip: IpDep = "unknown"
) -> WCSResponse[list[UserInfoResponse]]:
    """
    Create a new user with specified token and permissions.
    """
    userRepo = UserRepository(session)
    created_tokens: list[UserInfoResponse] = []
    for token_info in tokens:
        user = User(
            token=hash_token(token_info.token),
            is_active=True,
            permissions=token_info.permissions,
            expires_at=token_info.expires_at,
            creation_ip=ip,
        )
        await userRepo.save(user)
        created_tokens.append(UserInfoResponse.model_validate(user))

    LOGGER.info(f"Created {len(created_tokens)} new users: {[hash_token(u.token) for u in created_tokens]}")
    return WCSResponse(data=created_tokens)


@ManageRouter.delete("/user", summary="Delete User")
@metadata.permission(permission="admin.users.write")
async def delete_user(tokens: list[str], session: SessionDep) -> WCSResponse[dict]:
    """
    Delete a user by their token string.
    """
    tokens = hash_tokens(tokens)
    userRepo = UserRepository(session)
    await userRepo.delete(tokens)
    LOGGER.info(f"Deleted {len(tokens)} users: {tokens}")
    return EMPTY_RESPONSE


@ManageRouter.put("/user/permissions", summary="Add Permissions to User")
@metadata.permission(permission="admin.users.write")
async def add_permissions_to_user(
    token_str: list[str], permissions: list[str], session: SessionDep
) -> WCSResponse[list[UserInfoResponse]]:
    """
    Add permissions to existing users.
    """
    userRepo = UserRepository(session)
    token_strs = hash_tokens(token_str)
    users = await userRepo.get_users_by_tokens(token_strs, include_inactive=True)

    for user in users:
        user.permissions = list(set(user.permissions + permissions))

    updated_user_infos = [UserInfoResponse.model_validate(user) for user in users]
    LOGGER.info(f"Added permissions {permissions} to users: {token_strs}")
    return WCSResponse(data=updated_user_infos)


@ManageRouter.delete("/user/permissions", summary="Remove Permissions from User")
@metadata.permission(permission="admin.users.write")
async def remove_permissions_from_user(
    token_str: list[str], permissions: list[str], session: SessionDep
) -> WCSResponse[list[UserInfoResponse]]:
    """
    Remove permissions from existing users.
    """
    token_strs = hash_tokens(token_str)
    userRepo = UserRepository(session)
    users = await userRepo.get_users_by_tokens(token_strs, include_inactive=True)

    for user in users:
        user.permissions = list(set(user.permissions) - set(permissions))

    updated_user_infos = [UserInfoResponse.model_validate(user) for user in users]
    LOGGER.info(f"Removed permissions {permissions} from users: {token_strs}")
    return WCSResponse(data=updated_user_infos)
