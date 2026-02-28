from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT, HTTP_500_INTERNAL_SERVER_ERROR

from app.core.log import LOGGER
from app.schemas.enums import ErrorCodes

from .schema import GenericExceptionResponse, HTTPErrorDefinition, HTTPErrorResponse, ValidationErrorResponse


def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Generic exception handler API.
    """
    LOGGER.exception(exc)
    return GenericExceptionResponse(data={"error": "INTERNAL_ERROR"}, code=ErrorCodes.UNKNOWN_ERROR).to_response(
        HTTP_500_INTERNAL_SERVER_ERROR
    )


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global exception handler API.
    """
    LOGGER.error(f"HTTP {exc.status_code}: {exc.detail}")
    return HTTPErrorResponse(
        data=HTTPErrorDefinition(status_code=exc.status_code, error=exc.detail), code=ErrorCodes.HTTP_ERROR
    ).to_response(exc.status_code, exc.headers)


def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Validation exception handler API.
    """
    LOGGER.error(exc)
    return ValidationErrorResponse(
        data=jsonable_encoder(exc.errors()),
    ).to_response(HTTP_422_UNPROCESSABLE_CONTENT)
