from app.domain.response import Data, Response


class PermissionListData(Data):
    """
    Data model for a list of permissions.
    """

    token: str
    permissions: list[str]


class PermissionListResponse(Response[PermissionListData]):
    """
    Response model for a list of permissions.
    """

    data: PermissionListData


class TokenListData(Data):
    """
    Data model for a list of tokens.
    """

    tokens: list[str]


class TokenListResponse(Response[TokenListData]):
    """
    Response model for a list of tokens.
    """

    data: TokenListData


__all__ = [
    "PermissionListData",
    "PermissionListResponse",
    "TokenListData",
]
