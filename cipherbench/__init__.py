"""CipherBench — AGI Proximity Benchmark.

Public API surface. Import from here; internal module paths are implementation detail.

Available now (Plan 01):
    AttemptScore      — frozen dataclass: score, max_score, is_correct
    DifficultyConfig  — frozen dataclass: alphabet, output_length

Added in Plan 03 (once engine/rule_engine.py is implemented):
    # from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
"""
from cipherbench.types import AttemptScore, DifficultyConfig

__all__ = ["AttemptScore", "DifficultyConfig"]
