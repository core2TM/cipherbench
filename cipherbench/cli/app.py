"""CipherBench CLI entry point — wires `run` and `play` subcommands (SESS-01, SESS-02, D-12, D-13).

No business logic here — this module is a coordinator that delegates to session runners.

Public names:
  app  — Typer application with `run` and `play` subcommands

Design decisions implemented here:
  D-12  `cipherbench run` flags: --model, --seed, --num-puzzles, --runs-per-puzzle,
        --difficulty, --output-dir, --litellm-config
  D-13  `cipherbench play` flags: --player-name, --seed, --difficulty, --output-dir
  D-14  API keys from env vars — LiteLLM reads standard provider env vars automatically
  D-15  Rich terminal output delegated entirely to HumanSessionRunner
"""
import random
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from cipherbench.puzzle import EASY, MEDIUM, HARD
from cipherbench.types import DifficultyConfig
from cipherbench.session.model_runner import create_model_session
from cipherbench.session.human_runner import create_human_session
from cipherbench.adapters.litellm_adapter import LiteLLMAdapter


# ---------------------------------------------------------------------------
# Difficulty enum and config mapping
# ---------------------------------------------------------------------------


class Difficulty(str, Enum):
    """Difficulty tier for a CipherBench puzzle session."""

    easy = "easy"
    medium = "medium"
    hard = "hard"


def _difficulty_to_config(d: Difficulty) -> DifficultyConfig:
    """Map a Difficulty enum value to the canonical DifficultyConfig preset.

    Parameters
    ----------
    d : Difficulty
        CLI difficulty tier enum value.

    Returns
    -------
    DifficultyConfig
        The EASY, MEDIUM, or HARD preset from cipherbench.puzzle.
    """
    if d == Difficulty.easy:
        return EASY
    if d == Difficulty.medium:
        return MEDIUM
    return HARD


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

app = typer.Typer(name="cipherbench", help="CipherBench — AGI Proximity Benchmark.")


# ---------------------------------------------------------------------------
# `cipherbench run` — D-12 flags
# ---------------------------------------------------------------------------


