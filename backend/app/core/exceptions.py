"""Application error hierarchy.

Every error the API returns to a client passes through one of these. The
handlers in app.main translate them into the standard error envelope, so a
client only ever has to understand one response shape.

Rule: internal detail (stack traces, driver messages, SQL) goes to the log,
never to the client. Each response carries a request_id so a support
conversation can find the matching log line.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for every expected, client-facing failure."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred. Please try again."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or []
        super().__init__(self.message)


class InvalidInputError(AppError):
    status_code = 422
    code = "INVALID_INPUT"
    message = "The submitted values are not valid."


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication is required."


class InvalidCredentialsError(UnauthorizedError):
    # Deliberately does not say whether the email or the password was wrong:
    # distinguishing them turns the login form into an account enumerator.
    message = "Incorrect email or password."


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "That resource already exists."


class ModelUnavailableError(AppError):
    status_code = 503
    code = "MODEL_UNAVAILABLE"
    message = (
        "The crop recommendation model is not available right now. "
        "Other features still work. Please try again shortly."
    )


class PredictionFailedError(AppError):
    status_code = 500
    code = "PREDICTION_FAILED"
    message = "The recommendation could not be generated. Please try again."


class DatabaseUnavailableError(AppError):
    status_code = 503
    code = "DATABASE_UNAVAILABLE"
    message = "The service is temporarily unavailable. Please try again shortly."
