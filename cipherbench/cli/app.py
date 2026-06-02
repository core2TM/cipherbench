"""CipherBench CLI entry point — wires `run`, `play`, `score`, and `inspect` subcommands.

No business logic here — this module is a coordinator that delegates to session runners.

Public names:
  app  — Typer application with subcommands

Design:
  Puzzles have 3 fixed levels (1, 2, 3). No seed or difficulty flags.
  --level selects which of the 3 fixed cipher challenges to run.
"""
from pathlib import Path
from typing import Annotated, Optional

import typer

from cipherbench.puzzle import get_ground_truth, ALPHABET, LEVEL_CONFIGS
from cipherbench.session.model_runner import create_model_session
from cipherbench.session.human_runner import create_human_session
from cipherbench.adapters.litellm_adapter import LiteLLMAdapter


app = typer.Typer(name="cipherbench", help="CipherBench — AGI Proximity Benchmark.")


# ---------------------------------------------------------------------------
# `cipherbench run` — LLM benchmark session
# ---------------------------------------------------------------------------


@app.command(name="run")
def run_command(
    model: Annotated[str, typer.Option("--model", help="LiteLLM model string, e.g. anthropic/claude-opus-4-7")],
    level: Annotated[int, typer.Option("--level", help="Puzzle level: 1 (easiest), 2, or 3")] = 1,
    num_puzzles: Annotated[int, typer.Option("--num-puzzles", help="Number of sessions to run")] = 1,
    output_dir: Annotated[str, typer.Option("--output-dir", help="Directory to write session JSON files")] = "./sessions",
    api_base: Annotated[Optional[str], typer.Option("--api-base", help="Base URL for LiteLLM proxy server")] = None,
) -> None:
    """Run a model benchmark session on a cipher puzzle."""
    if level not in (1, 2, 3):
        typer.echo("Error: --level must be 1, 2, or 3", err=True)
        raise typer.Exit(code=1)
    if num_puzzles < 1:
        typer.echo("Error: --num-puzzles must be >= 1", err=True)
        raise typer.Exit(code=1)

    ground_truth = get_ground_truth(level)
    typer.echo(f"Level {level} | Target: {ground_truth} | Alphabet: {ALPHABET}")

    out_path = Path(output_dir)
    current_run_sessions: list[dict] = []

    for run_idx in range(num_puzzles):
        adapter = LiteLLMAdapter(model, api_base=api_base)
        runner = create_model_session(level, adapter, out_path)
        session_record = runner.run()
        current_run_sessions.append(session_record)
        typer.echo(
            f"Run {run_idx + 1}/{num_puzzles}: level={level} outcome={session_record['outcome']}"
        )

    from cipherbench.scoring.scorer import load_sessions as _load_sessions
    from cipherbench.scoring.reporter import render_live_summary as _render_live_summary
    human_baseline = _load_sessions(out_path, runner_type="human")
    _render_live_summary(current_run_sessions, human_baseline)


# ---------------------------------------------------------------------------
# `cipherbench run-all` — run all 3 levels sequentially
# ---------------------------------------------------------------------------


@app.command(name="run-all")
def run_all_command(
    model: Annotated[str, typer.Option("--model", help="LiteLLM model string, e.g. anthropic/claude-opus-4-7")],
    num_puzzles: Annotated[int, typer.Option("--num-puzzles", help="Number of sessions per level")] = 1,
    output_dir: Annotated[str, typer.Option("--output-dir", help="Directory to write session JSON files")] = "./sessions",
    api_base: Annotated[Optional[str], typer.Option("--api-base", help="Base URL for LiteLLM proxy server")] = None,
) -> None:
    """Run a model through all 3 levels sequentially and print a combined summary."""
    from cipherbench.scoring.scorer import load_sessions as _load_sessions
    from cipherbench.scoring.reporter import render_live_summary as _render_live_summary

    out_path = Path(output_dir)
    all_sessions: list[dict] = []

    for level in sorted(LEVEL_CONFIGS):
        ground_truth = get_ground_truth(level)
        typer.echo(f"\n── Level {level} | Target: {ground_truth} | Alphabet: {ALPHABET} ──")

        for run_idx in range(num_puzzles):
            adapter = LiteLLMAdapter(model, api_base=api_base)
            runner = create_model_session(level, adapter, out_path)
            session_record = runner.run()
            all_sessions.append(session_record)
            typer.echo(
                f"  Run {run_idx + 1}/{num_puzzles}: outcome={session_record['outcome']}"
            )

    typer.echo("\n── Combined Results ──")
    human_baseline = _load_sessions(out_path, runner_type="human")
    _render_live_summary(all_sessions, human_baseline)