@app.command(name="run")
def run_command(
    model: Annotated[str, typer.Option("--model", help="LiteLLM model string, e.g. anthropic/claude-opus-4-7")],
    seed: Annotated[Optional[int], typer.Option("--seed", help="RNG seed (default: random)")] = None,
    num_puzzles: Annotated[int, typer.Option("--num-puzzles", help="Number of distinct puzzles to run")] = 1,
    runs_per_puzzle: Annotated[int, typer.Option("--runs-per-puzzle", help="Independent sessions per puzzle")] = 1,
    difficulty: Annotated[Difficulty, typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = Difficulty.medium,
    output_dir: Annotated[str, typer.Option("--output-dir", help="Directory to write session JSON files")] = "./sessions",
    litellm_config: Annotated[Optional[str], typer.Option("--litellm-config", help="Path to LiteLLM config.yaml")] = None,
) -> None:
    """Run a model benchmark session on a cipher puzzle (SESS-01)."""
    if num_puzzles < 1:
        typer.echo("Error: --num-puzzles must be >= 1", err=True)
        raise typer.Exit(code=1)
    if runs_per_puzzle < 1:
        typer.echo("Error: --runs-per-puzzle must be >= 1", err=True)
        raise typer.Exit(code=1)

    config = _difficulty_to_config(difficulty)
    out_path = Path(output_dir)

    # D-01, D-03: collect only current-run sessions (not all historical sessions)
    current_run_sessions: list[dict] = []

    # WR-02: derive per-puzzle seeds from root seed to ensure distinct puzzles when
    # --num-puzzles > 1 and --seed is provided.  random.Random(None) samples the OS
    # entropy source, preserving the non-seeded randomness contract (D-11, GEN-04).
    puzzle_rng = random.Random(seed)

    for puzzle_idx in range(num_puzzles):
        # RNG isolation: derive per-puzzle seed from puzzle_rng (D-11, GEN-04)
        puzzle_seed = puzzle_rng.randint(0, 2**32 - 1)

        for run_idx in range(runs_per_puzzle):
            adapter = LiteLLMAdapter(model, litellm_config_path=litellm_config)
            runner = create_model_session(puzzle_seed, config, adapter, out_path)
            session_record = runner.run()
            current_run_sessions.append(session_record)
            typer.echo(
                f"Puzzle {puzzle_idx + 1}/{num_puzzles} Run {run_idx + 1}/{runs_per_puzzle}: "
                f"seed={puzzle_seed} outcome={session_record['outcome']}"
            )

    # D-01, D-03: live summary after all sessions complete — use current-run sessions only
    from cipherbench.scoring.scorer import load_sessions as _load_sessions
    from cipherbench.scoring.reporter import render_live_summary as _render_live_summary
    human_baseline = _load_sessions(out_path, runner_type="human")
    _render_live_summary(current_run_sessions, human_baseline)


# ---------------------------------------------------------------------------
# `cipherbench play` — D-13 flags
# ---------------------------------------------------------------------------


@app.command(name="play")
def play_command(
    player_name: Annotated[str, typer.Option("--player-name", help="Player name stored in session JSON")] = "human",
    seed: Annotated[Optional[int], typer.Option("--seed", help="RNG seed (default: random)")] = None,
    difficulty: Annotated[Difficulty, typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = Difficulty.medium,
    output_dir: Annotated[str, typer.Option("--output-dir", help="Directory to write session JSON files")] = "./sessions",
) -> None:
    """Play a cipher puzzle interactively as a human (SESS-02)."""
    config = _difficulty_to_config(difficulty)
    out_path = Path(output_dir)

    # RNG isolation: isolated random.Random() for seed generation (D-11)
    play_seed = seed if seed is not None else random.Random().randint(0, 2**32 - 1)

    runner = create_human_session(play_seed, config, player_name, out_path)
    session_record = runner.run()
    typer.echo(
        f"Session complete: seed={play_seed} outcome={session_record['outcome']}"
    )


# ---------------------------------------------------------------------------
# `cipherbench score` — SCORE-01 through SCORE-04 flags (D-02)
# ---------------------------------------------------------------------------


@app.command(name="score")
def score_command(
    model: Annotated[Optional[str], typer.Option("--model", help="LiteLLM model string to score")] = None,
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
    difficulty: Annotated[Optional[Difficulty], typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = None,
    output_file: Annotated[Optional[str], typer.Option("--output-file", help="Write JSON report to this path")] = None,
    human: Annotated[bool, typer.Option("--human/--no-human", help="Score human sessions instead of model sessions")] = False,
) -> None:
    """Compute scoring report for a model or human player (SCORE-01 through SCORE-04). No business logic here — delegates to scorer + reporter + report_writer."""
    from cipherbench.scoring.scorer import load_sessions, compute_report
    from cipherbench.scoring.reporter import render_score_report
    from cipherbench.scoring.report_writer import write_json_report

    runner_type = "human" if human else "model"
    sessions_path = Path(sessions_dir).resolve()  # ASVS V5: resolve prevents path traversal (T-04-06)
    diff_str = difficulty.value if difficulty is not None else None

    model_sessions = load_sessions(sessions_path, runner_type=runner_type, model=model, difficulty=diff_str)
    human_sessions = load_sessions(sessions_path, runner_type="human", difficulty=diff_str) if not human else []

    if not model_sessions:
        typer.echo("No terminal sessions found matching the given filters.", err=True)
        raise typer.Exit(code=1)

    report = compute_report(model_sessions, human_sessions, model_str=model)
    label = model if model is not None else ("human" if human else "(all models)")
    render_score_report(report, model=label)

    if output_file:
        resolved_output = Path(output_file).resolve()  # ASVS V5: resolve prevents path traversal (T-04-06)
        try:
            write_json_report(report, resolved_output)
        except OSError as exc:
            typer.echo(f"Error: could not write report: {exc}", err=True)
            raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# `cipherbench inspect` — SESS-03 session replay
# ---------------------------------------------------------------------------


@app.command(name="inspect")
def inspect_command(
    session_id: Annotated[str, typer.Argument(help="Session ID or substring to match")],
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
) -> None:
    """Replay a stored session trace, displaying all probe attempts and final outcome (SESS-03)."""
    from cipherbench.session.inspector import inspect_session
    from rich.console import Console

    resolved = Path(sessions_dir).resolve()  # ASVS V5: resolve prevents path traversal (T-04-06)
    inspect_session(session_id, resolved, Console())


# ---------------------------------------------------------------------------
# Entry point guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
