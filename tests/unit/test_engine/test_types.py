"""Tests for AttemptScore and DifficultyConfig frozen dataclasses.

TDD RED: These tests are written before cipherbench/types.py exists.
They verify the invariants defined in the data contracts specification
(D-01, D-02, D-03, D-05, D-06, D-09).
"""
import pytest
from cipherbench.types import AttemptScore, DifficultyConfig


# --- AttemptScore tests ---

def test_attempt_score_valid():
    """A score below max_score with is_correct=False constructs successfully."""
    s = AttemptScore(score=3, max_score=5, is_correct=False)
    assert s.score == 3


def test_attempt_score_correct_flag_consistency():
    """score==max_score with is_correct=False must raise ValueError (D-03)."""
    with pytest.raises(ValueError):
        AttemptScore(score=5, max_score=5, is_correct=False)


def test_attempt_score_out_of_range():
    """score > max_score must raise ValueError (D-02 range enforcement)."""
    with pytest.raises(ValueError):
        AttemptScore(score=6, max_score=5, is_correct=False)


def test_attempt_score_score_zero_valid():
    """score=0 with is_correct=False is a valid construction (D-02: 0..output_length)."""
    s = AttemptScore(score=0, max_score=5, is_correct=False)
    assert s.score == 0


def test_attempt_score_perfect_correct():
    """score==max_score with is_correct=True constructs and is_correct==True (D-03)."""
    s = AttemptScore(score=5, max_score=5, is_correct=True)
    assert s.is_correct is True


def test_difficulty_config_defaults():
    """DifficultyConfig() uses alphabet=A-Z and output_length=5 (D-05, D-06)."""
    d = DifficultyConfig()
    assert d.alphabet == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert d.output_length == 5


def test_difficulty_config_short_alphabet_rejected():
    """Single-character alphabet must raise ValueError (minimum alphabet size = 2)."""
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="A")


def test_difficulty_config_zero_length_rejected():
    """output_length=0 must raise ValueError (output_length must be >= 1)."""
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="AB", output_length=0)


def test_dataclasses_are_frozen_score():
    """Mutating AttemptScore.score after construction raises FrozenInstanceError (D-09)."""
    from dataclasses import FrozenInstanceError
    s = AttemptScore(score=3, max_score=5, is_correct=False)
    with pytest.raises(FrozenInstanceError):
        s.score = 4  # type: ignore[misc]


def test_dataclasses_are_frozen_config():
    """Mutating DifficultyConfig.alphabet after construction raises FrozenInstanceError (D-09)."""
    from dataclasses import FrozenInstanceError
    d = DifficultyConfig()
    with pytest.raises(FrozenInstanceError):
        d.alphabet = "X"  # type: ignore[misc]


def test_attempt_score_no_ciphertext_field():
    """AttemptScore must NOT expose ciphertext, key, or shifts fields (RULE-04, D-09).

    The information boundary requires that AttemptScore contains only aggregate
    score data — never the cipher key, ground-truth ciphertext, or per-position shifts.
    """
    s = AttemptScore(score=3, max_score=5, is_correct=False)
    assert not hasattr(s, "ciphertext"), "AttemptScore must not have a 'ciphertext' field"
    assert not hasattr(s, "key"), "AttemptScore must not have a 'key' field"
    assert not hasattr(s, "shifts"), "AttemptScore must not have a 'shifts' field"
