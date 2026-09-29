"""Shared application exceptions.

Every AppError is rendered by main.py as
`{"error": {"code": ..., "message": ...}}` with its `status_code`.
"""


class AppError(Exception):
    """Base class for controlled application errors.

    Raised instead of letting raw exceptions (with stack traces) reach API
    consumers.
    """

    code = "app_error"
    status_code = 400

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class AIProviderError(AppError):
    """Raised when an AI provider (and any configured fallback) fails."""

    code = "ai_unavailable"
    status_code = 503


class DatasetNotFound(AppError):
    code = "dataset_not_found"
    status_code = 404


class NotFound(AppError):
    code = "not_found"
    status_code = 404


class RowsLimitExceeded(AppError):
    code = "rows_limit_exceeded"
    status_code = 422
