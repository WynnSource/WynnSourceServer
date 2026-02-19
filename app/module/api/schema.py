from pydantic import BaseModel
from pydantic_core import ErrorDetails

from app.schemas.enums import ErrorCodes
from app.schemas.response.response import WCSResponse


class GenericExceptionResponse(WCSResponse[dict]):
    """
    Generic exception response model.
    """


class HTTPErrorDefinition(BaseModel):
    status_code: int
    error: str


class HTTPErrorResponse(WCSResponse[dict]):
    """
    HTTP error response model.
    """

    data: HTTPErrorDefinition
    code: ErrorCodes = ErrorCodes.HTTP_ERROR


class ValidationErrorResponse(WCSResponse[list]):
    """
    Validation error response model.
    """

    data: list[ErrorDetails]
    code: ErrorCodes = ErrorCodes.VALIDATION_ERROR


__all__ = ["GenericExceptionResponse", "HTTPErrorResponse", "ValidationErrorResponse"]
