from datetime import datetime, timezone

from app.domain.constants import __VERSION__
from app.domain.enums import ErrorCodes
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.status import HTTP_200_OK

from .data import Data


class V1Response[T: (BaseModel, dict)](BaseModel):
    """
    Base class for all v1 response models.
    """

    data: T
    code: ErrorCodes = Field(default=ErrorCodes.OK)
    timestamp: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()), frozen=True)
    version: int = Field(default=1, frozen=True)

    def to_response(self, response_code: int = HTTP_200_OK):
        return JSONResponse(
            status_code=response_code,
            content=self.model_dump(mode="json"),
        )

    @classmethod
    def from_message(cls, message: str) -> "V1Response[dict]":
        """
        Create a response with a message.
        """
        return V1Response[dict](
            data={"message": message},
            code=ErrorCodes.OK,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "V1Response[dict]":
        """
        Create a response from a dictionary.
        """
        return V1Response[dict](
            data=data,
            code=ErrorCodes.OK,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )


class StatusData(Data):
    """
    Status data model for v1 responses.
    """

    # TODO DB connection status
    status: str = Field(default="OK", frozen=True)
    version: str = Field(default=__VERSION__, frozen=True)


class StatusResponse(V1Response[StatusData]):
    """
    Status response model for v1.
    """

    data: StatusData = Field(default=StatusData(), frozen=True)
