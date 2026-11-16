"""Exception hierarchy for STANG."""

from __future__ import annotations


class STANGError(Exception):
    """Base class for all STANG errors."""


class ContainerError(STANGError, ValueError):
    """Raised when container parsing, validation, or serialization fails."""


class ChecksumError(ContainerError):
    """Raised when the trailing digest does not match the payload."""


class AuthenticationError(ContainerError):
    """Raised when an encrypted container cannot be authenticated.

    In practice this means the wrong passphrase was supplied or the file was
    tampered with after creation.
    """


class IntegrityError(ContainerError):
    """Raised when a keyed (HMAC) integrity check fails."""


class EncryptionError(ContainerError):
    """Raised when encryption parameters are missing or invalid."""
