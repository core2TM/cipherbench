"""CipherBench session data contracts — D-08 (AttemptEntry), D-11 (SessionRecord).

This module contains two public names:
  AttemptEntry   — TypedDict for a single probe attempt (D-08)
  SessionRecord  — TypedDict for a complete benchmark session (D-11)

Design decisions implemented here:
  D-07  runner_type field: 'model' | 'human' — canonical discriminator for Phase 4/5
  D-08  AttemptEntry fields: attempt_num, probe, score, max_score, is_correct,
        raw_response, extraction_failed
  D-11  SessionRecord fields: session_id, runner_type, model, player_name, seed,
        difficulty, puzzle_hash, outcome, final_answer, attempts, created_at,
        completed_at

Note: NO imports from cipherbench.engine — this is the pure data contract layer,
identical to the discipline in cipherbench.types.
"""
from __future__ import annotations

from typing import List, Literal, Optional, TypedDict


class AttemptEntry(TypedDict):
    """A single probe attempt in a benchmark session (D-08).

    Fields
    ------
    attempt_num : int
        1-indexed attempt number within the session.
    probe : Optional[str]
        The probe string submitted (5 characters from the puzzle alphabet).
        None if extraction completely failed (extraction_failed=True).
    score : Optional[int]
        Number of characters in the correct position (0..max_score).
        None if extraction failed and no score was computed.
    max_score : int
        Maximum possible score (equals output_length, e.g. 5).
    is_correct : bool
        True iff score == max_score.  False for extraction failures.
    raw_response : Optional[str]
        The full raw text from the model (model sessions only).
        None for human sessions.
    extraction_failed : bool
        True if the model response did not yield a valid probe string.
        Extraction failures do NOT consume an attempt count (D-05).
    """

    attempt_num: int
    probe: Optional[str]
    score: Optional[int]
    max_score: int
    is_correct: bool
    raw_response: Optional[str]
    extraction_failed: bool


class SessionRecord(TypedDict):
    """Top-level benchmark session schema (D-11).

    Fields
    ------
    session_id : str
        Unique session identifier, e.g. '20260529T143022-claude-opus'.
        Used as primary key for Phase 5 session inspector.
    runner_type : Literal['model', 'human']
        Canonical discriminator for Phase 4 scoring and Phase 5 inspector (D-07).
        'model' for LLM sessions; 'human' for human baseline sessions.
    model : Optional[str]
        LiteLLM model string for model sessions (e.g. 'anthropic/claude-opus-4-7').
        None for human sessions.
    player_name : Optional[str]
        Player name for human sessions.  None for model sessions.
    seed : int
        RNG seed used to generate the puzzle.  Enables reproducibility.
    difficulty : str
        Tier name: 'easy' | 'medium' | 'hard' | 'custom'.
        Stored as a string (not DifficultyConfig) per D-11 to keep JSON compact.
    puzzle_hash : str
        Integrity hash copied from the Puzzle object.
    outcome : Literal['success', 'failure', 'rate_limited', 'in_progress']
        Terminal state of the session (D-09).
        'in_progress' is overwritten on terminal state; 'rate_limited' triggers resume.
    final_answer : Optional[str]
        The model's or human's final ANSWER: submission.  None if session did not
        reach the final-answer step (e.g. rate_limited before all 5 probes).
    attempts : List[AttemptEntry]
        All probe attempts, including extraction failures (D-08).
    created_at : str
        ISO 8601 UTC timestamp when the session was initialized.
    completed_at : Optional[str]
        ISO 8601 UTC timestamp when the session reached a terminal state.
        None for in_progress sessions.
    """

    session_id: str
    runner_type: Literal["model", "human"]
    model: Optional[str]
    player_name: Optional[str]
    seed: int
    difficulty: str
    puzzle_hash: str
    outcome: Literal["success", "failure", "rate_limited", "in_progress"]
    final_answer: Optional[str]
    attempts: List[AttemptEntry]
    created_at: str
    completed_at: Optional[str]
