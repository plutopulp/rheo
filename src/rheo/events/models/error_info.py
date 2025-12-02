"""Structured error information for failure events."""

import traceback as tb

from pydantic import BaseModel, ConfigDict, Field


class ErrorInfo(BaseModel):
    """Structured error information for failure events."""

    model_config = ConfigDict(frozen=True)

    exc_type: str = Field(
        description="Exception class name, e.g. 'aiohttp.ClientError'"
    )
    message: str = Field(description="Error message")
    traceback: str | None = Field(
        default=None,
        description="Full traceback if available",
    )

    @classmethod
    def from_exception(
        cls, exc: BaseException, include_traceback: bool = False
    ) -> "ErrorInfo":
        """Create ErrorInfo from an exception.

        Args:
            exc: The exception to convert
            include_traceback: Whether to include full traceback (default False)

        Returns:
            Structured ErrorInfo model
        """
        return cls(
            exc_type=f"{type(exc).__module__}.{type(exc).__name__}",
            message=str(exc),
            traceback=tb.format_exc() if include_traceback else None,
        )
