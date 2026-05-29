"""Unit tests for HumanSessionRunner — SESS-02."""
from __future__ import annotations

import pytest

# Guard: skip entire module if human_runner not yet implemented
pytest.importorskip("cipherbench.session.human_runner")


# ---------------------------------------------------------------------------
# SESS-02: human session runner
# ---------------------------------------------------------------------------


def test_human_session_json_schema_matches_model(tmp_sessions_dir):
    """SESS-02: Human session JSON uses the same top-level schema as model sessions (D-11)."""
    pytest.fail("not implemented")


def test_human_runner_rejects_invalid_length_input(tmp_sessions_dir):
    """SESS-02: HumanSessionRunner rejects probe input with incorrect character length."""
    pytest.fail("not implemented")


def test_human_runner_rejects_chars_outside_alphabet(tmp_sessions_dir):
    """SESS-02: HumanSessionRunner rejects probe input with characters outside the puzzle alphabet."""
    pytest.fail("not implemented")
