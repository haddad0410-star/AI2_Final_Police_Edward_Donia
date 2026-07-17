"""Shared exception types for configuration and protocol validation.

These are plain, dependency-free exceptions so that both peers can raise and
catch precise error conditions without importing a validation framework.
"""

from __future__ import annotations


class ConfigError(Exception):
    """Raised when a configuration file is missing, malformed, or invalid."""


class PrivateOverrideError(ConfigError):
    """Raised when a private game.toml attempts to override a binding shared field."""


class SchemaValidationError(Exception):
    """Raised when a protocol message fails schema validation."""
