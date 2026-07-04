import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppError
from app.shared.responses import error_response

logger = logging.getLogger(__name__)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    logger.warning("application_error", extra={"error_code": exc.code})
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code=exc.code, message=exc.message),
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.warning(
        "request_validation_error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "error_count": len(exc.errors()),
        },
    )
    return JSONResponse(
        status_code=422,
        content=error_response(
            code="validation_error",
            message="Request validation failed.",
        ),
    )


async def database_error_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    logger.exception(
        "database_error",
        extra={"method": request.method, "path": request.url.path},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=503,
        content=error_response(
            code="database_error",
            message="A database error occurred.",
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={"method": request.method, "path": request.url.path},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content=error_response(
            code="internal_server_error",
            message="An unexpected error occurred.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
