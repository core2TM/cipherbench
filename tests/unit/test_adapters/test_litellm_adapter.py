"""Unit tests for LiteLLMAdapter — ADAPT-01, ADAPT-02, ADAPT-03."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

# Guard: skip entire module if litellm_adapter not yet implemented (Plan 02)
litellm_adapter_mod = pytest.importorskip("cipherbench.adapters.litellm_adapter")
LiteLLMAdapter = litellm_adapter_mod.LiteLLMAdapter

import litellm


# ---------------------------------------------------------------------------
# ADAPT-01: complete() interface
# ---------------------------------------------------------------------------


def test_complete_returns_str():
    """ADAPT-01: complete(messages) must return a str."""
    adapter = LiteLLMAdapter("gpt-3.5-turbo")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "PROBE: AAAAA"
    with patch("litellm.completion", return_value=mock_response):
        result = adapter.complete([{"role": "user", "content": "test"}])
    assert isinstance(result, str)
    assert result == "PROBE: AAAAA"


def test_complete_with_mock_response():
    """ADAPT-01: complete() returns the model's content string from the response."""
    adapter = LiteLLMAdapter("gpt-3.5-turbo")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "PROBE: BBBBB"
    with patch("litellm.completion", return_value=mock_response):
        result = adapter.complete([{"role": "user", "content": "test"}])
    assert isinstance(result, str)
    assert result == "PROBE: BBBBB"


# ---------------------------------------------------------------------------
# ADAPT-02: token budget check
# ---------------------------------------------------------------------------


def test_budget_check_returns_tuple():
    """ADAPT-02: check_token_budget() does not raise when max_tokens is known."""
    adapter = LiteLLMAdapter("gpt-3.5-turbo")
    with patch("litellm.token_counter", return_value=100):
        with patch("litellm.get_max_tokens", return_value=4096):
            # Should not raise — just warns if over threshold
            adapter.check_token_budget([{"role": "user", "content": "test"}])


def test_budget_check_warns_on_unknown_model():
    """ADAPT-02: check_token_budget() handles None max_tokens for unknown models gracefully."""
    adapter = LiteLLMAdapter("custom-unknown-model-xyz")
    with patch("litellm.token_counter", return_value=100):
        with patch("litellm.get_max_tokens", return_value=None):
            # Must NOT raise TypeError — guard handles None gracefully
            adapter.check_token_budget([{"role": "user", "content": "test"}])


# ---------------------------------------------------------------------------
# ADAPT-03: rate-limit retry
# ---------------------------------------------------------------------------


def test_rate_limit_triggers_backoff():
    """ADAPT-03: RateLimitError triggers tenacity exponential backoff retry."""
    adapter = LiteLLMAdapter("gpt-3.5-turbo")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "PROBE: AAAAA"

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise litellm.RateLimitError(
                message="rate limited",
                llm_provider="openai",
                model="gpt-3.5-turbo",
            )
        return mock_response

    with patch("litellm.completion", side_effect=side_effect):
        result = adapter.complete([{"role": "user", "content": "test"}])

    assert result == "PROBE: AAAAA"
    assert call_count == 3


def test_rate_limit_exhaustion_reraises():
    """ADAPT-03: After N retries exhausted, RateLimitError is re-raised to caller."""
    adapter = LiteLLMAdapter("gpt-3.5-turbo")

    def always_rate_limit(*args, **kwargs):
        raise litellm.RateLimitError(
            message="rate limited",
            llm_provider="openai",
            model="gpt-3.5-turbo",
        )

    with patch("litellm.completion", side_effect=always_rate_limit):
        with pytest.raises(litellm.RateLimitError):
            adapter.complete([{"role": "user", "content": "test"}])
