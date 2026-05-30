"""CipherBench data contracts.

Defines the shared frozen dataclasses that all phases import.
These types are the stable public API surface — field names and validation
rules are locked by decisions D-01 through D-06 and D-09.

NO imports from cipherbench.engine — this is the pure data layer.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DifficultyConfig:
    """Configuration for a cipher puzzle difficulty tier.

    Frozen after construction — mutation raises FrozenInstanceError (D-09).
    All puzzle instances with the same DifficultyConfig are comparable.

    Fields
    ------
    alphabet : str
        The character set used for input and output. Default: A-Z (D-05).
        Must have at least 2 characters (prevents degenerate modular arithmetic).
    output_length : int
        Number of characters in both the probe and the encoded output. Default: 5 (D-06).
        Fixed at 5 across all puzzles in v1; the 5-attempt limit maps to this length.
    state_change_rate : float
        Multiplier applied to the state layer shift formula. Default: 1.0 (D-02).
        Controls how aggressively the effective shift grows with each round.
        Must be strictly positive (> 0.0); zero or negative values are meaningless.
    cross_char_depth : int
        Number of cross-character offset distances applied in sequence. Default: 1 (D-03).
        Depth=1 uses a single k value (identical to Phase 1 behavior).
        Depth=2+ stacks multiple k values for stronger positional mixing.
        Must be in [1, output_length-1]; depth >= output_length would prevent valid sampling.
    """

    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    output_length: int = 5
    state_change_rate: float = 1.0
    cross_char_depth: int = 1

    def __post_init__(self) -> None:
        if len(self.alphabet) < 2:
            raise ValueError("alphabet must have at least 2 characters")
        if self.output_length < 2:
            raise ValueError(
                "output_length must be at least 2 "
                "(output_length=1 leaves no valid cross_char_depth)"
            )
        if self.state_change_rate <= 0.0:
            raise ValueError("state_change_rate must be positive")
        if not (1 <= self.cross_char_depth <= self.output_length - 1):
            raise ValueError(
                f"cross_char_depth must be in [1, output_length-1={self.output_length - 1}],"
                f" got {self.cross_char_depth}"
            )


@dataclass(frozen=True)
class AttemptScore:
    """Result returned by RuleEngine.score_attempt().

    Exposes aggregate position-correct count only — never per-position breakdown,
    cipher key, ground-truth ciphertext, or shift values (D-01, D-09, RULE-04).

    Frozen after construction — mutation raises FrozenInstanceError (D-09).

    Fields
    ------
    score : int
        Number of characters in the correct position (0..max_score). D-01/D-02.
    max_score : int
        Maximum possible score (equals output_length, e.g. 5). D-02.
    is_correct : bool
        True iff score == max_score (exact match, binary). D-03.
        Must be consistent with score — a mismatch raises ValueError.
    correct_chars : int
        Number of characters in ``guess`` that appear anywhere in the ground truth
        (multiset intersection — independent of position). Display/hint only; not
        used in efficiency score calculation.
    """

    score: int
    max_score: int
    is_correct: bool
    correct_chars: int

    def __post_init__(self) -> None:
        if not (0 <= self.score <= self.max_score):
            raise ValueError(
                f"score {self.score} out of range 0..{self.max_score}"
            )
        if self.is_correct != (self.score == self.max_score):
            raise ValueError("is_correct must match score == max_score")
        if not (0 <= self.correct_chars <= self.max_score):
            raise ValueError(
                f"correct_chars {self.correct_chars} out of range 0..{self.max_score}"
            )
