"""Unit tests for SessionWriter atomic write and checkpoint behavior."""
from __future__ import annotations

import json

import pytest

writer_mod = pytest.importorskip("cipherbench.session.writer")
_atomic_write_json = writer_mod._atomic_write_json
SessionWriter = writer_mod.SessionWriter


# ---------------------------------------------------------------------------
# Atomic write behavior
# ---------------------------------------------------------------------------


def test_atomic_write_creates_file(tmp_sessions_dir):
    """_atomic_write_json creates the file and writes valid JSON."""
    path = tmp_sessions_dir / "test.json"
    _atomic_write_json(path, {"key": "value"})
    assert path.exists()
    assert json.loads(path.read_text()) == {"key": "value"}


def test_atomic_write_is_idempotent_on_overwrite(tmp_sessions_dir):
    """_atomic_write_json overwrites without leaving tmp files behind."""
    path = tmp_sessions_dir / "test.json"
    _atomic_write_json(path, {"outcome": "in_progress"})
    _atomic_write_json(path, {"outcome": "success"})
    assert json.loads(path.read_text()) == {"outcome": "success"}
    # No .tmp files left behind
    tmp_files = list(tmp_sessions_dir.glob("*.tmp"))
    assert tmp_files == []


# ---------------------------------------------------------------------------
# Checkpoint lifecycle
# ---------------------------------------------------------------------------


def test_in_progress_written_at_init(tmp_sessions_dir):
    """SessionWriter writes outcome='in_progress' when session is initialized."""
    writer = SessionWriter(tmp_sessions_dir, "20260529T000000-test-model")
    record: dict = {"session_id": "20260529T000000-test-model", "attempts": []}
    writer.init_session(record)

    assert writer.path.exists()
    data = json.loads(writer.path.read_text())
    assert data["outcome"] == "in_progress"
    assert data["completed_at"] is None


def test_outcome_overwritten_on_finalize(tmp_sessions_dir):
    """SessionWriter.finalize() overwrites outcome and sets completed_at."""
    writer = SessionWriter(tmp_sessions_dir, "20260529T000000-test-model")
    record: dict = {"session_id": "20260529T000000-test-model", "attempts": []}
    writer.init_session(record)
    writer.finalize(record, "success", final_answer="ABCDE")

    data = json.loads(writer.path.read_text())
    assert data["outcome"] == "success"
    assert data["completed_at"] is not None
    assert data["final_answer"] == "ABCDE"
