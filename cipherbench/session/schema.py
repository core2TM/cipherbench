"""CipherBench session data contracts.

This module contains two public names:
  AttemptEntry   — TypedDict for a single probe attempt
  SessionRecord  — TypedDict for a complete benchmark session

Session fields use `level` (1|2|3) instead of seed/difficulty/puzzle_hash
since puzzles are now deterministic with no RNG.
"""
from typing import List, Literal, Optional, TypedDict


class AttemptEntry(TypedDict):
    """A single probe attempt in a benchmark session.

    Fields
    ------
    attempt_num : int
        1-indexed attempt number within the session.
    probe : Optional[str]
        The probe string submitted (5 characters from the puzzle alphabet).
        None if extraction completely failed (extraction_failed=True).
    encoded_output : Optional[str]
        The cipher-encoded form of the probe. Always present for valid probes.
        None only for extraction failures.
    score : Optional[int]
        Number of positions where encode(probe)[i] == ground_truth[i] (0..max_score).
        None if extraction failed and no score was computed.
    max_score : int
        Maximum possible score (equals output_length, e.g. 5).
    is_correct : bool
        True iff score == max_score. False for extraction failures.
    raw_response : Optional[str]
        The full raw text from the model (model sessions only). None for human sessions.
    extraction_failed : bool
        True if the model response did not yield a valid probe string.
        Extraction failures do NOT consume an attempt count.
    """

    attempt_num: int
    probe: Optional[str]
    encoded_output: Optional[str]
    score: Optional[int]
    max_score: int
    is_correct: bool
    raw_response: Optional[str]
    extraction_failed: bool


class SessionRecord(TypedDict):
    """Top-level benchmark session schema.

    Fields
    ------
    session_id : str
        Unique session identifier, e.g. '20260529T143022-claude-opus'.
    runner_type : Literal['model', 'human']
        'model' for LLM sessions; 'human' for human baseline sessions.
    model : Optional[str]
        LiteLLM model string for model sessions. None for human sessions.
    player_name : Optional[str]
        Player name for human sessions. None for model sessions.
    level : int
        Puzzle level: 1, 2, or 3.
    ground_truth : str
        The fixed cipher target shown to the player at session start.
    outcome : Literal['success', 'failure', 'rate_limited', 'in_progress']
        Terminal state of the session.
    final_answer : Optional[str]
        The model's or human's final ANSWER: submission.
    attempts : List[AttemptEntry]
        All probe attempts, including extraction failures.
    created_at : str
        ISO 8601 UTC timestamp when the session was initialized.
    completed_at : Optional[str]
        ISO 8601 UTC timestamp when the session reached a terminal state.
    """

    session_id: str
    runner_type: Literal["model", "human"]
    model: Optional[str]
    player_name: Optional[str]
    level: int
    ground_truth: str
    outcome: Literal["success", "failure", "rate_limited", "in_progress"]
    final_answer: Optional[str]
    attempts: List[AttemptEntry]
    created_at: str
    completed_at: Optional[str]
