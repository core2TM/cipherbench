"""CLI integration tests using Typer CliRunner — SESS-01, SESS-02."""
from __future__ import annotations

import pytest

# Guard: skip entire module if cli.app not yet implemented
pytest.importorskip("cipherbench.cli.app")
from typer.testing import CliRunner  # noqa: E402  (after importorskip)


# ---------------------------------------------------------------------------
# cipherbench run subcommand
# ---------------------------------------------------------------------------


def test_run_command_help_exits_zero():
    """cipherbench run --help exits with code 0."""
    pytest.fail("not implemented")


def test_run_command_shows_model_flag():
    """cipherbench run --help output includes --model flag description."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# cipherbench play subcommand
# ---------------------------------------------------------------------------


def test_play_command_help_exits_zero():
    """cipherbench play --help exits with code 0."""
    pytest.fail("not implemented")


def test_play_command_shows_player_name_flag():
    """cipherbench play --help output includes --player-name flag description."""
    pytest.fail("not implemented")
