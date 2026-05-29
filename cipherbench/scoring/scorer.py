"""CipherBench scoring — pure computation: session loading, filtering, and score formulas.

Public names:
  load_sessions       — glob sessions dir, filter to terminal sessions matching criteria
  efficiency_score    — SCORE-02: per-session efficiency formula
  success_rate        — SCORE-01: fraction of successful sessions
  group_by_difficulty — SCORE-04: bucket sessions by difficulty tier
  agi_proximity       — SCORE-03: model_avg_efficiency / human_avg_efficiency; None if no baseline
  compute_report      — aggregate all metrics into a ScoreReport dict
  ScoreReport         — TypedDict for the complete scoring result

Design decisions implemented here:
  D-04  Session set = terminal sessions (outcome in {'success','failure'}) only
  D-06  attempts_used = count of attempts where extraction_failed=False
  D-08  Human baseline matched by difficulty tier, not exact seed
  D-09  AGI proximity = model_avg / human_avg; None when no human sessions or human_avg=0
  D-10  Empty or non-existent sessions directory: return [] (no error)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

MAX_ATTEMPTS: int = 5  # Fixed core mechanic — not configurable in v1 (D-06)
TERMINAL_OUTCOMES: frozenset[str] = frozenset({"success", "failure"})


class TierStats(TypedDict):
    """Per-difficulty-tier aggregated statistics (SCORE-04)."""

    sessions: int
    success_rate: float
    avg_efficiency: float
    agi_proximity: Optional[float]  # None renders as null in JSON, "N/A" in terminal


class ScoreReport(TypedDict):
    """Complete scoring result for a model or human player run (SCORE-01 through SCORE-04).

    Fields
    ------
    model : Optional[str]
        LiteLLM model string if scoring model sessions; None for human sessions.
    sessions_scored : int
        Total number of terminal sessions included in the report.
    by_difficulty : dict[str, TierStats]
        Per-difficulty-tier statistics (SCORE-04).
    totals : TierStats
        Aggregate statistics across all difficulty tiers.
    generated_at : str
        ISO 8601 UTC timestamp when this report was computed.
    """

    model: Optional[str]
    sessions_scored: int
    by_difficulty: dict[str, TierStats]
    totals: TierStats
    generated_at: str


def load_sessions(
    sessions_dir: Path,
    runner_type: str,
    model: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    """Load and filter terminal sessions from sessions_dir (D-04, D-05).

    Returns [] if sessions_dir does not exist or is empty (Pitfall 4 guard).
    Only includes sessions with outcome in TERMINAL_OUTCOMES (D-04).
    Exact-match on model string — no slug conversion (Pitfall 3).
    """
    raise NotImplementedError


def efficiency_score(session: dict) -> float:
    """SCORE-02: success * (max_attempts - attempts_used + 1) / max_attempts.

    attempts_used = count of attempts where extraction_failed=False (D-06).
    Division by zero is impossible: MAX_ATTEMPTS is a fixed positive integer.
    """
    raise NotImplementedError


def success_rate(sessions: list[dict]) -> float:
    """SCORE-01: fraction of sessions with outcome='success'.

    Returns 0.0 for an empty list.
    """
    raise NotImplementedError


def group_by_difficulty(sessions: list[dict]) -> dict[str, list[dict]]:
    """SCORE-04: bucket sessions by difficulty tier string ('easy'|'medium'|'hard').

    Unknown tiers are stored under their literal string value.
    """
    raise NotImplementedError


def agi_proximity(
    model_sessions: list[dict],
    human_sessions: list[dict],
) -> float | None:
    """SCORE-03: model_avg_efficiency / human_avg_efficiency.

    Returns None when no human baseline (D-10) or human_avg == 0.0 (Pitfall 5).
    Terminal display shows 'N/A'; JSON stores null (D-12).
    """
    raise NotImplementedError


def compute_report(
    model_sessions: list[dict],
    human_sessions: list[dict],
    model_str: str | None = None,
) -> ScoreReport:
    """Aggregate all metrics into a ScoreReport TypedDict (SCORE-01 through SCORE-04).

    Parameters
    ----------
    model_sessions : list[dict]
        Terminal model sessions to score.
    human_sessions : list[dict]
        Terminal human sessions used as AGI proximity baseline (SCORE-03).
    model_str : str or None
        LiteLLM model identifier to embed in the report.
    """
    raise NotImplementedError
