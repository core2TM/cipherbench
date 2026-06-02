"""Unit tests for scoring reporter — Rich terminal output (D-11, D-03)."""
from __future__ import annotations

import io
import re

import pytest
import typer

reporter_mod = pytest.importorskip("cipherbench.scoring.reporter")
render_score_report = reporter_mod.render_score_report
render_live_summary = reporter_mod.render_live_summary


def _make_session(outcome: str, attempts_used: int, extraction_failures: int = 0, difficulty: str = "easy") -> dict:
    """Build a minimal SessionRecord dict for unit testing formulas."""
    attempts = []
    for i in range(extraction_failures):
        attempts.append({
            "attempt_num": i + 1,
            "probe": None,
            "score": None,
            "max_score": 5,
            "is_correct": False,
            "raw_response": "invalid",
            "extraction_failed": True,
        })
    for i in range(attempts_used):
        attempts.append({
            "attempt_num": extraction_failures + i + 1,
            "probe": "AAAAA",
            "score": 0,
            "max_score": 5,
            "is_correct": (outcome == "success" and i == attempts_used - 1),
            "raw_response": "PROBE: AAAAA",
            "extraction_failed": False,
        })
    return {
        "session_id": "test-session",
        "runner_type": "model",
        "model": "test/model",
        "player_name": None,
        "seed": 42,
        "difficulty": difficulty,
        "puzzle_hash": "abc123",
        "outcome": outcome,
        "final_answer": None,
        "attempts": attempts,
        "created_at": "2026-05-29T00:00:00Z",
        "completed_at": "2026-05-29T00:01:00Z",
    }


def _make_report(agi_proximity_value=None):
    """Build a minimal ScoreReport for testing."""
    tier_stats = {
        "sessions": 3,
        "success_rate": 0.67,
        "avg_efficiency": 0.6,
        "agi_proximity": agi_proximity_value,
        "avg_probe_efficiency": None,
        "avg_known_info": 10.0,
        "solution_probability": {10: 0.67},
    }
    return {
        "model": "test/model",
        "sessions_scored": 3,
        "by_difficulty": {"easy": dict(tier_stats)},
        "totals": dict(tier_stats),
        "generated_at": "2026-05-29T00:00:00Z",
    }


def _capture_render_score_report(report, model, monkeypatch):
    """Capture render_score_report output by patching _console."""
    from rich.console import Console
    captured = io.StringIO()
    mock_console = Console(file=captured, force_terminal=False, width=120)
    monkeypatch.setattr(reporter_mod, "_console", mock_console)
    render_score_report(report, model)
    return captured.getvalue()


def test_render_score_report_prints_panel(monkeypatch):
    """D-11: output contains model name in panel."""
    report = _make_report()
    output = _capture_render_score_report(report, "test/model", monkeypatch)
    assert "CipherBench Score Report" in output
    assert "test/model" in output


def test_render_score_report_prints_table(monkeypatch):
    """D-11: output contains difficulty tier rows and column headers."""
    report = _make_report()
    output = _capture_render_score_report(report, "test/model", monkeypatch)
    assert "easy" in output
    assert "Sessions" in output


def test_render_score_report_na_hint(monkeypatch):
    """D-10: hint printed when agi_proximity is None."""
    report = _make_report(agi_proximity_value=None)
    output = _capture_render_score_report(report, "test/model", monkeypatch)
    assert "cipherbench play" in output


def test_render_live_summary_format(monkeypatch):
    """D-03: one-line format N/M success (P%) | avg efficiency: X.XX | AGI proximity: Y.YYx."""
    sessions = [
        _make_session("success", attempts_used=1),
        _make_session("success", attempts_used=2),
        _make_session("success", attempts_used=3),
        _make_session("failure", attempts_used=4),
        _make_session("failure", attempts_used=5),
    ]
    human_sessions = []

    output_lines = []
    monkeypatch.setattr(typer, "echo", lambda msg: output_lines.append(msg))

    render_live_summary(sessions, human_sessions)

    assert len(output_lines) == 1
    line = output_lines[0]
    # D-03: match the required format
    pattern = r"\d+/\d+ success \(\d+%\) \| avg efficiency: \d+\.\d{2} \| AGI proximity: .+"
    assert re.match(pattern, line), f"Line does not match expected format: {line!r}"
    # 3 successes out of 5
    assert line.startswith("3/5 success")
    # No human baseline → N/A
    assert "N/A" in line
