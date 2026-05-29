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

    for puzzle_idx in range(num_puzzles):
        # RNG isolation: isolated random.Random() per puzzle (D-11, GEN-04)
        puzzle_seed = seed if seed is not None else random.Random().randint(0, 2**32 - 1)

        for run_idx in range(runs_per_puzzle):
            adapter = LiteLLMAdapter(model, litellm_config_path=litellm_config)
            runner = create_model_session(puzzle_seed, config, adapter, out_path)
            session_record = runner.run()
            typer.echo(
                f"Puzzle {puzzle_idx + 1}/{num_puzzles} Run {run_idx + 1}/{runs_per_puzzle}: "
                f"seed={puzzle_seed} outcome={session_record['outcome']}"
            )


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
# Entry point guard
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
