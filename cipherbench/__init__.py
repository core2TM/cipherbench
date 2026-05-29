"""CipherBench — AGI Proximity Benchmark.

Public API surface. Import from here; internal module paths are implementation detail.

Available:
    AttemptScore      — frozen dataclass: score, max_score, is_correct
    DifficultyConfig  — frozen dataclass: alphabet, output_length
    RuleEngine        — stateful oracle; single public method: score_attempt()
    create_rule_engine — factory: create_rule_engine(seed, difficulty) -> RuleEngine
    Puzzle            — frozen dataclass: seed, difficulty, puzzle_hash
    generate_puzzle   — factory: generate_puzzle(seed, difficulty) -> Puzzle
    verify_puzzle     — hash integrity assertion: verify_puzzle(puzzle) -> None
    get_tier          — tier classifier: get_tier(difficulty) -> str
    EASY              — DifficultyConfig preset: 10-char alphabet, depth=1, rate=1.0
    MEDIUM            — DifficultyConfig preset: 26-char alphabet, depth=2, rate=1.5
    HARD              — DifficultyConfig preset: 36-char alphabet, depth=3, rate=2.0
    load_sessions     — load and filter terminal sessions from a directory
    compute_report    — aggregate all metrics into a ScoreReport dict
    ScoreReport       — TypedDict: the structured scoring result
"""
from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
from cipherbench.puzzle import Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD
from cipherbench.scoring.scorer import load_sessions, compute_report, ScoreReport

__all__ = [
    "AttemptScore",
    "DifficultyConfig",
    "RuleEngine",
    "create_rule_engine",
    "Puzzle",
    "generate_puzzle",
    "verify_puzzle",
    "get_tier",
    "EASY",
    "MEDIUM",
    "HARD",
    "load_sessions",
    "compute_report",
    "ScoreReport",
]
