from collections.abc import Mapping
from datetime import UTC, datetime

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.status import HTTP_200_OK

from app.schemas.constants import __REVISION__, __VERSION__
from app.schemas.enums import ErrorCodes


class WCSResponse[T: (BaseModel, dict, list)](BaseModel):
    """
    Base class for all v1 response models.
    """

    data: T
    code: ErrorCodes = Field(default=ErrorCodes.OK)
    timestamp: int = Field(default_factory=lambda: int(datetime.now(UTC).timestamp()), frozen=True)
    version: int = Field(default=__REVISION__, frozen=True)

    def to_response(self, response_code: int = HTTP_200_OK, headers: Mapping[str, str] | None = None) -> JSONResponse:
        return JSONResponse(
            status_code=response_code,
            content=self.model_dump(mode="json"),
            headers=headers,
        )

    @classmethod
    def from_message(cls, message: str) -> "WCSResponse[dict]":
        """
        Create a response with a message.
        """
        return WCSResponse[dict](
            data={"message": message},
            code=ErrorCodes.OK,
            timestamp=int(datetime.now(UTC).timestamp()),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "WCSResponse[dict]":
        """
        Create a response from a dictionary.
        """
        return WCSResponse[dict](
            data=data,
            code=ErrorCodes.OK,
            timestamp=int(datetime.now(UTC).timestamp()),
        )


class StatusData(BaseModel):
    """
    Status data model for v1 responses.
    """

    status: str = Field(default="OK", frozen=True)
    version: str = Field(default=__VERSION__, frozen=True)


class StatusResponse(WCSResponse[StatusData]):
    """
    Status response model for v1.
    """

    data: StatusData = Field(default=StatusData(), frozen=True)
