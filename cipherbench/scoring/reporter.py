"""CipherBench scoring reporter — Rich terminal output for score reports (D-11).

Public names:
  render_score_report  — print Rich Panel + Table for a ScoreReport
  render_live_summary  — print one-line summary for end of cipherbench run (D-03)

Design decisions:
  D-11  Rich Panel header: model name + session count
  D-11  Rich Table columns: Difficulty | Sessions | Success Rate | Avg Efficiency | AGI Proximity
  D-03  Live summary: one typer.echo line only — no Rich components
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from cipherbench.scoring.scorer import ScoreReport

_console = Console()


def render_score_report(report: "ScoreReport", model: str) -> None:
    """Print Rich Panel header + per-difficulty Table to terminal (D-11).

    Parameters
    ----------
    report : ScoreReport
        Structured scoring result from compute_report().
    model : str
        Model identifier string shown in the Panel title.
    """
    raise NotImplementedError


def render_live_summary(sessions: list[dict], human_sessions: list[dict]) -> None:
    """Print one-line summary at end of cipherbench run (D-03).

    Format: "3/5 success (60%) | avg efficiency: 0.72 | AGI proximity: 0.85x"
    Uses typer.echo (not Rich console) to keep run output clean.

    Parameters
    ----------
    sessions : list[dict]
        Completed model sessions for the current run.
    human_sessions : list[dict]
        Human baseline sessions for AGI proximity calculation (SCORE-03).
    """
    raise NotImplementedError
