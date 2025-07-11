from app.domain.enums import ErrorCodes
from app.domain.response import Response
from app.log import LOGGER
from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


def v1_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global exception handler for v1 API.
    This function can be extended to handle specific exceptions and return appropriate responses.
    """
    return Response[dict](data=jsonable_encoder(obj=exc), code=ErrorCodes.UNKNOWN_ERROR).to_response(exc.status_code)


def v1_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Validation exception handler for v1 API.
    This function can be extended to handle validation errors and return appropriate responses.
    """
    LOGGER.exception(exc)
    return Response[list](
        data=jsonable_encoder(exc.errors()),
        code=ErrorCodes.VALIDATION_ERROR,
    ).to_response(HTTP_422_UNPROCESSABLE_ENTITY)
