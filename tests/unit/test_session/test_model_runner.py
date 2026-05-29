"""Unit tests for ModelSessionRunner — SESS-01, SESS-04."""
from __future__ import annotations

import pytest

# Guard: skip entire module if model_runner not yet implemented
pytest.importorskip("cipherbench.session.model_runner")


# ---------------------------------------------------------------------------
# SESS-01: session JSON written
# ---------------------------------------------------------------------------


def test_session_json_written(tmp_sessions_dir, mock_adapter):
    """SESS-01: ModelSessionRunner writes a session JSON file to output_dir."""
    pytest.fail("not implemented")


def test_checkpoint_written_after_each_attempt(tmp_sessions_dir, mock_adapter):
    """SESS-01: Inline checkpoint (in_progress) is updated after each probe attempt."""
    pytest.fail("not implemented")


def test_outcome_transitions_to_success(tmp_sessions_dir, mock_adapter):
    """SESS-01: Session outcome transitions from in_progress to success on correct answer."""
    pytest.fail("not implemented")


def test_outcome_transitions_to_failure(tmp_sessions_dir, mock_adapter):
    """SESS-01: Session outcome transitions to failure when all 5 attempts are wrong."""
    pytest.fail("not implemented")


def test_rate_limited_outcome_on_exhaustion(tmp_sessions_dir):
    """SESS-01: Session outcome is rate_limited when adapter raises RateLimitError after retries."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# SESS-04: RNG determinism
# ---------------------------------------------------------------------------


def test_rng_does_not_pollute_global_random(tmp_sessions_dir, mock_adapter):
    """SESS-04: ModelSessionRunner must not call random.seed() globally."""
    pytest.fail("not implemented")


def test_extraction_failure_does_not_consume_attempt(tmp_sessions_dir):
    """SESS-01/D-05: extraction_failed=True attempts are NOT counted toward the 5-attempt limit."""
    pytest.fail("not implemented")
