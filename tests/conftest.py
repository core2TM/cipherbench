"""Shared pytest fixtures for the CipherBench test suite.

Fixtures here are available in all test modules without explicit import.
All engine fixtures use scope="function" (default) to ensure each test
gets a fresh, isolated instance (prevents state bleed — PITFALLS.md C-3).
"""
import pytest
from cipherbench.puzzle import create_engine_for_level


@pytest.fixture
def rule_engine_seed_42():
    """Fresh RuleEngine for Level 1 — the canonical test engine.

    Function-scoped (default): each test gets an isolated instance.
    """
    return create_engine_for_level(1)


@pytest.fixture
def rule_engine_seed_0():
    """Fresh RuleEngine for Level 1 — boundary/edge case fixture.

    Function-scoped (default): each test gets an isolated instance.
    """
    return create_engine_for_level(1)


# ---------------------------------------------------------------------------
# Phase 3 fixtures — mock adapter and session directory
# ---------------------------------------------------------------------------


class FixedResponseAdapter:
    """Mock adapter that returns a fixed probe string — used in SESS-04 determinism tests.

    Satisfies the adapter interface without making real API calls.
    """

    def __init__(self, response: str = "PROBE: AAAAA") -> None:
        self.response = response

    def complete(self, messages: list[dict]) -> str:
        """Return the fixed response string regardless of message content."""
        return self.response

    def check_token_budget(self, messages: list[dict]) -> None:
        """No-op — mock does not perform real token counting."""


@pytest.fixture
def mock_adapter() -> FixedResponseAdapter:
    """Mock adapter returning a fixed PROBE: AAAAA response for determinism tests."""
    return FixedResponseAdapter("PROBE: AAAAA")


@pytest.fixture
def tmp_sessions_dir(tmp_path):
    """Temporary sessions directory, unique per test."""
    return tmp_path / "sessions"
