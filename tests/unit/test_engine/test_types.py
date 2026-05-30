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
    """output_length=0 must raise ValueError (minimum is 2)."""
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="AB", output_length=0)


def test_difficulty_config_one_length_rejected():
    """output_length=1 must raise ValueError (minimum is 2)."""
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="AB", output_length=1)


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


# --- DifficultyConfig: state_change_rate tests (D-02) ---

def test_difficulty_config_state_change_rate_default():
    """DifficultyConfig().state_change_rate defaults to 1.0 (D-02)."""
    assert DifficultyConfig().state_change_rate == 1.0


def test_difficulty_config_state_change_rate_custom():
    """DifficultyConfig(state_change_rate=2.0) stores the custom value."""
    assert DifficultyConfig(state_change_rate=2.0).state_change_rate == 2.0


def test_difficulty_config_state_change_rate_invalid_zero():
    """state_change_rate=0.0 must raise ValueError (must be positive)."""
    with pytest.raises(ValueError):
        DifficultyConfig(state_change_rate=0.0)


def test_difficulty_config_state_change_rate_invalid_negative():
    """state_change_rate=-0.5 must raise ValueError (must be positive)."""
    with pytest.raises(ValueError):
        DifficultyConfig(state_change_rate=-0.5)


# --- DifficultyConfig: cross_char_depth tests (D-03) ---

def test_difficulty_config_cross_char_depth_default():
    """DifficultyConfig().cross_char_depth defaults to 1 (D-03)."""
    assert DifficultyConfig().cross_char_depth == 1


def test_difficulty_config_cross_char_depth_max_valid():
    """cross_char_depth=4 with output_length=5 is valid (4 == output_length - 1)."""
    d = DifficultyConfig(cross_char_depth=4, output_length=5)
    assert d.cross_char_depth == 4


def test_difficulty_config_cross_char_depth_exceeds_max():
    """cross_char_depth=5 with output_length=5 raises ValueError (max is output_length-1=4)."""
    with pytest.raises(ValueError):
        DifficultyConfig(cross_char_depth=5, output_length=5)


def test_difficulty_config_cross_char_depth_zero():
    """cross_char_depth=0 raises ValueError (minimum is 1)."""
    with pytest.raises(ValueError):
        DifficultyConfig(cross_char_depth=0)


def test_difficulty_config_defaults_backward_compat():
    """DifficultyConfig() still has alphabet=A-Z and output_length=5 (existing behavior unchanged)."""
    d = DifficultyConfig()
    assert d.alphabet == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert d.output_length == 5
