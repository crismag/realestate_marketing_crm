"""Domain errors raised by service functions and translated by views."""
from __future__ import annotations


class DomainError(Exception):
    """A business rule refused the operation. ``code`` is stable for tests/UI."""

    code = "domain_error"
    status = 400

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class ConflictError(DomainError):
    """Another change won (stale version, already claimed, stale handover)."""

    code = "conflict"
    status = 409


class NotAllowed(DomainError):
    """The acting user is not the party who may perform this specific transition."""

    code = "not_allowed"
    status = 403


class InvalidTransition(DomainError):
    code = "invalid_transition"
    status = 409


class ServiceUnavailable(DomainError):
    """Persistence is temporarily unavailable (e.g. SQLite lock not obtained)."""

    code = "unavailable"
    status = 503
