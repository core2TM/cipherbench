"""CipherBench — AGI Proximity Benchmark.

Public API surface. Import from here; internal module paths are implementation detail.

Available:
    AttemptScore           — frozen dataclass: score, max_score, is_correct, encoded_output
    DifficultyConfig       — frozen dataclass: alphabet, output_length
    RuleEngine             — stateful oracle; single public method: score_attempt()
    create_rule_engine     — factory: create_rule_engine(alphabet, ground_truth, max_attempts)
    ALPHABET               — fixed 10-character alphabet: "ABCDEFGHIJ"
    OUTPUT_LENGTH          — fixed probe/answer length: 5
    LEVEL_CONFIGS          — dict mapping level int (1|2|3) to (ground_truth, max_attempts)
    get_ground_truth       — get_ground_truth(level) -> str
    get_max_attempts       — get_max_attempts(level) -> int
    create_engine_for_level — create_engine_for_level(level) -> RuleEngine
    load_sessions          — load and filter terminal sessions from a directory
    compute_report         — aggregate all metrics into a ScoreReport dict
    ScoreReport            — TypedDict: the structured scoring result
    inspect_session        — replay a stored session trace to terminal
"""
from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
from cipherbench.puzzle import (
    ALPHABET,
    OUTPUT_LENGTH,
    LEVEL_CONFIGS,
    get_ground_truth,
    get_max_attempts,
    create_engine_for_level,
)
from cipherbench.scoring.scorer import load_sessions, compute_report, ScoreReport
from cipherbench.session.inspector import inspect_session

__all__ = [
    "AttemptScore",
    "DifficultyConfig",
    "RuleEngine",
    "create_rule_engine",
    "ALPHABET",
    "OUTPUT_LENGTH",
    "LEVEL_CONFIGS",
    "get_ground_truth",
    "get_max_attempts",
    "create_engine_for_level",
    "load_sessions",
    "compute_report",
    "ScoreReport",
    "inspect_session",
]
