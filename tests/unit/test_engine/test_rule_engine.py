"""Integration tests for RuleEngine class and create_rule_engine factory.

Covers: information boundary enforcement (RULE-04, D-09), input validation (ASVS V5),
state evolution (RULE-01), and factory isolation (D-10).
"""
from __future__ import annotations

import inspect

import pytest

from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine


# ---------------------------------------------------------------------------
# Boundary tests — RULE-04, D-09
# ---------------------------------------------------------------------------


def test_no_public_key_accessor(rule_engine_seed_42):
    """RuleEngine must expose exactly one public method: score_attempt."""
    engine = rule_engine_seed_42
    public_methods = [m for m in dir(engine) if not m.startswith("_")]
    assert public_methods == ["score_attempt"], (
        f"Expected only ['score_attempt'], got {public_methods}"
    )


def test_score_attempt_returns_count_only(rule_engine_seed_42):
    """score_attempt returns AttemptScore with no cipher state exposed."""
    from cipherbench.types import AttemptScore

    result = rule_engine_seed_42.score_attempt("AAAAA")
    assert isinstance(result, AttemptScore)
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 5
    assert isinstance(result.is_correct, bool)
    assert not hasattr(result, "ciphertext")
    assert not hasattr(result, "key")
    assert not hasattr(result, "shifts")


def test_cipher_key_not_accessible(rule_engine_seed_42):
    """Engine must not expose cipher key, ground truth, base_shifts, or encode method."""
    engine = rule_engine_seed_42
    assert not hasattr(engine, "cipher_key")
    assert not hasattr(engine, "ground_truth")
    assert not hasattr(engine, "base_shifts")
    assert not hasattr(engine, "encode")


# ---------------------------------------------------------------------------
# Input validation tests — ASVS V5
# ---------------------------------------------------------------------------


def test_score_attempt_rejects_wrong_length(rule_engine_seed_42):
    """score_attempt must raise ValueError for a guess that is too short."""
    with pytest.raises(ValueError):
        rule_engine_seed_42.score_attempt("ABC")  # length 3, expected 5


def test_score_attempt_rejects_too_long(rule_engine_seed_42):
    """score_attempt must raise ValueError for a guess that is too long."""
    with pytest.raises(ValueError):
        rule_engine_seed_42.score_attempt("ABCDEFGH")  # length 8, expected 5


def test_score_attempt_rejects_invalid_chars(rule_engine_seed_42):
    """score_attempt must raise ValueError for characters outside the alphabet."""
    with pytest.raises(ValueError):
        rule_engine_seed_42.score_attempt("12345")  # digits not in A-Z


# ---------------------------------------------------------------------------
# State evolution test — RULE-01
# ---------------------------------------------------------------------------


def test_factory_produces_fresh_instances():
    """Two engines from the same seed must produce equal score_attempt results at round 1."""
    d = DifficultyConfig()
    engine_a = create_rule_engine(seed=42, difficulty=d)
    engine_b = create_rule_engine(seed=42, difficulty=d)
    result_a = engine_a.score_attempt("ABCDE")
    result_b = engine_b.score_attempt("ABCDE")
    assert result_a == result_b


def test_state_layer_changes_target_across_rounds():
    """The encoded target must differ between round 1 and round 2 (RULE-01 state layer active).

    This is a white-box test that calls the private _encode_for_round method directly
    to verify the state layer is active without going through score_attempt.
    Uses seed=42 which produces non-trivial base shifts (all >= 1, never 0).
    """
    engine = create_rule_engine(seed=42, difficulty=DifficultyConfig())
    encoded_round_1 = engine._encode_for_round(1)
    encoded_round_2 = engine._encode_for_round(2)
    # With linear multiplier: round 2 shifts are 2× round 1. For non-zero base_shifts
    # this produces a different ciphertext at every round.
    assert encoded_round_1 != encoded_round_2, (
        "State layer not active: round 1 and round 2 produced identical encoded targets"
    )


# ---------------------------------------------------------------------------
# Factory isolation test — D-10
# ---------------------------------------------------------------------------


def test_instance_round_counter_is_independent():
    """Advancing engine_a does not affect engine_b created from the same seed.

    engine_a consumes 3 rounds, then engine_b (fresh from same seed) round 1 score
    must match engine_a's original round 1 score.
    """
    d = DifficultyConfig()
    # Create engine_c to record the original round 1 score before any state mutation
    engine_c = create_rule_engine(seed=42, difficulty=d)
    original_round_1 = engine_c.score_attempt("ABCDE")

    # Advance engine_a by 3 rounds
    engine_a = create_rule_engine(seed=42, difficulty=d)
    engine_a.score_attempt("ABCDE")  # round 1
    engine_a.score_attempt("ABCDE")  # round 2
    engine_a.score_attempt("ABCDE")  # round 3

    # Fresh engine_b from same seed — its round 1 must match original_round_1
    engine_b = create_rule_engine(seed=42, difficulty=d)
    fresh_round_1 = engine_b.score_attempt("ABCDE")
    assert fresh_round_1 == original_round_1, (
        "State bleed: engine_b round 1 differs from original round 1 after engine_a was advanced"
    )


# ---------------------------------------------------------------------------
# show_encoding parameter tests — Task 1 TDD (w7g)
# ---------------------------------------------------------------------------


def test_score_attempt_default_encoded_output_is_none():
    """score_attempt() with default args returns AttemptScore where encoded_output is None."""
    engine = create_rule_engine(seed=42)
    result = engine.score_attempt("AAAAA")
    assert result.encoded_output is None


def test_score_attempt_show_encoding_false_encoded_output_is_none():
    """score_attempt(..., show_encoding=False) explicitly keeps encoded_output as None."""
    engine = create_rule_engine(seed=42)
    result = engine.score_attempt("AAAAA", show_encoding=False)
    assert result.encoded_output is None


def test_score_attempt_show_encoding_true_returns_string():
    """score_attempt("AAAAA", show_encoding=True) returns encoded_output as a non-None string."""
    engine = create_rule_engine(seed=42)
    result = engine.score_attempt("AAAAA", show_encoding=True)
    assert result.encoded_output is not None
    assert isinstance(result.encoded_output, str)


def test_score_attempt_show_encoding_true_correct_length():
    """score_attempt show_encoding=True returns encoded_output with length equal to output_length."""
    engine = create_rule_engine(seed=42)
    result = engine.score_attempt("AAAAA", show_encoding=True)
    assert len(result.encoded_output) == 5


def test_score_attempt_show_encoding_true_alphabet_chars():
    """score_attempt show_encoding=True: encoded_output chars are in the configured alphabet."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    engine = create_rule_engine(seed=42)
    result = engine.score_attempt("AAAAA", show_encoding=True)
    assert all(c in alphabet for c in result.encoded_output)


def test_score_attempt_show_encoding_does_not_change_score():
    """show_encoding=True must not change score or is_correct vs show_encoding=False."""
    engine_a = create_rule_engine(seed=42)
    result_hidden = engine_a.score_attempt("AAAAA", show_encoding=False)

    engine_b = create_rule_engine(seed=42)
    result_shown = engine_b.score_attempt("AAAAA", show_encoding=True)

    assert result_hidden.score == result_shown.score
    assert result_hidden.is_correct == result_shown.is_correct
