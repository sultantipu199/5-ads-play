import pytest

from agency_engine.domain.exceptions import CredentialError
from agency_engine.security.redaction import redact_data, redact_string
from agency_engine.security.secret_provider import MemorySecretProvider


def test_redact_string_bearer_token() -> None:
    raw_log = "Sending request with Bearer secret_token_abc_12345 to endpoint"
    cleaned = redact_string(raw_log)
    assert "[REDACTED_SECRET]" in cleaned
    assert "secret_token_abc_12345" not in cleaned


def test_redact_data_nested_dict() -> None:
    payload = {
        "client_name": "Global Brand",
        "api_key": "super_secret_key_123",
        "nested": {
            "oauth_token": "EAAabcdefgh1234567890123456789012345678901234567890",
            "normal_field": "visible_data",
        },
        "items": [
            {"password": "mypassword"},
            {"campaign": "summer_promo"},
        ],
    }

    cleaned = redact_data(payload)
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["oauth_token"] == "[REDACTED]"
    assert cleaned["nested"]["normal_field"] == "visible_data"
    assert cleaned["items"][0]["password"] == "[REDACTED]"
    assert cleaned["items"][1]["campaign"] == "summer_promo"


def test_memory_secret_provider() -> None:
    provider = MemorySecretProvider({"agency/client/meta": "test_meta_tok"})
    assert provider.get_secret("agency/client/meta") == "test_meta_tok"

    provider.set_secret("agency/client/google", "test_google_tok")
    assert provider.get_secret("agency/client/google") == "test_google_tok"

    provider.delete_secret("agency/client/meta")
    with pytest.raises(CredentialError):
        provider.get_secret("agency/client/meta")
