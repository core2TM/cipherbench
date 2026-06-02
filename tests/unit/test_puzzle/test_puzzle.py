"""Tests for cipherbench.puzzle — current fixed-level API.

Covers:
  LEVEL_CONFIGS has exactly 3 entries with integer keys 1, 2, 3
  get_ground_truth returns correct strings and raises for invalid levels
  get_max_attempts returns 5 for all levels and raises for invalid levels
  create_engine_for_level returns RuleEngine for levels 1, 2, 3 and raises for invalid
  Engines for different levels produce different encoded outputs
"""

import pytest
from cipherbench.engine.rule_engine import RuleEngine
from cipherbench.puzzle import (
    ALPHABET,
    LEVEL_CONFIGS,
    OUTPUT_LENGTH,
    get_ground_truth,
    get_max_attempts,
    create_engine_for_level,
)


# ---------------------------------------------------------------------------
# LEVEL_CONFIGS structure
# ---------------------------------------------------------------------------


def test_level_configs_has_three_entries():
    """LEVEL_CONFIGS must have exactly 3 entries."""
    assert len(LEVEL_CONFIGS) == 3


def test_level_configs_keys_are_1_2_3():
    """LEVEL_CONFIGS keys must be exactly {1, 2, 3}."""
    assert set(LEVEL_CONFIGS.keys()) == {1, 2, 3}


# ---------------------------------------------------------------------------
# get_ground_truth
# ---------------------------------------------------------------------------


def test_get_ground_truth_level_1():
    """get_ground_truth(1) returns the level-1 ground truth string."""
    gt = get_ground_truth(1)
    assert isinstance(gt, str)
    assert len(gt) == OUTPUT_LENGTH


def test_get_ground_truth_level_2():
    """get_ground_truth(2) returns the level-2 ground truth string."""
    gt = get_ground_truth(2)
    assert isinstance(gt, str)
    assert len(gt) == OUTPUT_LENGTH


def test_get_ground_truth_level_3():
    """get_ground_truth(3) returns the level-3 ground truth string."""
    gt = get_ground_truth(3)
    assert isinstance(gt, str)
    assert len(gt) == OUTPUT_LENGTH


def test_get_ground_truth_invalid_level_0():
    """get_ground_truth(0) raises ValueError."""
    with pytest.raises(ValueError):
        get_ground_truth(0)


def test_get_ground_truth_invalid_level_4():
    """get_ground_truth(4) raises ValueError."""
    with pytest.raises(ValueError):
        get_ground_truth(4)


def test_get_ground_truth_levels_are_distinct():
    """Ground truths must differ across levels."""
    gt1 = get_ground_truth(1)
    gt2 = get_ground_truth(2)
    gt3 = get_ground_truth(3)
    assert gt1 != gt2
    assert gt2 != gt3
    assert gt1 != gt3


# ---------------------------------------------------------------------------
# get_max_attempts
# ---------------------------------------------------------------------------


def test_get_max_attempts_returns_5_for_all_levels():
    """get_max_attempts returns 5 for levels 1, 2, and 3."""
    for level in (1, 2, 3):
        assert get_max_attempts(level) == 5


def test_get_max_attempts_invalid_level_0():
    """get_max_attempts(0) raises ValueError."""
    with pytest.raises(ValueError):
        get_max_attempts(0)


def test_get_max_attempts_invalid_level_4():
    """get_max_attempts(4) raises ValueError."""
    with pytest.raises(ValueError):
        get_max_attempts(4)


# ---------------------------------------------------------------------------
# create_engine_for_level
# ---------------------------------------------------------------------------


def test_create_engine_for_level_1():
    """create_engine_for_level(1) returns a RuleEngine instance."""
    engine = create_engine_for_level(1)
    assert isinstance(engine, RuleEngine)


def test_create_engine_for_level_2():
    """create_engine_for_level(2) returns a RuleEngine instance."""
    engine = create_engine_for_level(2)
    assert isinstance(engine, RuleEngine)


def test_create_engine_for_level_3():
    """create_engine_for_level(3) returns a RuleEngine instance."""
    engine = create_engine_for_level(3)
    assert isinstance(engine, RuleEngine)


def test_create_engine_for_level_invalid_0():
    """create_engine_for_level(0) raises ValueError."""
    with pytest.raises(ValueError):
        create_engine_for_level(0)


def test_create_engine_for_level_invalid_4():
    """create_engine_for_level(4) raises ValueError."""
    with pytest.raises(ValueError):
        create_engine_for_level(4)


def test_level_1_and_2_engines_produce_different_outputs():
    """Engines for level 1 and level 2 must produce different encoded outputs for the same probe."""
    engine1 = create_engine_for_level(1)
    engine2 = create_engine_for_level(2)
    result1 = engine1.score_attempt("ABCDE")
    result2 = engine2.score_attempt("ABCDE")
    assert result1.encoded_output != result2.encoded_output, (
        "Level 1 and Level 2 produced identical encoded outputs — cipher configurations must differ."
    )


def test_create_engine_fresh_each_call():
    """Two calls to create_engine_for_level(1) return independent engine instances."""
    engine_a = create_engine_for_level(1)
    engine_b = create_engine_for_level(1)
    # Advance engine_a and verify engine_b is unaffected
    engine_a.score_attempt("ABCDE")
    result_b = engine_b.score_attempt("ABCDE")
    engine_c = create_engine_for_level(1)
    result_c = engine_c.score_attempt("ABCDE")
    assert result_b == result_c, "engine_b and engine_c should produce the same result at attempt 1"
