"""Tests for cipherbench.puzzle — Puzzle dataclass, generate_puzzle, verify_puzzle, get_tier.

Covers:
  GEN-01: Same seed + difficulty always yields identical Puzzle (hash equality)
  GEN-02: verify_puzzle passes for fresh puzzle; raises ValueError on mutation
  GEN-03: EASY/MEDIUM/HARD are distinct configs; get_tier maps correctly;
          tiers produce measurably distinct complexity
  D-04/D-05: Puzzle.create_engine() returns fresh RuleEngine each call
  D-06: Public import path works as specified
  D-09: Puzzle is frozen; no leaking of engine private state through Puzzle
  D-12: get_tier returns 'custom' for unrecognized configs
"""
from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from hypothesis import given, settings
from hypothesis import strategies as st

from cipherbench.types import DifficultyConfig
from cipherbench.puzzle import (
    Puzzle,
    generate_puzzle,
    verify_puzzle,
    get_tier,
    EASY,
    MEDIUM,
    HARD,
)
from cipherbench.engine.rule_engine import RuleEngine


# ---------------------------------------------------------------------------
# GEN-01: Reproducibility
# ---------------------------------------------------------------------------


def test_generate_puzzle_reproducible():
    """GEN-01: Same seed + difficulty called twice produces identical puzzle_hash."""
    p1 = generate_puzzle(42)
    p2 = generate_puzzle(42)
    assert p1.puzzle_hash == p2.puzzle_hash


def test_same_seed_same_puzzle():
    """GEN-01: generate_puzzle with same seed and explicit difficulty is deterministic."""
    p1 = generate_puzzle(seed=42, difficulty=MEDIUM)
    p2 = generate_puzzle(seed=42, difficulty=MEDIUM)
    assert p1 == p2  # frozen dataclass __eq__ covers all fields


# ---------------------------------------------------------------------------
# GEN-02: Hash verification
# ---------------------------------------------------------------------------


def test_verify_puzzle_passes():
    """GEN-02: verify_puzzle does not raise for a freshly generated puzzle."""
    puzzle = generate_puzzle(seed=0)
    verify_puzzle(puzzle)  # must not raise


def test_verify_puzzle_detects_mutation():
    """GEN-02: verify_puzzle raises ValueError when puzzle_hash does not match re-derived hash."""
    puzzle = generate_puzzle(seed=1)
    # Construct a tampered puzzle with a different seed but same stored hash
    tampered = Puzzle(seed=999, difficulty=puzzle.difficulty, puzzle_hash=puzzle.puzzle_hash)
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_puzzle(tampered)


# ---------------------------------------------------------------------------
# GEN-03: Tier constants and complexity
# ---------------------------------------------------------------------------


def test_tier_constants_distinct():
    """GEN-03: EASY, MEDIUM, HARD are three distinct DifficultyConfig instances."""
    assert EASY != MEDIUM
    assert MEDIUM != HARD
    assert EASY != HARD


def test_get_tier():
    """GEN-03: get_tier maps each preset to the correct string label."""
    assert get_tier(EASY) == "easy"
    assert get_tier(MEDIUM) == "medium"
    assert get_tier(HARD) == "hard"


def test_get_tier_custom():
    """D-12: get_tier returns 'custom' for a config not matching any preset."""
    custom = DifficultyConfig(
        alphabet="ABCDE",
        output_length=4,
        state_change_rate=1.0,
        cross_char_depth=1,
    )
    assert get_tier(custom) == "custom"


def test_difficulty_tiers_distinct_complexity():
    """GEN-03: EASY/MEDIUM/HARD generate structurally distinct puzzles over N seeds.

    Asserts that the set of puzzle_hash values differs across tiers for the same seeds,
    confirming that different parameters produce different derived states.
    """
    seeds = list(range(20))
    easy_hashes = {generate_puzzle(s, EASY).puzzle_hash for s in seeds}
    medium_hashes = {generate_puzzle(s, MEDIUM).puzzle_hash for s in seeds}
    hard_hashes = {generate_puzzle(s, HARD).puzzle_hash for s in seeds}
    assert easy_hashes.isdisjoint(medium_hashes), "EASY and MEDIUM share puzzle hashes"
    assert medium_hashes.isdisjoint(hard_hashes), "MEDIUM and HARD share puzzle hashes"
    assert easy_hashes.isdisjoint(hard_hashes), "EASY and HARD share puzzle hashes"


# ---------------------------------------------------------------------------
# D-04/D-05: Puzzle.create_engine() returns fresh independent engines
# ---------------------------------------------------------------------------


def test_create_engine_returns_rule_engine():
    """D-05: Puzzle.create_engine() returns a RuleEngine instance."""
    puzzle = generate_puzzle(seed=42)
    engine = puzzle.create_engine()
    assert isinstance(engine, RuleEngine)


def test_create_engine_fresh_each_call():
    """D-05: Two calls to puzzle.create_engine() return independent engine instances."""
    puzzle = generate_puzzle(seed=42)
    engine_a = puzzle.create_engine()
    engine_b = puzzle.create_engine()
    # Each should be at round 1; advance engine_a and check engine_b is unaffected
    engine_a.score_attempt("AAAAA")  # advance engine_a to round 2
    result_b = engine_b.score_attempt("AAAAA")
    engine_c = puzzle.create_engine()
    result_c = engine_c.score_attempt("AAAAA")
    assert result_b == result_c, "engine_b and engine_c should both be at round 1"


# ---------------------------------------------------------------------------
# D-09: Puzzle is frozen
# ---------------------------------------------------------------------------


def test_puzzle_is_frozen():
    """D-09: Mutating Puzzle fields after construction raises FrozenInstanceError."""
    puzzle = generate_puzzle(seed=42)
    with pytest.raises(FrozenInstanceError):
        puzzle.seed = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# D-06: Public import path
# ---------------------------------------------------------------------------


def test_public_import_path():
    """D-06: All public names importable from cipherbench.puzzle."""
    from cipherbench.puzzle import Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD
    assert Puzzle is not None
    assert callable(generate_puzzle)
    assert callable(verify_puzzle)
    assert callable(get_tier)


# ---------------------------------------------------------------------------
# GEN-02 Hypothesis property test
# ---------------------------------------------------------------------------


@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=50)
def test_verify_puzzle_always_passes_for_fresh_puzzle(seed: int) -> None:
    """GEN-02 property: verify_puzzle(generate_puzzle(seed)) never raises for any seed."""
    puzzle = generate_puzzle(seed)
    verify_puzzle(puzzle)  # must not raise
