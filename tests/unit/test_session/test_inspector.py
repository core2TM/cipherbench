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
    """Capture display_session Rich output via injected console parameter.

    Returns the captured string output.
    """
    from rich.console import Console

    captured = io.StringIO()
    mock_console = Console(file=captured, force_terminal=False, width=120)
    # monkeypatch not needed — display_session uses injected console parameter only
    display_session(session, mock_console)
    return captured.getvalue()


# ---------------------------------------------------------------------------
# 12 test stubs — SESS-03-A through SESS-03-L
# ---------------------------------------------------------------------------


def test_display_session_shows_all_attempts(monkeypatch):
    """SESS-03-A: display_session renders all attempt rows in the table (D-03)."""
    session = _make_session("failure", attempts_used=3)
    output = _capture_display_session(session, monkeypatch)
    # Table title is present
    assert "Attempt Trace" in output
    # All 3 attempt numbers appear
    assert "1" in output
    assert "2" in output
    assert "3" in output
    # Column headers
    assert "Attempt" in output
    assert "Probe" in output
    assert "Score" in output
    assert "Correct?" in output


def test_display_extraction_failure_row(monkeypatch):
    """SESS-03-B: extraction-failure attempts render as [extraction failed] with score — (D-04)."""
    session = _make_session("failure", attempts_used=1, extraction_failures=1)
    output = _capture_display_session(session, monkeypatch)
    # D-05: extraction failure row markers
    assert "(extraction failed)" in output
    # em-dash for score
    assert "—" in output


def test_display_footer_success(monkeypatch):
    """SESS-03-C: footer shows outcome=success and final_answer when session succeeded (D-05)."""
    session = _make_session("success", attempts_used=2, final_answer="AAAAA")
    output = _capture_display_session(session, monkeypatch)
    # D-06: footer with final_answer and outcome
    assert "Final answer" in output
    assert "AAAAA" in output
    assert "Success" in output
    assert "✓" in output


def test_display_footer_not_reached(monkeypatch):
    """SESS-03-D: footer shows 'Final answer not reached' when final_answer is None (D-06)."""
    session = _make_session("failure", attempts_used=2, final_answer=None)
    output = _capture_display_session(session, monkeypatch)
    # D-06: not reached path
    assert "Final answer" in output
    assert "(not reached)" in output


def test_inspect_substring_match(tmp_sessions_dir):
    """SESS-03-E: inspect_session resolves session by partial substring of filename stem (D-01)."""
    session_id = "20260529T143022-alice-test"
    _write_session(tmp_sessions_dir, session_id, _make_session("success", 2))
    result = CliRunner().invoke(app, ["inspect", "alice", "--sessions-dir", str(tmp_sessions_dir)])
    assert result.exit_code == 0


def test_inspect_case_insensitive(tmp_sessions_dir):
    """SESS-03-F: inspect_session resolves session case-insensitively (D-01)."""
    session_id = "20260529T000000-UPPER"
    _write_session(tmp_sessions_dir, session_id, _make_session("success", 2))
    result = CliRunner().invoke(app, ["inspect", "upper", "--sessions-dir", str(tmp_sessions_dir)])
    assert result.exit_code == 0


def test_inspect_not_found(tmp_sessions_dir):
    """SESS-03-G: inspect_session exits 1 and lists available sessions when ID not found (D-08)."""
    _write_session(tmp_sessions_dir, "20260529T000000-test", _make_session("success", 2))
    result = CliRunner().invoke(app, ["inspect", "zzz-nomatch", "--sessions-dir", str(tmp_sessions_dir)])
    assert result.exit_code == 1
    assert "Session not found" in result.output


def test_inspect_ambiguous(tmp_sessions_dir):
    """SESS-03-H: inspect_session exits 1 and prints list of matches when ambiguous (D-02)."""
    _write_session(tmp_sessions_dir, "20260529T000000-shared-a", _make_session("success", 2))
    _write_session(tmp_sessions_dir, "20260529T000001-shared-b", _make_session("failure", 3))
    result = CliRunner().invoke(app, ["inspect", "shared", "--sessions-dir", str(tmp_sessions_dir)])
    assert result.exit_code == 1
    assert "Ambiguous" in result.output


def test_inspect_missing_dir(tmp_sessions_dir):
    """SESS-03-I: inspect_session exits 1 with descriptive error when sessions_dir missing (D-09)."""
    missing = tmp_sessions_dir / "nonexistent"
    result = CliRunner().invoke(app, ["inspect", "any", "--sessions-dir", str(missing)])
    assert result.exit_code == 1
    assert "Sessions directory not found" in result.output


def test_inspect_empty_dir(tmp_sessions_dir):
    """SESS-03-J: inspect_session exits 1 with descriptive error when sessions_dir is empty (D-10)."""
    tmp_sessions_dir.mkdir(parents=True, exist_ok=True)
    result = CliRunner().invoke(app, ["inspect", "any", "--sessions-dir", str(tmp_sessions_dir)])
    assert result.exit_code == 1
    assert "No sessions found" in result.output


def test_inspect_command_help():
    """SESS-03-K: `cipherbench inspect --help` exits 0 and shows session-id argument."""
    result = CliRunner().invoke(app, ["inspect", "--help"])
    assert result.exit_code == 0
    assert "--sessions-dir" in result.output


def test_inspect_schema_parity(monkeypatch):
    """SESS-03-L: display_session renders human sessions identically to model sessions (D-07)."""
    model_session = _make_session("success", 2)
    human_session = dict(
        _make_session("success", 2),
        runner_type="human",
        player_name="Alice",
        model=None,
    )
    model_output = _capture_display_session(model_session, monkeypatch)
    human_output = _capture_display_session(human_session, monkeypatch)
    # Both outputs must contain the same column headers
    for header in ("Attempt", "Probe", "Score", "Correct?"):
        assert header in model_output, f"Column '{header}' missing from model session output"
        assert header in human_output, f"Column '{header}' missing from human session output"
    # Both must show the table title
    assert "Attempt Trace" in model_output
    assert "Attempt Trace" in human_output
