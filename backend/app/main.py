"""FastAPI application factory.

Startup loads the ML artifacts once. A failure there is logged and the app
still starts: /health reports the model unavailable and /predict returns 503,
while authentication, profile and history keep working. Refusing to boot
because one model file is missing would turn a single broken feature into a
full outage.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError, DatabaseUnavailableError
from app.core.logging import configure_logging, request_id_ctx
from app.ml.crop_recommendation.inference.predictor import init_predictor

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.ENVIRONMENT)

    predictor = init_predictor(settings.MODEL_ARTIFACTS_DIR)
    if not predictor.is_loaded:
        logger.warning(
            "Crop recommendation model not loaded - /predict will return 503. "
            "Train it with: python -m app.ml.crop_recommendation.training.train"
        )

    yield
    logger.info("Shutting down")


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": request_id_ctx.get(),
            },
        },
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "AgriGuru AI - Phase 1. Crop recommendation from soil and weather "
            "values, with prediction history.\n\n"
            "**Note on model output:** confidence values come from the trained "
            "model's own probability estimates on a clean, class-balanced, "
            "largely synthetic benchmark dataset. They are not a forecast of "
            "field success. See `/api/v1/crop-recommendation/model-info`."
        ),
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,   # never "*": credentials are sent
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)

    # --- Exception handlers: every error leaves through the same envelope ---

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("Application error: %s", exc.code)
        else:
            logger.info("Handled error %s: %s", exc.code, exc.message)
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Translate Pydantic's structure into our field/message detail list so
        # the frontend can attach each message to the right input.
        details = []
        for err in exc.errors():
            location = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            details.append(
                {
                    "field": ".".join(location) or None,
                    "message": err["msg"].removeprefix("Value error, "),
                }
            )
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_INPUT",
            "Some of the values you entered are not valid. Please check and try again.",
            details,
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        # Driver messages can carry table names, SQL and occasionally values.
        # They go to the log; the client gets a generic message and an id.
        logger.exception("Database error")
        err = DatabaseUnavailableError()
        return _error_response(err.status_code, err.code, err.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 401: "UNAUTHORIZED"}
        return _error_response(
            exc.status_code,
            codes.get(exc.status_code, "HTTP_ERROR"),
            str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Last resort. A stack trace must never reach a farmer's phone.
        logger.exception("Unhandled exception")
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Something went wrong on our side. Please try again.",
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, Any]:
        return {
            "success": True,
            "data": {
                "name": settings.APP_NAME,
                "phase": 1,
                "docs": f"{settings.API_V1_PREFIX}/docs",
            },
        }

    return app


app = create_app()
