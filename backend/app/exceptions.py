"""Custom exception classes for Lyftr AI Backend."""
from fastapi import HTTPException, status


class AllProvidersUnavailableException(HTTPException):
    def __init__(self, detail: str = "all providers unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


class SessionNotFoundException(HTTPException):
    def __init__(self, detail: str = "session not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )
