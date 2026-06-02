"""Hypothesis property-based tests — GEN-04 and phase gate.

Tests invariants that must hold for any guess combination.
Uses Hypothesis to auto-generate adversarial inputs and find edge cases
that hand-written tests miss.

Source references:
  RESEARCH.md §Code Examples — Hypothesis Strategy Sketch
  PATTERNS.md §tests/test_properties.py — Hypothesis strategy sketches
  RULE-04: score_attempt never reveals private state
  GEN-04: same level → same score for same probe (determinism)
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from cipherbench.types import AttemptScore
from cipherbench.puzzle import create_engine_for_level

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# RULE-04: AttemptScore never reveals cipher private state
# ---------------------------------------------------------------------------


@given(
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_score_attempt_never_reveals_private_state(guess: str) -> None:
    """For any guess, AttemptScore must not expose cipher key, ciphertext, or shifts."""
    engine = create_engine_for_level(1)
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
# GEN-04 + SESS-04: Same level + same probe = same score
# ---------------------------------------------------------------------------


@given(
    probe=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_same_seed_same_probe_same_score(probe: str) -> None:
    """Two engines from the same level must return equal AttemptScore for the same probe."""
    engine_1 = create_engine_for_level(1)
    engine_2 = create_engine_for_level(1)
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
        score=score, max_score=max_score, is_correct=(score == max_score),
    )
    assert result.is_correct == (result.score == result.max_score)


# ---------------------------------------------------------------------------
# score in valid range for any guess
# ---------------------------------------------------------------------------


@given(
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_score_in_valid_range(guess: str) -> None:
    """result.score is always in range 0..max_score for any guess."""
    engine = create_engine_for_level(1)
    result = engine.score_attempt(guess)
    assert 0 <= result.score <= result.max_score


# ---------------------------------------------------------------------------
# is_correct iff score == max_score
# ---------------------------------------------------------------------------


@given(
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
@settings(max_examples=100)
def test_is_correct_iff_score_equals_max(guess: str) -> None:
    """result.is_correct is exactly (result.score == result.max_score) for any input."""
    engine = create_engine_for_level(1)
    result = engine.score_attempt(guess)
    assert result.is_correct == (result.score == result.max_score)
