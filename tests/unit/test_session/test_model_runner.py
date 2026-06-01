"""Unit tests for ModelSessionRunner — SESS-01, SESS-04."""
from __future__ import annotations

import json
import random

import pytest
from unittest.mock import MagicMock, patch

runner_mod = pytest.importorskip("cipherbench.session.model_runner")
create_model_session = runner_mod.create_model_session

import litellm
from cipherbench.puzzle import EASY, generate_puzzle
from cipherbench.types import AttemptScore


# ---------------------------------------------------------------------------
# SESS-01: session JSON written
# ---------------------------------------------------------------------------


def test_session_json_written(tmp_sessions_dir, mock_adapter):
    """SESS-01: run() writes a session JSON with all D-11 fields to output_dir."""
    runner = create_model_session(seed=42, difficulty=EASY, adapter=mock_adapter, output_dir=tmp_sessions_dir)
    result = runner.run()

    # File exists on disk
    files = list(tmp_sessions_dir.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())

    # All D-11 top-level fields present
    for field in (
        "session_id", "runner_type", "model", "player_name", "seed",
        "difficulty", "puzzle_hash", "outcome", "final_answer",
        "attempts", "created_at", "completed_at",
    ):
        assert field in data, f"Missing D-11 field: {field}"

    assert data["runner_type"] == "model"
    assert data["seed"] == 42
    assert data["outcome"] in ("success", "failure")
    assert data["completed_at"] is not None
    assert isinstance(data["attempts"], list)


def test_checkpoint_written_after_each_attempt(tmp_sessions_dir):
    """SESS-01: write_checkpoint is called with growing attempts list after each probe.

    Uses PROBE: ABCDE which scores 0/5 for seed=42/EASY across all rounds,
    ensuring all MAX_ATTEMPTS valid attempts run without early termination.
    Patches MAX_ATTEMPTS to 5 to keep the test fast and match original intent.
    """
    from tests.conftest import FixedResponseAdapter
    adapter = FixedResponseAdapter("PROBE: ABCDE")
    with patch("cipherbench.session.model_runner.MAX_ATTEMPTS", 5):
        runner = create_model_session(seed=42, difficulty=EASY, adapter=adapter, output_dir=tmp_sessions_dir)

        checkpoint_sizes: list[int] = []
        orig = runner._writer.write_checkpoint

        def spy(record: dict) -> None:
            checkpoint_sizes.append(len(record["attempts"]))
            orig(record)

        runner._writer.write_checkpoint = spy
        runner.run()

        # One checkpoint per valid probe (PROBE: ABCDE scores 0 for seed=42/EASY)
        assert len(checkpoint_sizes) == 5
        assert checkpoint_sizes == list(range(1, 6))


def test_outcome_transitions_to_success(tmp_sessions_dir, mock_adapter):
    """SESS-01: outcome becomes 'success' when engine returns is_correct=True."""
    runner = create_model_session(seed=42, difficulty=EASY, adapter=mock_adapter, output_dir=tmp_sessions_dir)
    # Patch engine to report correct on the first scored probe
    runner._engine.score_attempt = MagicMock(
        return_value=AttemptScore(score=5, max_score=5, is_correct=True)
    )
    result = runner.run()

    assert result["outcome"] == "success"
    assert any(a["is_correct"] for a in result["attempts"])
    assert result["completed_at"] is not None


def test_outcome_transitions_to_failure(tmp_sessions_dir):
    """SESS-01: outcome is 'failure' when all 5 valid probes score is_correct=False.

    PROBE: ABCDE is not the ground truth for seed=42/EASY, so is_correct never fires.
    Patches MAX_ATTEMPTS to 5 to keep the test fast and match original intent.
    """
    from tests.conftest import FixedResponseAdapter
    adapter = FixedResponseAdapter("PROBE: ABCDE")
    with patch("cipherbench.session.model_runner.MAX_ATTEMPTS", 5):
        runner = create_model_session(seed=42, difficulty=EASY, adapter=adapter, output_dir=tmp_sessions_dir)
        result = runner.run()

    assert result["outcome"] == "failure"
    assert not any(a["is_correct"] for a in result["attempts"])
    valid = [a for a in result["attempts"] if not a["extraction_failed"]]
    assert len(valid) == 5


def test_rate_limited_outcome_on_exhaustion(tmp_sessions_dir):
    """SESS-01: outcome is 'rate_limited' when adapter.complete() raises RateLimitError."""

    class RateLimitedAdapter:
        def complete(self, messages: list) -> str:
            raise litellm.RateLimitError(
                message="rate limited",
                llm_provider="openai",
                model="gpt-3.5-turbo",
            )

        def check_token_budget(self, messages: list) -> None:
            pass

    runner = create_model_session(
        seed=42, difficulty=EASY, adapter=RateLimitedAdapter(), output_dir=tmp_sessions_dir
    )
    result = runner.run()

    assert result["outcome"] == "rate_limited"
    files = list(tmp_sessions_dir.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["outcome"] == "rate_limited"


# ---------------------------------------------------------------------------
# SESS-04: RNG isolation
# ---------------------------------------------------------------------------


def test_rng_does_not_pollute_global_random(tmp_sessions_dir, mock_adapter):
    """SESS-04: ModelSessionRunner must not touch global random state."""
    state_before = random.getstate()
    runner = create_model_session(seed=42, difficulty=EASY, adapter=mock_adapter, output_dir=tmp_sessions_dir)
    runner.run()
    state_after = random.getstate()

    assert state_before == state_after


# ---------------------------------------------------------------------------
# D-05: extraction failure semantics
# ---------------------------------------------------------------------------


def test_extraction_failure_does_not_consume_attempt(tmp_sessions_dir):
    """D-05: extraction_failed=True attempts are NOT counted toward the 5-attempt budget."""

    class CountingAdapter:
        """Returns an unextractable response for the first 3 calls, then a valid probe."""

        def __init__(self) -> None:
            self.call_count = 0

        def complete(self, messages: list) -> str:
            self.call_count += 1
            if self.call_count <= 3:
                # All-lowercase: no 5-char uppercase run from EASY alphabet "ABCDEFGHIJ"
                return "this is lowercase, no valid probe at all"
            # ABCDE scores 0/5 for seed=42/EASY — does not trigger is_correct, allowing
            # all 5 valid attempts to run (CR-01: AAAAA now trivially correct, cannot use it here)
            return "PROBE: ABCDE"

        def check_token_budget(self, messages: list) -> None:
            pass

    adapter = CountingAdapter()
    with patch("cipherbench.session.model_runner.MAX_ATTEMPTS", 5):
        runner = create_model_session(seed=42, difficulty=EASY, adapter=adapter, output_dir=tmp_sessions_dir)
        result = runner.run()

    valid = [a for a in result["attempts"] if not a["extraction_failed"]]
    failed = [a for a in result["attempts"] if a["extraction_failed"]]

    assert len(valid) == 5, "Expected exactly 5 valid probe attempts"
    assert len(failed) == 3, "Expected exactly 3 extraction-failed attempts"
    assert len(result["attempts"]) == 8

    for a in failed:
        assert a["probe"] is None
        assert a["score"] is None
        assert a["extraction_failed"] is True
