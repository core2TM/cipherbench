"""CipherBench — AGI Proximity Benchmark.

Public API surface. Import from here; internal module paths are implementation detail.

Available:
    AttemptScore      — frozen dataclass: score, max_score, is_correct
    DifficultyConfig  — frozen dataclass: alphabet, output_length
    RuleEngine        — stateful oracle; single public method: score_attempt()
    create_rule_engine — factory: create_rule_engine(seed, difficulty) -> RuleEngine
"""
from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine

__all__ = ["AttemptScore", "DifficultyConfig", "RuleEngine", "create_rule_engine"]
