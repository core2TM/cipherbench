"""CipherBench puzzle layer — 3 fixed levels, each with its own cipher.

Provides:
  ALPHABET        — the full 26-character alphabet (A-Z)
  OUTPUT_LENGTH   — fixed probe/answer length (5)
  LEVEL_CONFIGS   — dict mapping level int (1|2|3) to (ground_truth, max_attempts, substitution)
  get_ground_truth(level)      — returns the ground_truth for a level
  get_max_attempts(level)      — returns the attempt limit for a level
  create_engine_for_level(level) — constructs a fresh RuleEngine for the level

Level cipher rules:
  Level 1: Cyclic shift [+7,+8,+9,+10,+0] repeating — A→H, B→J, C→L, ...  (5 attempts)
  Level 2: ±7 alternating — even chars +7, odd chars -7 mod 26  (5 attempts)
  Level 3: ±7 alternating — same as Level 2  (5 attempts)
"""
from __future__ import annotations

from cipherbench.engine.layers import ATBASH, ALTERNATING7, CYCLIC5, GROUPED, STAIRCASE
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine

ALPHABET: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
OUTPUT_LENGTH: int = 5

LEVEL_CONFIGS: dict[int, tuple[str, int, list[int]]] = {
    1: ("ABCDE", 5, CYCLIC5),
    2: ("CLNHJ", 5, GROUPED),
    3: ("VJOTB", 5, STAIRCASE),
}


def get_ground_truth(level: int) -> str:
    """Return the fixed ground_truth (cipher target) for the given level.

    Parameters
    ----------
    level : int
        Level number: 1, 2, or 3.

    Returns
    -------
    str
        5-character ground_truth string using alphabet A-J.

    Raises
    ------
    ValueError
        If level is not 1, 2, or 3.
    """
    if level not in LEVEL_CONFIGS:
        raise ValueError(f"level must be 1, 2, or 3; got {level}")
    return LEVEL_CONFIGS[level][0]


def get_max_attempts(level: int) -> int:
    """Return the probe attempt limit for the given level.

    Parameters
    ----------
    level : int
        Level number: 1, 2, or 3.

    Returns
    -------
    int
        Maximum number of score_attempt calls allowed (5, 3, or 2).

    Raises
    ------
    ValueError
        If level is not 1, 2, or 3.
    """
    if level not in LEVEL_CONFIGS:
        raise ValueError(f"level must be 1, 2, or 3; got {level}")
    return LEVEL_CONFIGS[level][1]


def create_engine_for_level(level: int) -> RuleEngine:
    """Construct a fresh RuleEngine for the given level.

    Each call creates an independent engine instance. Never reuse an engine
    across sessions.

    Parameters
    ----------
    level : int
        Level number: 1, 2, or 3.

    Returns
    -------
    RuleEngine
        Fresh engine ready for scoring.
    """
    if level not in LEVEL_CONFIGS:
        raise ValueError(f"level must be 1, 2, or 3; got {level}")
    ground_truth, max_attempts, substitution = LEVEL_CONFIGS[level]
    return create_rule_engine(alphabet=ALPHABET, ground_truth=ground_truth, substitution=substitution, max_attempts=max_attempts)
