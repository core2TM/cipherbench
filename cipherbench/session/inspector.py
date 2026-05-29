"""CipherBench session inspector — display a recorded session trace in the terminal.

Public names:
  inspect_session  — locate a session by ID (substring/case-insensitive) and display it
  display_session  — render a single session dict as Rich Panel + Table

Design decisions implemented here:
  D-01  inspect command resolves session_id by substring match against JSON filename stems
  D-02  Ambiguous match (>1 result) prints list of matches and exits 1
  D-03  Each attempt row shows: attempt_num, probe, score/max_score, is_correct
  D-04  Extraction-failure rows display probe as "[extraction failed]" with score as "—"
  D-05  Footer shows outcome and final_answer when outcome == 'success'
  D-06  Footer shows "Final answer not reached" when final_answer is None
  D-07  inspect_session reads sessions_dir; does not parse engine internals
  D-08  Not-found: prints list of available session IDs and exits 1
  D-09  Missing sessions_dir: prints descriptive error and exits 1
  D-10  Empty sessions_dir: prints descriptive error and exits 1
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()


def inspect_session(
    session_id: str,
    sessions_dir: Path,
    console: Console | None = None,
) -> None:
    """Locate a session by ID and display it to the terminal (SESS-03).

    Resolves *session_id* by case-insensitive substring match against JSON
    filename stems in *sessions_dir*.  Exits with code 1 on error (not found,
    ambiguous, missing dir, empty dir, malformed JSON).

    Parameters
    ----------
    session_id : str
        Full or partial session identifier to look up.
    sessions_dir : Path
        Directory containing ``*.json`` session files.
    console : Console | None
        Rich Console to render to.  Defaults to the module-level ``_console``.
    """
    raise NotImplementedError


def display_session(session: dict, console: Console) -> None:
    """Render a single session dict as a Rich Panel + attempts Table (D-03, D-04, D-05, D-06).

    Parameters
    ----------
    session : dict
        A SessionRecord-shaped dict loaded from a session JSON file.
    console : Console
        Rich Console instance to print to (injected by inspect_session or tests).

    Design decisions applied:
      D-03  Table rows: attempt_num | probe | score | is_correct
      D-04  Extraction failures: probe = "[extraction failed]", score = "—"
      D-05  Footer row shows outcome + final_answer when outcome == 'success'
      D-06  Footer shows "Final answer not reached" when final_answer is None
    """
    raise NotImplementedError
