from app.domain.response.v1.data import Data
from app.domain.response.v1.response import V1Response


class PermissionListData(Data):
    """
    Data model for a list of permissions.
    """

    token: str
    permissions: list[str]


class PermissionListResponse(V1Response[PermissionListData]):
    """
    Response model for a list of permissions.
    """

    data: PermissionListData


class TokenListData(Data):
    """
    Data model for a list of tokens.
    """

    tokens: list[str]


class TokenListResponse(V1Response[TokenListData]):
    """
    Response model for a list of tokens.
    """

    data: TokenListData


__all__ = [
    "PermissionListData",
    "PermissionListResponse",
    "TokenListData",
]
