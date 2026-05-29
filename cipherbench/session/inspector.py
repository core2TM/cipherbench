"""CipherBench session inspector — display a recorded session trace in the terminal.

Public names:
  InspectorError   — raised by inspect_session on unrecoverable errors
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
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

_console = Console()


class InspectorError(RuntimeError):
    """Raised by inspect_session on unrecoverable errors (not-found, ambiguous, I/O)."""


def inspect_session(
    session_id: str,
    sessions_dir: Path,
    console: Console | None = None,
) -> None:
    """Locate a session by ID and display it to the terminal (SESS-03).

    Resolves *session_id* by case-insensitive substring match against JSON
    filename stems in *sessions_dir*.  Raises :exc:`InspectorError` on error
    (not found, ambiguous, missing dir, empty dir, malformed JSON) so that
    library callers can recover via ``except InspectorError``.

    The CLI layer (``inspect_command`` in ``app.py``) converts
    :exc:`InspectorError` to ``typer.Exit(code=1)`` so end-user behaviour is
    unchanged.

    Parameters
    ----------
    session_id : str
        Full or partial session identifier to look up.  Must be a non-empty,
        non-whitespace-only string.
    sessions_dir : Path
        Directory containing ``*.json`` session files.
    console : Console | None
        Rich Console to render to.  Defaults to the module-level ``_console``.
    """
    if console is None:
        console = _console

    # Guard: reject empty / whitespace-only session_id (CR-02)
    if not session_id or not session_id.strip():
        msg = "session_id must be a non-empty string."
        console.print(f"Error: {msg}", style="red")
        raise InspectorError(msg)

    # D-09: sessions directory missing
    if not sessions_dir.exists():
        msg = (
            f"Sessions directory not found: {sessions_dir}\n"
            "Run 'cipherbench run' or 'cipherbench play' to record sessions first."
        )
        console.print(msg, style="red")
        raise InspectorError(msg)

    all_paths = list(sessions_dir.glob("*.json"))

    # D-10: sessions directory empty
    if not all_paths:
        msg = f"No sessions found in: {sessions_dir}"
        console.print(msg, style="red")
        raise InspectorError(msg)

    matches = [p for p in all_paths if session_id.lower() in p.stem.lower()]
    all_stems = sorted(p.stem for p in all_paths)

    # D-08: zero matches — list all available stems
    if not matches:
        console.print(f"Session not found: '{session_id}'", style="red")
        for stem in all_stems:
            console.print(f"  {stem}")
        raise InspectorError(f"Session not found: '{session_id}'")

    # D-02: ambiguous (2+ matches) — list matching stems
    if len(matches) > 1:
        console.print(
            f"Ambiguous: matched {len(matches)} sessions for '{session_id}':",
            style="yellow",
        )
        for p in sorted(matches, key=lambda p: p.stem):
            console.print(f"  {p.stem}")
        raise InspectorError(
            f"Ambiguous: matched {len(matches)} sessions for '{session_id}'"
        )

    # Exactly 1 match — load and display
    path = matches[0]
    try:
        with path.open(encoding="utf-8") as f:  # WR-01: explicit UTF-8 for cross-platform compat
            session = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        msg = f"Error reading session file: {exc}"
        console.print(msg, style="red")
        raise InspectorError(msg) from exc

    display_session(session, console)


def display_session(session: dict, console: Console) -> None:
    """Render a single session dict as a Rich Panel + attempts Table (D-03, D-04, D-05, D-06).

    Parameters
    ----------
    session : dict
        A SessionRecord-shaped dict loaded from a session JSON file.
    console : Console
        Rich Console instance to print to (injected by inspect_session or tests).

    Design decisions applied:
      D-03  Panel header: session_id, Runner (unified label), Seed | Difficulty, Outcome
      D-04  Table columns: Attempt | Probe | Score | Correct?
      D-05  Extraction failures: Probe="— (extraction failed)", Score="—", Correct?="✗"
      D-06  Footer: "Final answer: <ans> — ✓/✗ Outcome" or "Final answer: — (not reached)"
    """
    # D-03: Panel header — unified runner label (no branching on runner_type)
    # WR-01: escape all user-controlled values to prevent Rich markup injection
    runner = escape(str(session.get("runner_type", "unknown")))
    runner_label = escape(str(session.get("model") or session.get("player_name") or "—"))
    body = (
        f"Session ID : {escape(str(session.get('session_id', '—')))}\n"
        f"Runner     : {runner} ({runner_label})\n"
        f"Seed       : {escape(str(session.get('seed', '—')))}  |  "
        f"Difficulty : {escape(str(session.get('difficulty', '—')))}\n"
        f"Outcome    : {escape(str(session.get('outcome', '—')))}"
    )
    console.print(Panel(body, title="[bold]CipherBench Session Inspector[/bold]"))

    # D-04: Attempt table
    table = Table(title="Attempt Trace", show_header=True, header_style="bold")
    table.add_column("Attempt", justify="right", min_width=8)
    table.add_column("Probe", min_width=8)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Correct?", justify="center", min_width=9)

    entries = sorted(
        session.get("attempts", []),
        key=lambda e: e.get("attempt_num", 0),
    )
    for entry in entries:
        if entry.get("extraction_failed"):
            # D-05: extraction failures shown, not hidden
            table.add_row(
                str(entry.get("attempt_num", "?")),
                "— (extraction failed)",
                "—",
                "✗",
                style="red",
            )
        else:
            score = entry.get("score")
            max_score = entry.get("max_score", "?")
            score_str = f"{score}/{max_score}" if score is not None else "—"
            is_correct = entry.get("is_correct", False)
            table.add_row(
                str(entry.get("attempt_num", "?")),
                escape(entry.get("probe") or "—"),
                score_str,
                "✓" if is_correct else "✗",
                style="green" if is_correct else None,
            )

    console.print(table)

    # D-06: Footer — final_answer and outcome
    final_answer = session.get("final_answer")
    outcome = session.get("outcome", "unknown")
    if final_answer is None:
        footer = "Final answer: — (not reached)"
    else:
        outcome_symbol = "✓" if outcome == "success" else "✗"
        outcome_label = outcome.capitalize()
        footer = f"Final answer: {final_answer} — {outcome_symbol} {outcome_label}"
    console.print(footer)
