from app.domain.response.v1.error import ErrorCodes
from app.domain.response.v1.response import V1Response
from app.log import logger
from app.router.manage import ManageRouter
from app.router.pool import PoolRouter
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

# API Router for version 1

V1Router = APIRouter(prefix="/api/v1")
V1Router.include_router(ManageRouter)
V1Router.include_router(PoolRouter)


def v1_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global exception handler for v1 API.
    This function can be extended to handle specific exceptions and return appropriate responses.
    """
    logger.exception(exc)
    return V1Response(data=jsonable_encoder(obj=exc), code=ErrorCodes.UNKNOWN_ERROR).to_response(exc.status_code)


def v1_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Validation exception handler for v1 API.
    This function can be extended to handle validation errors and return appropriate responses.
    """
    logger.exception(exc)
    return V1Response(
        data=jsonable_encoder(exc.errors()),
        code=ErrorCodes.VALIDATION_ERROR,
    ).to_response(HTTP_422_UNPROCESSABLE_ENTITY)


__all__ = [
    "V1Router",
    "v1_exception_handler",
    "v1_validation_exception_handler",
]