# ---------------------------------------------------------------------------
# `cipherbench play` — human interactive session, all 3 levels
# ---------------------------------------------------------------------------


@app.command(name="play")
def play_command(
    player_name: Annotated[str, typer.Option("--player-name", help="Player name stored in session JSON")] = "human",
    output_dir: Annotated[str, typer.Option("--output-dir", help="Directory to write session JSON files")] = "./sessions",
) -> None:
    """Play all 3 cipher levels interactively as a human, one after another."""
    out_path = Path(output_dir)
    results: list[dict] = []

    for level in sorted(LEVEL_CONFIGS):
        typer.echo(f"\n── Level {level} of {len(LEVEL_CONFIGS)} ──")
        runner = create_human_session(level, player_name, out_path)
        session_record = runner.run()
        results.append(session_record)
        outcome = session_record["outcome"]
        typer.echo(f"Level {level} complete: {outcome}")
        if level < len(LEVEL_CONFIGS):
            typer.confirm("Continue to next level?", default=True, abort=True)

    typer.echo("\n── Final Results ──")
    for r in results:
        typer.echo(f"  Level {r['level']}: {r['outcome']}")


# ---------------------------------------------------------------------------
# `cipherbench score` — scoring report
# ---------------------------------------------------------------------------


@app.command(name="score")
def score_command(
    model: Annotated[Optional[str], typer.Option("--model", help="LiteLLM model string to score")] = None,
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
    level: Annotated[Optional[int], typer.Option("--level", help="Filter by puzzle level (1, 2, or 3)")] = None,
    output_file: Annotated[Optional[str], typer.Option("--output-file", help="Write JSON report to this path")] = None,
    human: Annotated[bool, typer.Option("--human/--no-human", help="Score human sessions instead of model sessions")] = False,
) -> None:
    """Compute scoring report for a model or human player."""
    from cipherbench.scoring.scorer import load_sessions, compute_report
    from cipherbench.scoring.reporter import render_score_report
    from cipherbench.scoring.report_writer import write_json_report

    runner_type = "human" if human else "model"
    sessions_path = Path(sessions_dir).resolve()
    level_filter = str(level) if level is not None else None

    model_sessions = load_sessions(sessions_path, runner_type=runner_type, model=model, difficulty=level_filter)
    human_sessions = load_sessions(sessions_path, runner_type="human", difficulty=level_filter) if not human else []

    if not model_sessions:
        typer.echo("No terminal sessions found matching the given filters.", err=True)
        raise typer.Exit(code=1)

    report = compute_report(model_sessions, human_sessions, model_str=model)
    label = model if model is not None else ("human" if human else "(all models)")
    render_score_report(report, model=label)

    if output_file:
        resolved_output = Path(output_file).resolve()
        try:
            write_json_report(report, resolved_output)
        except OSError as exc:
            typer.echo(f"Error: could not write report: {exc}", err=True)
            raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# `cipherbench inspect` — session replay
# ---------------------------------------------------------------------------


@app.command(name="inspect")
def inspect_command(
    session_id: Annotated[str, typer.Argument(help="Session ID or substring to match")],
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
) -> None:
    """Replay a stored session trace, displaying all probe attempts and final outcome."""
    from cipherbench.session.inspector import inspect_session, InspectorError
    from rich.console import Console

    resolved = Path(sessions_dir).resolve()
    try:
        inspect_session(session_id, resolved, Console())
    except InspectorError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Entry point guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
