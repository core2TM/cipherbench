"""CipherBench human session runner — interactive CLI probe loop for human baseline
recording (SESS-02).

Public names:
  HumanSessionRunner  — drives the interactive attempt loop; call .run() -> dict
  create_human_session — factory: builds puzzle, engine, writer, and runner

Design decisions implemented here:
  D-05  Human re-prompt on invalid input (does not raise; loop until valid)
  D-07  runner_type='human' in session record
  D-08  raw_response=None for all human attempt entries
  D-15  Rich terminal display: Panel header, attempt history table, colored score lines
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cipherbench.puzzle import generate_puzzle, get_tier
from cipherbench.types import DifficultyConfig
from cipherbench.session.writer import SessionWriter, slugify_model, make_session_id

logger = logging.getLogger(__name__)

_console = Console()

MAX_ATTEMPTS: int = 5  # Fixed at 5 — a core mechanic, not configurable in v1


# ---------------------------------------------------------------------------
# Module-private Rich display helpers (D-15)
# ---------------------------------------------------------------------------


def _show_puzzle_header(seed: int, difficulty_name: str, alphabet: str, output_length: int) -> None:
    """Print Rich Panel with puzzle metadata (D-15).

    Parameters
    ----------
    seed : int
        RNG seed for the puzzle.
    difficulty_name : str
        Tier name, e.g. 'easy', 'medium', 'hard'.
    alphabet : str
        Character set used for probes and answers.
    output_length : int
        Length of each probe and answer string.
    """
    body = (
        f"Seed: {seed}\n"
        f"Difficulty: {difficulty_name}\n"
        f"Alphabet: {alphabet}\n\n"
        f"PROBE: submit as  PROBE: {'X' * output_length}\n"
        f"ANSWER: submit as  ANSWER: {'X' * output_length}"
    )
    _console.print(Panel(body, title="[bold]CipherBench[/bold]"))


def _show_attempt_history(attempts: list[dict], max_score: int) -> None:
    """Print a Rich Table with attempt history (D-15).

    Rows are colored: green if is_correct, yellow if score > 0, red if score == 0.
    Empty table is printed if no attempts have been made yet.

    Parameters
    ----------
    attempts : list[dict]
        List of AttemptEntry dicts from the session record.
    max_score : int
        Maximum score per attempt (equals output_length).
    """
    table = Table(title="Attempt History", show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Probe", min_width=8)
    table.add_column("Score", min_width=8)

    for a in attempts:
        probe_str = a.get("probe") or "INVALID"
        score = a.get("score")
        is_correct = a.get("is_correct", False)

        if score is None:
            score_str = "N/A"
            row_style = "red"
        elif is_correct:
            score_str = f"[green]{score}/{max_score}[/green]"
            row_style = "green"
        elif score > 0:
            score_str = f"[yellow]{score}/{max_score}[/yellow]"
            row_style = "yellow"
        else:
            score_str = f"[red]{score}/{max_score}[/red]"
            row_style = "red"

        table.add_row(str(a["attempt_num"]), probe_str, score_str, style=row_style if not is_correct else None)

    _console.print(table)


def _show_score_line(score: int, max_score: int, is_correct: bool) -> None:
    """Print a single colored score feedback line (D-15).

    Parameters
    ----------
    score : int
        Score for the most recent attempt.
    max_score : int
        Maximum possible score.
    is_correct : bool
        True if the probe matched the cipher output exactly.
    """
    if is_correct:
        _console.print("[green]Correct![/green]")
    elif score > 0:
        _console.print(f"[yellow]Score: {score}/{max_score}[/yellow]")
    else:
        _console.print(f"[red]Score: {score}/{max_score}[/red]")


def _validate_probe(probe: str, alphabet: str, output_length: int) -> bool:
    """Return True if probe has the right length and all chars are in the alphabet.

    Parameters
    ----------
    probe : str
        Candidate probe string (already stripped and uppercased).
    alphabet : str
        Valid character set for the puzzle.
    output_length : int
        Expected length of the probe.

    Returns
    -------
    bool
        True if valid, False if invalid.
    """
    return len(probe) == output_length and all(c in alphabet for c in probe)


# ---------------------------------------------------------------------------
# HumanSessionRunner
# ---------------------------------------------------------------------------


class HumanSessionRunner:
    """Drives the interactive probe-attempt loop for a human benchmark session (SESS-02).

    Do not instantiate directly — use :func:`create_human_session`.

    Private attributes (single-underscore convention):
      _puzzle         : Puzzle
      _engine         : RuleEngine  — fresh per session, never reused
      _writer         : SessionWriter
      _session_record : dict        — mutable session state; mutated in-place by run()
    """

    def __init__(self, puzzle, engine, writer: SessionWriter, session_record: dict) -> None:
        self._puzzle = puzzle
        self._engine = engine
        self._writer = writer
        self._session_record = session_record

    def run(self) -> dict:
        """Execute the interactive probe loop and return the final session record.

        Loop behavior
        -------------
        - Valid input is collected via typer.prompt with re-prompt on invalid input (D-05)
        - write_checkpoint is called after every valid attempt (D-17)
        - Rich Panel, attempt history table, and colored score lines shown per D-15
        - Session finalizes after correct answer or all 5 attempts exhausted

        Returns
        -------
        dict
            The final session_record with all D-11 fields.
        """
        alphabet = self._puzzle.difficulty.alphabet
        output_length = self._puzzle.difficulty.output_length
        max_score = output_length

        _show_puzzle_header(
            self._puzzle.seed,
            get_tier(self._puzzle.difficulty),
            alphabet,
            output_length,
        )

        valid_attempts: int = 0

        while valid_attempts < MAX_ATTEMPTS:
            # Show attempt history before each probe (empty table on first attempt)
            _show_attempt_history(self._session_record["attempts"], max_score)

            # Input validation loop — re-prompt until valid (D-05)
            raw = typer.prompt(f"Probe {valid_attempts + 1}/{MAX_ATTEMPTS}").strip().upper()
            while not _validate_probe(raw, alphabet, output_length):
                _console.print(
                    f"[red]Invalid: must be {output_length} chars from alphabet '{alphabet}'[/red]"
                )
                raw = typer.prompt(f"Probe {valid_attempts + 1}/{MAX_ATTEMPTS}").strip().upper()

            attempt_score = self._engine.score_attempt(raw)

            entry: dict = {
                "attempt_num": len(self._session_record["attempts"]) + 1,
                "probe": raw,
                "score": attempt_score.score,
                "max_score": max_score,
                "is_correct": attempt_score.is_correct,
                "raw_response": None,  # D-08: always None for human sessions
                "extraction_failed": False,
            }
            self._session_record["attempts"].append(entry)
            self._writer.write_checkpoint(self._session_record)

            _show_score_line(attempt_score.score, max_score, attempt_score.is_correct)

            valid_attempts += 1
            if attempt_score.is_correct:
                break

        # Final answer step — only if no correct probe found
        raw_ans_clean: Optional[str] = None
        if not any(a["is_correct"] for a in self._session_record["attempts"]):
            _console.print(
                f"\nYou have used all your probe attempts.\n"
                f"Submit your final answer as: ANSWER: {'X' * output_length}"
            )
            raw_ans = typer.prompt("Submit final answer (ANSWER: XXXXX)").strip().upper()

            # Strip leading "ANSWER:" prefix if present
            if raw_ans.startswith("ANSWER:"):
                raw_ans = raw_ans[len("ANSWER:"):].strip()

            # Validate; re-prompt once if invalid
            if not _validate_probe(raw_ans, alphabet, output_length):
                _console.print(
                    f"[red]Invalid: must be {output_length} chars from alphabet '{alphabet}'[/red]"
                )
                raw_ans = typer.prompt("Submit final answer (ANSWER: XXXXX)").strip().upper()
                if raw_ans.startswith("ANSWER:"):
                    raw_ans = raw_ans[len("ANSWER:"):].strip()

            raw_ans_clean = raw_ans if _validate_probe(raw_ans, alphabet, output_length) else None

        outcome = (
            "success"
            if any(a["is_correct"] for a in self._session_record["attempts"])
            else "failure"
        )
        self._writer.finalize(self._session_record, outcome, final_answer=raw_ans_clean)
        return self._session_record


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_human_session(
    seed: Optional[int],
    difficulty: DifficultyConfig,
    player_name: str,
    output_dir: Path | str,
) -> HumanSessionRunner:
    """Build a fresh :class:`HumanSessionRunner` for a new human benchmark session.

    Parameters
    ----------
    seed : int or None
        RNG seed for puzzle generation.  ``None`` generates a random seed using
        an isolated ``random.Random()`` instance (never touches global state, D-11).
    difficulty : DifficultyConfig
        Difficulty preset (EASY, MEDIUM, HARD, or custom).
    player_name : str
        Human player name stored in the session JSON (D-13).
    output_dir : Path or str
        Directory for session JSON files (D-10).

    Returns
    -------
    HumanSessionRunner
        A fully initialised runner with the session ``in_progress`` file already
        written to disk (D-17).
    """
    output_dir = Path(output_dir)

    # RNG isolation: never call global random.seed() (D-11)
    if seed is None:
        seed = random.Random().randint(0, 2**32 - 1)

    player_slug = slugify_model(player_name)
    human_slug = f"human-{player_slug}"

    # Build session ID following D-06: {YYYYMMDD}T{HHMMSS}-human-{player-name}
    session_id = make_session_id(human_slug, output_dir)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    puzzle = generate_puzzle(seed, difficulty)
    engine = puzzle.create_engine()

    session_record: dict = {
        "session_id": session_id,
        "runner_type": "human",
        "model": None,
        "player_name": player_name,
        "seed": seed,
        "difficulty": get_tier(difficulty),
        "puzzle_hash": puzzle.puzzle_hash,
        "outcome": "in_progress",
        "final_answer": None,
        "attempts": [],
        "created_at": now_iso,
        "completed_at": None,
    }

    writer = SessionWriter(output_dir, session_id)
    writer.init_session(session_record)

    return HumanSessionRunner(puzzle, engine, writer, session_record)
