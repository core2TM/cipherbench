"""Integration test — SESS-04: 50 sequential sessions from seed=42 produce identical outcomes."""
from __future__ import annotations

import pytest

# Guard: skip entire module if model_runner not yet implemented
pytest.importorskip("cipherbench.session.model_runner")


# ---------------------------------------------------------------------------
# SESS-04: determinism across 50 sequential sessions
# ---------------------------------------------------------------------------


def test_fifty_sequential_sessions_are_deterministic(tmp_sessions_dir, mock_adapter):
    """SESS-04: 50 sequential sessions from seed=42 with FixedResponseAdapter all have identical outcomes."""
    pytest.fail("not implemented")


def test_different_seeds_produce_different_session_outcomes(tmp_sessions_dir, mock_adapter):
    """SESS-04: Sessions run with different seeds must not produce identical puzzle state."""
    pytest.fail("not implemented")
