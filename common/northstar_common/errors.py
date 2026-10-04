"""Shared error hierarchy (dependency-free).

Controllers map these to HTTP statuses; services raise them.
"""


class NorthstarError(Exception):
    """Base error with a machine-readable code."""

    code = "NORTHSTAR_ERROR"


class ConfigError(NorthstarError):
    """Invalid or missing configuration."""

    code = "CONFIG_ERROR"


class ServiceError(NorthstarError):
    """Business/service layer failure."""

    code = "SERVICE_ERROR"


class NotFoundError(NorthstarError):
    """Requested entity does not exist."""

    code = "NOT_FOUND"


class ValidationError(NorthstarError):
    """Invalid input that failed domain validation."""

    code = "VALIDATION_ERROR"
