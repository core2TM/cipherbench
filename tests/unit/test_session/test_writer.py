"""Unit tests for SessionWriter atomic write and checkpoint behavior."""
from __future__ import annotations

import pytest

# Guard: skip entire module if writer not yet implemented
pytest.importorskip("cipherbench.session.writer")


# ---------------------------------------------------------------------------
# Atomic write behavior
# ---------------------------------------------------------------------------


def test_atomic_write_creates_file(tmp_sessions_dir):
    """SessionWriter._atomic_write_json() creates the file at the specified path."""
    pytest.fail("not implemented")


def test_atomic_write_is_idempotent_on_overwrite(tmp_sessions_dir):
    """SessionWriter._atomic_write_json() overwrites existing file without data loss."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# Checkpoint lifecycle
# ---------------------------------------------------------------------------


def test_in_progress_written_at_init(tmp_sessions_dir):
    """SessionWriter writes outcome='in_progress' when session is initialized."""
    pytest.fail("not implemented")


def test_outcome_overwritten_on_finalize(tmp_sessions_dir):
    """SessionWriter.finalize() overwrites outcome field from in_progress to terminal state."""
    pytest.fail("not implemented")
