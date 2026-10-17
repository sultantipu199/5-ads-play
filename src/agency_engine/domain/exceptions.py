"""Domain exceptions for agency engine error taxonomy."""

from __future__ import annotations


class AgencyEngineError(Exception):
    """Base error for all engine failures."""


class CredentialError(AgencyEngineError):
    """Raised when authentication, token validation, or rotation fails."""


class StaleDataError(AgencyEngineError):
    """Raised when observed data freshness exceeds configured threshold."""


class PolicyViolationError(AgencyEngineError):
    """Raised when an operation breaches safety policies or limits."""


class CircuitBreakerError(AgencyEngineError):
    """Raised when a circuit breaker blocks operations to protect campaigns."""


class IdempotencyConflictError(AgencyEngineError):
    """Raised when a duplicated action is detected or fingerprint already exists."""


class PlatformApiError(AgencyEngineError):
    """Raised on platform HTTP failures with status and retry indicators."""

    def __init__(
        self,
        platform: str,
        status_code: int | None = None,
        message: str = "",
        is_transient: bool = False,
        retry_after: float | None = None,
    ):
        super().__init__(f"[{platform}] Status {status_code}: {message}")
        self.platform = platform
        self.status_code = status_code
        self.is_transient = is_transient
        self.retry_after = retry_after


class StateConflictError(AgencyEngineError):
    """Raised when pre-execution re-reading detects upstream resource state changed."""
