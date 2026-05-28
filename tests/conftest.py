"""Shared pytest fixtures for the CipherBench test suite.

Fixtures here are available in all test modules without explicit import.
All engine fixtures use scope="function" (default) to ensure each test
gets a fresh, isolated instance (prevents state bleed — PITFALLS.md C-3).
"""
import pytest
from cipherbench.types import DifficultyConfig


@pytest.fixture
def default_difficulty() -> DifficultyConfig:
    """Standard A-Z alphabet with output_length=5. Used as the default config."""
    return DifficultyConfig()


@pytest.fixture
def rule_engine_seed_42(default_difficulty: DifficultyConfig):
    """Fresh RuleEngine for seed 42 — the canonical test seed.

    Stub: RuleEngine is not yet implemented. Available after Plan 03.
    Tests using this fixture are skipped until then.
    """
    pytest.skip("RuleEngine not implemented yet — available in Plan 03")


@pytest.fixture
def rule_engine_seed_0(default_difficulty: DifficultyConfig):
    """Fresh RuleEngine for seed 0 — boundary/edge case seed.

    Stub: RuleEngine is not yet implemented. Available after Plan 03.
    Tests using this fixture are skipped until then.
    """
    pytest.skip("RuleEngine not implemented yet — available in Plan 03")
