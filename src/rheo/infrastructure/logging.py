"""
Simple logging configuration using Loguru.

This module provides a pre-configured logger with rich formatting
and contextual information including module name, function, and line number.
"""

import sys
import typing as t

from loguru import logger

from ..config.settings import Environment, LogLevel, Settings

if t.TYPE_CHECKING:
    import loguru
# Remove default logger
logger.remove()

# Define log format with extensive information and nice formatting
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# Global configuration state
_configured = False


def configure_logger(
    level: LogLevel = LogLevel.INFO, environment: Environment = Environment.DEVELOPMENT
) -> None:
    """Configure the logger with the given level and environment."""
    global _configured

    logger.remove()

    # Use coloured format for development, plain for production
    format_string = (
        LOG_FORMAT
        if environment == Environment.DEVELOPMENT
        else (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    )

    logger.configure(
        handlers=[
            {
                "sink": sys.stderr,
                "format": format_string,
                "colorize": environment == Environment.DEVELOPMENT,
                "level": level.value,
                "diagnose": environment == Environment.DEVELOPMENT,
            }
        ],
    )

    _configured = True


def setup_logging(settings: Settings | None = None) -> None:
    """Set up logging with provided settings or defaults."""
    settings = settings or Settings()
    configure_logger(settings.log_level, settings.environment)


def get_logger(name: str) -> "loguru.Logger":
    """Get a logger with the given name.

    Auto-configures with defaults if not already configured.
    """
    if not _configured:
        # Auto-configure with library-friendly defaults
        configure_logger()

    return logger.bind(name=name)


def is_configured() -> bool:
    """Check if logging has been configured."""
    return _configured


def reset_logging() -> None:
    """Reset logging configuration. Useful for testing."""
    global _configured
    logger.remove()
    _configured = False
