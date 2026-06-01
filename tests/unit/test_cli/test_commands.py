"""CLI integration tests using Typer CliRunner — SESS-01, SESS-02."""
from __future__ import annotations

import pytest

# Guard: skip entire module if cli.app not yet implemented
pytest.importorskip("cipherbench.cli.app")
from typer.testing import CliRunner  # noqa: E402  (after importorskip)
from cipherbench.cli.app import app  # noqa: E402


# ---------------------------------------------------------------------------
# cipherbench run subcommand — SESS-01, D-12
# ---------------------------------------------------------------------------


def test_run_command_help_exits_zero():
    """cipherbench run --help exits with code 0."""
    result = CliRunner().invoke(app, ["run", "--help"])
    assert result.exit_code == 0


def test_run_command_shows_model_flag():
    """cipherbench run --help output includes --model flag description."""
    result = CliRunner().invoke(app, ["run", "--help"])
    assert "--model" in result.output


def test_run_command_shows_seed_flag():
    """cipherbench run --help output includes --seed flag."""
    result = CliRunner().invoke(app, ["run", "--help"])
    assert "--seed" in result.output


# ---------------------------------------------------------------------------
# cipherbench play subcommand — SESS-02, D-13
# ---------------------------------------------------------------------------


def test_play_command_help_exits_zero():
    """cipherbench play --help exits with code 0."""
    result = CliRunner().invoke(app, ["play", "--help"])
    assert result.exit_code == 0


def test_play_command_shows_player_name_flag():
    """cipherbench play --help output includes --player-name flag description."""
    result = CliRunner().invoke(app, ["play", "--help"])
    assert "--player-name" in result.output


def test_play_command_shows_seed_flag():
    """cipherbench play --help output includes --seed flag."""
    result = CliRunner().invoke(app, ["play", "--help"])
    assert "--seed" in result.output



def test_play_command_shows_length_flag():
    """cipherbench play --help output includes --length flag (w7g)."""
    result = CliRunner().invoke(app, ["play", "--help"])
    assert "--length" in result.output
