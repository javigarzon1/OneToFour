"""Tests de las utilidades del límite de uso."""
from backend.app.limits import (
    client_ip,
    env_int,
    rate_key,
    retry_after,
    window_start,
)


def test_client_ip_prefers_vercel_header():
    headers = {
        "x-vercel-forwarded-for": "203.0.113.7",
        "x-forwarded-for": "198.51.100.1, 10.0.0.1",
    }
    assert client_ip(headers) == "203.0.113.7"


def test_client_ip_uses_first_forwarded_address_and_fallback():
    assert client_ip({"x-forwarded-for": "198.51.100.1, 10.0.0.1"}) == "198.51.100.1"
    assert client_ip({}, fallback="127.0.0.1") == "127.0.0.1"
    assert client_ip({}) == "desconocida"


def test_rate_key_is_anonymous_and_stable():
    key = rate_key("203.0.113.7", "generate", salt="sal")
    assert key == rate_key("203.0.113.7", "generate", salt="sal")
    assert key != rate_key("203.0.113.8", "generate", salt="sal")
    assert key != rate_key("203.0.113.7", "generate", salt="otra")
    assert "203.0.113.7" not in key
    assert key.startswith("generate:")


def test_window_start_and_retry_after():
    assert window_start(1_000_000, 600) == 999_600
    assert retry_after(999_600, 600) == 600
    assert retry_after(1_000_199, 600) == 1
    assert retry_after(1_000_200, 600) == 600  # empieza otra ventana


def test_env_int_validates():
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {"X_LIMIT": "7"}):
        assert env_int("X_LIMIT", 5) == 7
    with patch.dict(os.environ, {"X_LIMIT": "abc"}):
        assert env_int("X_LIMIT", 5) == 5
    with patch.dict(os.environ, {"X_LIMIT": "0"}):
        assert env_int("X_LIMIT", 5) == 5
    with patch.dict(os.environ, {}, clear=True):
        assert env_int("X_LIMIT", 5) == 5
