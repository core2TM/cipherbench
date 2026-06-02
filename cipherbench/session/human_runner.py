"""CipherBench human session runner — interactive CLI probe loop for human baseline
recording.

Public names:
  HumanSessionRunner  — drives the interactive attempt loop; call .run() -> dict
  create_human_session — factory: builds engine, writer, and runner

The ground_truth (cipher target) is shown to the player at session start.
After each probe the player sees their encoded output alongside the score.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cipherbench.engine.layers import apply_cipher
from cipherbench.puzzle import (
    ALPHABET,
    LEVEL_CONFIGS,
    OUTPUT_LENGTH,
    create_engine_for_level,
    get_ground_truth,
    get_max_attempts,
)
from cipherbench.session.writer import SessionWriter, slugify_model, make_session_id

logger = logging.getLogger(__name__)

_console = Console()


# ---------------------------------------------------------------------------
# Module-private Rich display helpers
# ---------------------------------------------------------------------------


def _show_puzzle_header(level: int, ground_truth: str, alphabet: str, output_length: int) -> None:
    """Print Rich Panel with puzzle info and the target encoding."""
    body = (
        f"Level: {level}\n"
        f"Target: [bold cyan]{ground_truth}[/bold cyan]\n"
        f"Alphabet: {alphabet}\n\n"
        f"Find the input whose encoded output matches the target exactly.\n\n"
        f"PROBE:  submit as  PROBE: {'X' * output_length}\n"
        f"ANSWER: submit as  ANSWER: {'X' * output_length}"
    )
    _console.print(Panel(body, title=f"[bold]CipherBench — Level {level}[/bold]"))


def _show_attempt_history(attempts: list[dict], max_score: int) -> None:
    """Print a Rich Table with attempt history including encoded output."""
    table = Table(title="Attempt History", show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Probe", min_width=8)
    table.add_column("Encoded", min_width=8)
    table.add_column("Score", min_width=8)
    for a in attempts:
        probe_str = a.get("probe") or "INVALID"
        encoded_str = a.get("encoded_output") or "N/A"
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

        table.add_row(
            str(a["attempt_num"]),
            probe_str,
            encoded_str,
            score_str,
            style=row_style if not is_correct else None,
        )

    _console.print(table)


def _show_score_line(score: int, max_score: int, is_correct: bool, encoded: str) -> None:
    if is_correct:
        _console.print(f"[green]Correct! Encoded: {encoded}[/green]")
    elif score > 0:
        _console.print(f"[yellow]Score: {score}/{max_score}  Encoded: {encoded}[/yellow]")
    else:
        _console.print(f"[red]Score: {score}/{max_score}  Encoded: {encoded}[/red]")


def _validate_probe(probe: str, alphabet: str, output_length: int) -> bool:
    """Return True if probe has the right length and all chars are in the alphabet."""
    return len(probe) == output_length and all(c in alphabet for c in probe)


# ---------------------------------------------------------------------------
# HumanSessionRunner
# ---------------------------------------------------------------------------


class HumanSessionRunner:
    """Drives the interactive probe-attempt loop for a human benchmark session.

    Do not instantiate directly — use :func:`create_human_session`.
    """

    def __init__(
        self,
        level: int,
        ground_truth: str,
        engine,
        writer: SessionWriter,
        session_record: dict,
        max_attempts: int = 5,
    ) -> None:
        self._level = level
        self._ground_truth = ground_truth
        self._engine = engine
        self._writer = writer
        self._session_record = session_record
        self._max_attempts = max_attempts

    def run(self) -> dict:
        """Execute the interactive probe loop and return the final session record.

        Returns
        -------
        dict
            The final session_record with all fields.
        """
        alphabet = ALPHABET
        output_length = OUTPUT_LENGTH
        max_score = output_length

        _show_puzzle_header(self._level, self._ground_truth, alphabet, output_length)

        valid_attempts: int = 0

        _show_attempt_history(self._session_record["attempts"], max_score)

        while valid_attempts < self._max_attempts:
            raw = typer.prompt(f"Probe {valid_attempts + 1}/{self._max_attempts}").strip().upper()
            if raw.startswith("PROBE:"):
                raw = raw[len("PROBE:"):].strip()
            while not _validate_probe(raw, alphabet, output_length):
                _console.print(
                    f"[red]Invalid: must be {output_length} chars from alphabet '{alphabet}'[/red]"
                )
                raw = typer.prompt(f"Probe {valid_attempts + 1}/{self._max_attempts}").strip().upper()
                if raw.startswith("PROBE:"):
                    raw = raw[len("PROBE:"):].strip()

            attempt_score = self._engine.score_attempt(raw)

            entry: dict = {
                "attempt_num": len(self._session_record["attempts"]) + 1,
                "probe": raw,
                "encoded_output": attempt_score.encoded_output,
                "score": attempt_score.score,
                "max_score": max_score,
                "is_correct": attempt_score.is_correct,
                "raw_response": None,
                "extraction_failed": False,
                "reason": None,
            }
            self._session_record["attempts"].append(entry)
            self._writer.write_checkpoint(self._session_record)

            _show_attempt_history(self._session_record["attempts"], max_score)

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
            if raw_ans.startswith("ANSWER:"):
                raw_ans = raw_ans[len("ANSWER:"):].strip()

            if not _validate_probe(raw_ans, alphabet, output_length):
                _console.print(
                    f"[red]Invalid: must be {output_length} chars from alphabet '{alphabet}'[/red]"
                )
                raw_ans = typer.prompt("Submit final answer (ANSWER: XXXXX)").strip().upper()
                if raw_ans.startswith("ANSWER:"):
                    raw_ans = raw_ans[len("ANSWER:"):].strip()

            raw_ans_clean = raw_ans if _validate_probe(raw_ans, alphabet, output_length) else None

        answer_is_correct = False
        if raw_ans_clean:
            _, _, substitution = LEVEL_CONFIGS[self._level]
            shifted = apply_cipher(raw_ans_clean, ALPHABET, substitution)
            encoded = "".join(ALPHABET[i] for i in shifted)
            answer_is_correct = (encoded == self._ground_truth)

        outcome = (
            "success"
            if any(a["is_correct"] for a in self._session_record["attempts"]) or answer_is_correct
            else "failure"
        )
        self._writer.finalize(self._session_record, outcome, final_answer=raw_ans_clean)
        return self._session_record


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_human_session(
    level: int,
    player_name: str,
    output_dir: Path | str,
) -> HumanSessionRunner:
    """Build a fresh HumanSessionRunner for a new human benchmark session.

    Parameters
    ----------
    level : int
        Puzzle level: 1, 2, or 3.
    player_name : str
        Human player name stored in the session JSON.
    output_dir : Path or str
        Directory for session JSON files.

    Returns
    -------
    HumanSessionRunner
        A fully initialised runner with the session 'in_progress' file already
        written to disk.
    """
    output_dir = Path(output_dir)
    ground_truth = get_ground_truth(level)
    max_attempts = get_max_attempts(level)
    engine = create_engine_for_level(level)

    player_slug = slugify_model(player_name)
    human_slug = f"human-{player_slug}"
    session_id = make_session_id(human_slug, output_dir)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    session_record: dict = {
        "session_id": session_id,
        "runner_type": "human",
        "model": None,
        "player_name": player_name,
        "level": level,
        "ground_truth": ground_truth,
        "outcome": "in_progress",
        "final_answer": None,
        "final_answer_reason": None,
        "attempts": [],
        "created_at": now_iso,
        "completed_at": None,
    }

    writer = SessionWriter(output_dir, session_id)
    writer.init_session(session_record)

    return HumanSessionRunner(level, ground_truth, engine, writer, session_record, max_attempts=max_attempts)
