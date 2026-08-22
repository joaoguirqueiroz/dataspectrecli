"""Domain exceptions used across the DataSpectre application."""

from __future__ import annotations


class DataSpectreError(Exception):
    """Base exception for all expected application errors."""


# Backward compatibility for extensions written for the previous project name.
SentinelScanError = DataSpectreError


class BootstrapError(DataSpectreError):
    """Raised when the application cannot initialize safely."""


class ConfigurationError(DataSpectreError):
    """Raised for invalid or unavailable configuration values."""


class ValidationError(DataSpectreError):
    """Raised when user or component input is invalid."""


class PermissionDeniedError(DataSpectreError):
    """Raised when the active profile cannot perform an operation."""


class ModuleError(DataSpectreError):
    """Raised for module discovery, validation, or execution failures."""


class PluginError(DataSpectreError):
    """Raised for plugin discovery, validation, or lifecycle failures."""


class ProjectError(DataSpectreError):
    """Raised for project catalog and project workspace failures."""


class SessionError(DataSpectreError):
    """Raised for session lifecycle failures."""


class ReportError(DataSpectreError):
    """Raised for report generation and catalog failures."""
