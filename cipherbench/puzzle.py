"""CipherBench puzzle generation layer.

Provides:
  Puzzle            — frozen dataclass: seed, difficulty, puzzle_hash
  generate_puzzle   — the only authorized Puzzle constructor (D-06)
  verify_puzzle     — hash-based integrity assertion (GEN-02, D-09)
  get_tier          — maps DifficultyConfig to tier name (D-12)
  EASY, MEDIUM, HARD — canonical DifficultyConfig tier presets (D-10)

Design decisions implemented here:
  D-04  Puzzle.create_engine() calls create_rule_engine — never reuses an engine.
  D-05  Each create_engine() call returns a fresh, independent RuleEngine instance.
  D-06  generate_puzzle is the only authorized Puzzle constructor.
  D-07  Hash covers derived state: base_shifts + k_list + ground_truth.
  D-08  hashlib.sha256 with json.dumps(sort_keys=True) serialization.
  D-09  verify_puzzle raises ValueError on hash mismatch — caller handles.
  D-10  EASY/MEDIUM/HARD constants defined here; all fields explicit.
  D-11  No global random.seed() calls — RNG threading delegated to create_rule_engine.
  D-12  get_tier returns 'easy'/'medium'/'hard'/'custom' — tier not stored in Puzzle.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine


@dataclass(frozen=True)
class Puzzle:
    """Immutable puzzle identity: seed + difficulty + derived-state hash.

    Frozen after construction (D-09). Two Puzzles with the same seed + difficulty
    are the same puzzle — equality via dataclass-generated __eq__.

    Never construct directly. Use generate_puzzle(seed, difficulty) (D-06).

    Fields
    ------
    seed : int
        Integer RNG seed. Same seed + difficulty always produces the same puzzle.
    difficulty : DifficultyConfig
        Difficulty configuration used to derive the puzzle state.
    puzzle_hash : str
        SHA-256 hex digest of the derived engine state (base_shifts + k_list +
        ground_truth). Proves bit-for-bit RNG determinism (GEN-02, D-07).
    """

    seed: int
    difficulty: DifficultyConfig
    puzzle_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if not self.puzzle_hash:
            raise ValueError("puzzle_hash must be non-empty")

    def create_engine(self) -> RuleEngine:
        """Return a fresh RuleEngine for this puzzle's seed and difficulty (D-05).

        Each call creates an independent engine instance with _round=1.
        Never reuse the returned engine across sessions (D-10).
        """
        return create_rule_engine(self.seed, self.difficulty)


def _compute_hash(base_shifts: list, k_list: list, ground_truth: str) -> str:
    """Compute SHA-256 hex digest of derived puzzle state (D-07, D-08).

    Serialization: json.dumps with sort_keys=True — deterministic across
    all Python versions and platforms for int/str values (no float ambiguity).
    k_list is always serialized as a JSON array, even at depth=1.
    """
    payload = json.dumps(
        {"base_shifts": base_shifts, "ground_truth": ground_truth, "k_list": k_list},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def generate_puzzle(seed: int, difficulty: DifficultyConfig = None) -> Puzzle:
    """Construct a Puzzle from a seed and difficulty configuration (GEN-01, GEN-02).

    This is the ONLY authorized way to construct a Puzzle (D-06).
    Calls create_rule_engine internally to derive base_shifts, k_list,
    and ground_truth, then hashes them for integrity verification.

    Parameters
    ----------
    seed : int
        Integer RNG seed. Same seed + difficulty yields the same Puzzle.
    difficulty : DifficultyConfig, optional
        Difficulty tier. Defaults to DifficultyConfig() (A-Z, length 5).

    Returns
    -------
    Puzzle
        Immutable puzzle with seed, difficulty, and SHA-256 hash of derived state.
    """
    if difficulty is None:
        difficulty = DifficultyConfig()
    engine = create_rule_engine(seed, difficulty)
    payload = engine._hash_payload()
    puzzle_hash = _compute_hash(payload["base_shifts"], payload["k_list"], payload["ground_truth"])
    return Puzzle(seed=seed, difficulty=difficulty, puzzle_hash=puzzle_hash)


def verify_puzzle(puzzle: Puzzle) -> None:
    """Re-derive the puzzle hash and assert it matches the stored value (GEN-02, D-09).

    Raises
    ------
    ValueError
        If the re-derived hash does not match puzzle.puzzle_hash.
        Message format: 'hash mismatch: expected {X}, got {Y}'.
    """
    engine = create_rule_engine(puzzle.seed, puzzle.difficulty)
    payload = engine._hash_payload()
    expected = _compute_hash(payload["base_shifts"], payload["k_list"], payload["ground_truth"])
    if expected != puzzle.puzzle_hash:
        raise ValueError(
            f"hash mismatch: expected {expected}, got {puzzle.puzzle_hash}"
        )


# ---------------------------------------------------------------------------
# Tier constants (D-10, D-11) — all four fields explicit to avoid get_tier
# fragility when DifficultyConfig grows new fields (Pitfall 6 from RESEARCH.md).
# ---------------------------------------------------------------------------

EASY = DifficultyConfig(
    alphabet="ABCDEFGHIJ",
    output_length=5,
    state_change_rate=1.0,
    cross_char_depth=1,
)

MEDIUM = DifficultyConfig(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    output_length=5,
    state_change_rate=1.5,
    cross_char_depth=2,
)

HARD = DifficultyConfig(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    output_length=5,
    state_change_rate=2.0,
    cross_char_depth=3,
)


def get_tier(difficulty: DifficultyConfig) -> str:
    """Return the tier name for a given DifficultyConfig (D-12).

    Uses frozen dataclass __eq__ (field-by-field comparison).
    Returns 'custom' for any config not matching a named preset.

    Parameters
    ----------
    difficulty : DifficultyConfig
        Difficulty configuration to classify.

    Returns
    -------
    str
        One of 'easy', 'medium', 'hard', or 'custom'.
    """
    if difficulty == EASY:
        return "easy"
    if difficulty == MEDIUM:
        return "medium"
    if difficulty == HARD:
        return "hard"
    return "custom"
