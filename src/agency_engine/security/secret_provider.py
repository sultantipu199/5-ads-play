"""Secure secret providers for credentials and platform tokens."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from agency_engine.domain.exceptions import CredentialError


class SecretProvider(ABC):
    """Abstract provider for credential retrieval and lifecycle management."""

    @abstractmethod
    def get_secret(self, secret_ref: str) -> str:
        """Retrieve the secret string corresponding to secret_ref."""

    @abstractmethod
    def set_secret(self, secret_ref: str, value: str) -> None:
        """Store or update a secret value."""

    @abstractmethod
    def delete_secret(self, secret_ref: str) -> None:
        """Revoke and delete a secret."""


class EnvSecretProvider(SecretProvider):
    """Retrieves secrets mapped to environment variables."""

    @staticmethod
    def _ref_to_env_var(secret_ref: str) -> str:
        # e.g., "agency/global_brand/meta" -> "AGENCY_GLOBAL_BRAND_META"
        clean = secret_ref.upper().replace("/", "_").replace("-", "_").replace(".", "_")
        return clean

    def get_secret(self, secret_ref: str) -> str:
        var_name = self._ref_to_env_var(secret_ref)
        val = os.getenv(var_name)
        if not val:
            # Fallback to direct ref match or short token name
            short_name = secret_ref.split("/")[-1].upper() + "_ACCESS_TOKEN"
            val = os.getenv(short_name)
        if not val:
            raise CredentialError(f"Secret not found for ref '{secret_ref}' (expected env var '{var_name}')")
        return val

    def set_secret(self, secret_ref: str, value: str) -> None:
        var_name = self._ref_to_env_var(secret_ref)
        os.environ[var_name] = value

    def delete_secret(self, secret_ref: str) -> None:
        var_name = self._ref_to_env_var(secret_ref)
        os.environ.pop(var_name, None)


class MemorySecretProvider(SecretProvider):
    """Hermetic in-memory secret provider for isolated tests and staging."""

    def __init__(self, initial_secrets: dict[str, str] | None = None) -> None:
        self._secrets: dict[str, str] = dict(initial_secrets or {})

    def get_secret(self, secret_ref: str) -> str:
        if secret_ref not in self._secrets:
            raise CredentialError(f"Secret not found in memory provider: {secret_ref}")
        return self._secrets[secret_ref]

    def set_secret(self, secret_ref: str, value: str) -> None:
        self._secrets[secret_ref] = value

    def delete_secret(self, secret_ref: str) -> None:
        self._secrets.pop(secret_ref, None)


def get_secret_provider(provider_type: str = "env") -> SecretProvider:
    if provider_type == "memory":
        return MemorySecretProvider()
    # Default to environment-based secret provider
    return EnvSecretProvider()
