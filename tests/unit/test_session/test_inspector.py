"""Unit tests for session inspector — display and inspect commands (SESS-03-A through SESS-03-L).

Wave 0 stubs: all 12 tests are SKIPPED until Plan 02 implements the bodies.
"""
from __future__ import annotations

import io
import json

import pytest

inspector_mod = pytest.importorskip("cipherbench.session.inspector")
inspect_session = inspector_mod.inspect_session
display_session = inspector_mod.display_session

_cli_mod = pytest.importorskip("cipherbench.cli.app")
from typer.testing import CliRunner  # noqa: E402
from cipherbench.cli.app import app  # noqa: E402


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_session(
    outcome: str,
    attempts_used: int,
    extraction_failures: int = 0,
    difficulty: str = "easy",
    final_answer: str | None = None,
) -> dict:
    """Build a minimal SessionRecord dict for unit testing inspector display.

    Extends the test_reporter.py factory with a final_answer parameter for
    D-06 footer tests.
    """
    attempts = []
    for i in range(extraction_failures):
        attempts.append(
            {
                "attempt_num": i + 1,
                "probe": None,
                "score": None,
                "max_score": 5,
                "is_correct": False,
                "raw_response": "invalid",
                "extraction_failed": True,
            }
        )
    for i in range(attempts_used):
        attempts.append(
            {
                "attempt_num": extraction_failures + i + 1,
                "probe": "AAAAA",
                "score": 0,
                "max_score": 5,
                "is_correct": (outcome == "success" and i == attempts_used - 1),
                "raw_response": "PROBE: AAAAA",
                "extraction_failed": False,
            }
        )
    return {
        "session_id": "test-session",
        "runner_type": "model",
        "model": "test/model",
        "player_name": None,
        "seed": 42,
        "difficulty": difficulty,
        "puzzle_hash": "abc123",
        "outcome": outcome,
        "final_answer": final_answer,
        "attempts": attempts,
        "created_at": "2026-05-29T00:00:00Z",
        "completed_at": "2026-05-29T00:01:00Z",
    }


def _write_session(tmp_dir, session_id: str, session: dict) -> None:
    """Write a session dict as a JSON file under tmp_dir."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / f"{session_id}.json").write_text(json.dumps(session))


def _capture_display_session(session: dict, monkeypatch) -> str:
    """Capture display_session Rich output by patching _console.

    Returns the captured string output.
    """
    from rich.console import Console

    captured = io.StringIO()
    mock_console = Console(file=captured, force_terminal=False, width=120)
    monkeypatch.setattr(inspector_mod, "_console", mock_console)
    display_session(session, mock_console)
    return captured.getvalue()


# ---------------------------------------------------------------------------
# 12 test stubs — SESS-03-A through SESS-03-L
# ---------------------------------------------------------------------------


def test_display_session_shows_all_attempts(monkeypatch):
    """SESS-03-A: display_session renders all attempt rows in the table (D-03)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_display_extraction_failure_row(monkeypatch):
    """SESS-03-B: extraction-failure attempts render as [extraction failed] with score — (D-04)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_display_footer_success(monkeypatch):
    """SESS-03-C: footer shows outcome=success and final_answer when session succeeded (D-05)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_display_footer_not_reached(monkeypatch):
    """SESS-03-D: footer shows 'Final answer not reached' when final_answer is None (D-06)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_substring_match(tmp_sessions_dir):
    """SESS-03-E: inspect_session resolves session by partial substring of filename stem (D-01)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_case_insensitive(tmp_sessions_dir):
    """SESS-03-F: inspect_session resolves session case-insensitively (D-01)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_not_found(tmp_sessions_dir):
    """SESS-03-G: inspect_session exits 1 and lists available sessions when ID not found (D-08)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_ambiguous(tmp_sessions_dir):
    """SESS-03-H: inspect_session exits 1 and prints list of matches when ambiguous (D-02)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_missing_dir(tmp_sessions_dir):
    """SESS-03-I: inspect_session exits 1 with descriptive error when sessions_dir missing (D-09)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_empty_dir(tmp_sessions_dir):
    """SESS-03-J: inspect_session exits 1 with descriptive error when sessions_dir is empty (D-10)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_command_help():
    """SESS-03-K: `cipherbench inspect --help` exits 0 and shows session-id argument."""
    pytest.skip("Wave 0 stub — implement in Plan 02")


def test_inspect_schema_parity(monkeypatch):
    """SESS-03-L: display_session renders human sessions identically to model sessions (D-07)."""
    pytest.skip("Wave 0 stub — implement in Plan 02")
