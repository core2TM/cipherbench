"""CipherBench data contracts.

Defines the shared frozen dataclasses that all phases import.
These types are the stable public API surface.

NO imports from cipherbench.engine — this is the pure data layer.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DifficultyConfig:
    """Configuration for a cipher puzzle difficulty tier.

    Only one difficulty exists in v1: easy (alphabet A-J, length 5).
    Frozen after construction — mutation raises FrozenInstanceError.

    Fields
    ------
    alphabet : str
        The character set used for input and output. Default: A-J.
        Must have at least 2 characters.
    output_length : int
        Number of characters in both the probe and the encoded output. Default: 5.
    """

    alphabet: str = "ABCDEFGHIJ"
    output_length: int = 5

    def __post_init__(self) -> None:
        if len(self.alphabet) < 2:
            raise ValueError("alphabet must have at least 2 characters")
        if self.output_length < 2:
            raise ValueError("output_length must be at least 2")


@dataclass(frozen=True)
class AttemptScore:
    """Result returned by RuleEngine.score_attempt().

    Exposes aggregate position-correct count and the encoded probe output.
    Frozen after construction — mutation raises FrozenInstanceError.

    Fields
    ------
    score : int
        Number of positions where encode(probe)[i] == ground_truth[i] (0..max_score).
    max_score : int
        Maximum possible score (equals output_length, e.g. 5).
    is_correct : bool
        True iff score == max_score (exact match).
    chars_present : Optional[int]
        Number of chars in encode(probe) that appear anywhere in ground_truth
        (multiset intersection). None if not computed.
    encoded_output : Optional[str]
        The cipher-encoded form of the submitted probe. Always included so the
        player can see what their probe encodes to.
    """

    score: int
    max_score: int
    is_correct: bool
    encoded_output: Optional[str] = None

    def __post_init__(self) -> None:
        if not (0 <= self.score <= self.max_score):
            raise ValueError(
                f"score {self.score} out of range 0..{self.max_score}"
            )
        if self.is_correct != (self.score == self.max_score):
            raise ValueError("is_correct must match score == max_score")
