"""Hypothesis property-based tests — GEN-04 and phase gate.

Tests invariants that must hold for any seed × guess combination.
Uses Hypothesis to auto-generate adversarial inputs and find edge cases
that hand-written tests miss.

Source references:
  RESEARCH.md §Code Examples — Hypothesis Strategy Sketch
  PATTERNS.md §tests/test_properties.py — Hypothesis strategy sketches
  RULE-04: score_attempt never reveals private state
  GEN-04: same seed → same score for same probe (determinism)
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# RULE-04: AttemptScore never reveals cipher private state
# ---------------------------------------------------------------------------


@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_score_attempt_never_reveals_private_state(seed: int, guess: str) -> None:
    """For any seed and guess, AttemptScore must not expose cipher key, ciphertext, or shifts."""
    engine = create_rule_engine(seed=seed, difficulty=DifficultyConfig())
    result = engine.score_attempt(guess)
    # Score must be a valid integer in 0..5
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 5
    # is_correct must be consistent with score
    assert result.is_correct == (result.score == 5)
    # No cipher state leaked via AttemptScore fields
    assert not hasattr(result, "ciphertext")
    assert not hasattr(result, "key")
    assert not hasattr(result, "shifts")


# ---------------------------------------------------------------------------
# GEN-04 + SESS-04: Same seed + same probe = same score
# ---------------------------------------------------------------------------


@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    probe=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_same_seed_same_probe_same_score(seed: int, probe: str) -> None:
    """Two engines from the same seed must return equal AttemptScore for the same probe at round 1."""
    d = DifficultyConfig()
    engine_1 = create_rule_engine(seed=seed, difficulty=d)
    engine_2 = create_rule_engine(seed=seed, difficulty=d)
    assert engine_1.score_attempt(probe) == engine_2.score_attempt(probe)


# ---------------------------------------------------------------------------
# AttemptScore dataclass invariant
# ---------------------------------------------------------------------------


@given(
    score=st.integers(min_value=0, max_value=5),
    max_score=st.just(5),
)
def test_attempt_score_invariant(score: int, max_score: int) -> None:
    """AttemptScore(score, max_score=5, is_correct=(score==5)) always satisfies invariants."""
    result = AttemptScore(
        score=score, max_score=max_score, is_correct=(score == max_score)
    )
    assert result.is_correct == (result.score == result.max_score)


# ---------------------------------------------------------------------------
# score in valid range for any seed/guess
# ---------------------------------------------------------------------------


@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_score_in_valid_range(seed: int, guess: str) -> None:
    """result.score is always in range 0..max_score for any seed and guess."""
    engine = create_rule_engine(seed=seed, difficulty=DifficultyConfig())
    result = engine.score_attempt(guess)
    assert 0 <= result.score <= result.max_score


# ---------------------------------------------------------------------------
# is_correct iff score == max_score
# ---------------------------------------------------------------------------


@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_is_correct_iff_score_equals_max(seed: int, guess: str) -> None:
    """result.is_correct is exactly (result.score == result.max_score) for any input."""
    engine = create_rule_engine(seed=seed, difficulty=DifficultyConfig())
    result = engine.score_attempt(guess)
    assert result.is_correct == (result.score == result.max_score)
