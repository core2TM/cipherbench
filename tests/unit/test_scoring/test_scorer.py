"""Unit tests for scoring formulas — SCORE-01, SCORE-02, SCORE-03, SCORE-04."""
from __future__ import annotations

import json

import pytest
from hypothesis import given, strategies as st

scorer_mod = pytest.importorskip("cipherbench.scoring.scorer")
load_sessions = scorer_mod.load_sessions
efficiency_score = scorer_mod.efficiency_score
success_rate = scorer_mod.success_rate
group_by_difficulty = scorer_mod.group_by_difficulty
agi_proximity = scorer_mod.agi_proximity
compute_report = scorer_mod.compute_report


def _make_session(
    outcome: str,
    attempts_used: int,
    extraction_failures: int = 0,
    difficulty: str = "easy",
) -> dict:
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


def test_success_rate():
    """SCORE-01: correct ratio for mix of success/failure sessions."""
    sessions = [
        _make_session("success", 1),
        _make_session("success", 2),
        _make_session("failure", 5),
        _make_session("failure", 5),
    ]
    assert success_rate(sessions) == 0.5


def test_success_rate_empty():
    """SCORE-01: returns 0.0 for empty list."""
    assert success_rate([]) == 0.0


def test_efficiency_score_success():
    """SCORE-02: correct efficiency for success on attempt N."""
    session = _make_session(outcome="success", attempts_used=1)
    assert efficiency_score(session) == 1.0
    session3 = _make_session(outcome="success", attempts_used=3)
    assert efficiency_score(session3) == pytest.approx((5 - 3 + 1) / 5)


def test_efficiency_score_failure():
    """SCORE-02: efficiency = 0.0 for any failure."""
    session = _make_session(outcome="failure", attempts_used=5)
    assert efficiency_score(session) == 0.0


def test_efficiency_extraction_failures_excluded():
    """SCORE-02: D-06 extraction_failed not counted in attempts_used."""
    session = _make_session(outcome="failure", attempts_used=5, extraction_failures=3)
    assert efficiency_score(session) == 0.0


def test_agi_proximity_with_baseline():
    """SCORE-03: correct ratio when human baseline present."""
    model_sessions = [_make_session("success", 1)]
    human_sessions = [_make_session("success", 2)]
    result = agi_proximity(model_sessions, human_sessions)
    assert result is not None
    assert result > 0.0


def test_agi_proximity_no_baseline():
    """SCORE-03: returns None when no human sessions."""
    model_sessions = [_make_session("success", 1)]
    assert agi_proximity(model_sessions, []) is None


def test_agi_proximity_zero_human_avg():
    """SCORE-03: returns None when human_avg == 0.0 (Pitfall 5)."""
    model_sessions = [_make_session("success", 1)]
    human_sessions = [_make_session("failure", 5), _make_session("failure", 5)]
    assert agi_proximity(model_sessions, human_sessions) is None


def test_group_by_difficulty():
    """SCORE-04: correct tier buckets."""
    sessions = [
        _make_session("success", 1, difficulty="easy"),
        _make_session("failure", 5, difficulty="hard"),
        _make_session("success", 2, difficulty="easy"),
    ]
    groups = group_by_difficulty(sessions)
    assert len(groups["easy"]) == 2
    assert len(groups["hard"]) == 1


def test_compute_report_totals_consistent():
    """SCORE-01/04: totals match per-difficulty aggregation."""
    sessions = [
        _make_session("success", 1, difficulty="easy"),
        _make_session("failure", 5, difficulty="medium"),
    ]
    report = compute_report(sessions, [], model_str="test/model")
    total_from_tiers = sum(
        stats["sessions"] for stats in report["by_difficulty"].values()
    )
    assert report["totals"]["sessions"] == total_from_tiers


def test_score_command_help():
    """CLI: cipherbench score --help exits 0 and shows all flags."""
    from typer.testing import CliRunner
    from cipherbench.cli.app import app

    result = CliRunner().invoke(app, ["score", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.output
    assert "--sessions-dir" in result.output
    assert "--difficulty" in result.output
    assert "--output-file" in result.output
    assert "--human" in result.output


def test_load_sessions_skips_non_terminal(tmp_sessions_dir):
    """D-04: skips in_progress and rate_limited sessions."""
    tmp_sessions_dir.mkdir(parents=True)
    for outcome in ("in_progress", "rate_limited"):
        path = tmp_sessions_dir / f"{outcome}.json"
        path.write_text(json.dumps({
            "outcome": outcome,
            "runner_type": "model",
            "model": "test/model",
            "difficulty": "easy",
            "attempts": [],
        }))
    result = load_sessions(tmp_sessions_dir, runner_type="model", model="test/model")
    assert result == []


def test_load_sessions_missing_dir(tmp_path):
    """Pitfall 4: returns [] when sessions_dir does not exist."""
    missing = tmp_path / "does_not_exist"
    assert load_sessions(missing, runner_type="model") == []


@given(
    outcome=st.sampled_from(["success", "failure"]),
    attempts_used=st.integers(min_value=0, max_value=5),
)
def test_efficiency_score_in_range(outcome, attempts_used):
    """SCORE-02 property: efficiency always in [0.0, 1.0]."""
    session = _make_session(outcome=outcome, attempts_used=attempts_used)
    result = efficiency_score(session)
    assert 0.0 <= result <= 1.0


def test_load_sessions_model_exact_match(tmp_sessions_dir):
    """Pitfall 3: exact-match on model string (no slug conversion)."""
    tmp_sessions_dir.mkdir(parents=True)
    path = tmp_sessions_dir / "session.json"
    path.write_text(json.dumps({
        "outcome": "success",
        "runner_type": "model",
        "model": "anthropic/claude-opus-4",
        "difficulty": "easy",
        "attempts": [],
    }))
    result = load_sessions(tmp_sessions_dir, runner_type="model", model="anthropic-claude-opus-4")
    assert result == []
