"""Shared application exceptions."""


class AppError(Exception):
    """Base class for controlled application errors.

    Raised instead of letting raw exceptions (with stack traces) reach API
    consumers.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AIProviderError(AppError):
    """Raised when an AI provider (and any configured fallback) fails."""
