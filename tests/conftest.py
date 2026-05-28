"""Shared pytest fixtures for the CipherBench test suite.

Fixtures here are available in all test modules without explicit import.
All engine fixtures use scope="function" (default) to ensure each test
gets a fresh, isolated instance (prevents state bleed — PITFALLS.md C-3).
"""
import pytest
from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine


@pytest.fixture
def default_difficulty() -> DifficultyConfig:
    """Standard A-Z alphabet with output_length=5. Used as the default config."""
    return DifficultyConfig()


@pytest.fixture
def rule_engine_seed_42(default_difficulty: DifficultyConfig):
    """Fresh RuleEngine for seed 42 — the canonical test seed.

    Function-scoped (default): each test gets an isolated instance with _round=1.
    """
    return create_rule_engine(seed=42, difficulty=default_difficulty)


@pytest.fixture
def rule_engine_seed_0(default_difficulty: DifficultyConfig):
    """Fresh RuleEngine for seed 0 — boundary/edge case seed.

    Function-scoped (default): each test gets an isolated instance with _round=1.
    """
    return create_rule_engine(seed=0, difficulty=default_difficulty)
