"""Automated secret redaction and log sanitization."""

from __future__ import annotations

import re
from typing import Any

# Patterns matching sensitive keys and values
SENSITIVE_KEY_PATTERNS = [
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"key", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
]

SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
    re.compile(r"(EAA[A-Za-z0-9]{50,})"),  # Meta Access Token
    re.compile(r"(ya29\.[A-Za-z0-9\-_]{50,})"),  # Google OAuth Token
]


def redact_string(text: str) -> str:
    """Redact raw sensitive strings matching token patterns."""
    sanitized = text
    for pattern in SENSITIVE_VALUE_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


def redact_data(data: Any) -> Any:
    """Recursively scrub sensitive keys and tokens from dicts, lists, or primitives."""
    if isinstance(data, dict):
        clean_dict: dict[str, Any] = {}
        for k, v in data.items():
            key_str = str(k)
            is_sensitive_key = any(p.search(key_str) for p in SENSITIVE_KEY_PATTERNS)
            if is_sensitive_key:
                clean_dict[key_str] = "[REDACTED]"
            else:
                clean_dict[key_str] = redact_data(v)
        return clean_dict
    elif isinstance(data, list):
        return [redact_data(item) for item in data]
    elif isinstance(data, str):
        return redact_string(data)
    return data
