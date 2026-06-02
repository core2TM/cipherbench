"""Integration tests for RuleEngine class and create_rule_engine factory.

Covers: information boundary enforcement (RULE-04, D-09), input validation (ASVS V5),
state evolution (RULE-01), and factory isolation (D-10).
"""

import inspect

import pytest

from cipherbench.puzzle import create_engine_for_level


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
# State evolution tests
# ---------------------------------------------------------------------------


def test_factory_produces_fresh_instances():
    """Two engines from level 1 must produce equal score_attempt results."""
    engine_a = create_engine_for_level(1)
    engine_b = create_engine_for_level(1)
    result_a = engine_a.score_attempt("ABCDE")
    result_b = engine_b.score_attempt("ABCDE")
    assert result_a == result_b


def test_encoding_is_deterministic():
    """Same probe on two fresh level-1 engines always returns identical score and encoding."""
    engine = create_engine_for_level(1)
    engine2 = create_engine_for_level(1)
    result_a = engine.score_attempt("ABCDE")
    result_b = engine2.score_attempt("ABCDE")
    assert result_a.score == result_b.score
    assert result_a.encoded_output == result_b.encoded_output


# ---------------------------------------------------------------------------
# Factory isolation test — D-10
# ---------------------------------------------------------------------------


def test_instance_round_counter_is_independent():
    """Advancing engine_a does not affect engine_b created from the same level.

    engine_a consumes 3 attempts, then engine_b (fresh from same level) attempt 1 score
    must match engine_a's original attempt 1 score.
    """
    # Create engine_c to record the original attempt 1 score before any state mutation
    engine_c = create_engine_for_level(1)
    original_result = engine_c.score_attempt("ABCDE")

    # Advance engine_a by 3 attempts
    engine_a = create_engine_for_level(1)
    engine_a.score_attempt("ABCDE")  # attempt 1
    engine_a.score_attempt("ABCDE")  # attempt 2
    engine_a.score_attempt("ABCDE")  # attempt 3

    # Fresh engine_b from same level — its attempt 1 must match original_result
    engine_b = create_engine_for_level(1)
    fresh_result = engine_b.score_attempt("ABCDE")
    assert fresh_result == original_result, (
        "State bleed: engine_b attempt 1 differs from original after engine_a was advanced"
    )
