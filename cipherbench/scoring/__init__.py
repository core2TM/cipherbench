"""CipherBench scoring package — session loading, formula computation, and reporting.

Public names:
  load_sessions   — load and filter terminal sessions from a directory
  compute_report  — compute ScoreReport from a list of sessions + optional human baseline
  ScoreReport     — TypedDict: the structured scoring result
"""
from cipherbench.scoring.scorer import load_sessions, compute_report, ScoreReport

__all__ = [
    "load_sessions",
    "compute_report",
    "ScoreReport",
]
