"""Integration tests — SESS-04: 50 sequential sessions from level 1 produce identical outcomes."""

import random

import pytest

# Guard: skip entire module if model_runner not yet implemented
pytest.importorskip("cipherbench.session.model_runner")

from cipherbench.puzzle import create_engine_for_level
from cipherbench.session.model_runner import create_model_session
from tests.conftest import FixedResponseAdapter


# ---------------------------------------------------------------------------
# SESS-04: 50-run determinism — session-level analogue of engine test_seeding.py
# ---------------------------------------------------------------------------


def test_fifty_sequential_sessions_are_deterministic(tmp_path):
    """SESS-04: 50 sequential sessions from level=1 with FixedResponseAdapter all have identical outcomes."""
    RESPONSE = "PROBE: TUVWX"
    reference_outcome = None

    for run in range(50):
        adapter = FixedResponseAdapter(RESPONSE)
        runner = create_model_session(
            level=1,
            adapter=adapter,
            output_dir=tmp_path / f"run_{run}",
        )
        session = runner.run()
        if reference_outcome is None:
            reference_outcome = session["outcome"]
        assert session["outcome"] == reference_outcome, (
            f"Run {run}: got {session['outcome']}, expected {reference_outcome}. State bleed detected."
        )

    assert reference_outcome is not None


def test_different_seeds_produce_different_puzzle_state(tmp_path):
    """SESS-04: Different levels must produce different internal puzzle configurations.

    Verifies level isolation at the engine level: ground_truth must differ between
    levels 1 and 2.
    """
    engine_1 = create_engine_for_level(1)
    engine_2 = create_engine_for_level(2)

    assert engine_1._ground_truth != engine_2._ground_truth, (
        f"Level 1 and Level 2 produced identical _ground_truth: '{engine_1._ground_truth}'. "
        "Level isolation may be broken."
    )


def test_session_runner_does_not_pollute_global_random(tmp_path):
    """D-11: ModelSessionRunner.run() must not touch the global random state."""
    state_before = random.getstate()

    adapter = FixedResponseAdapter("PROBE: TUVWX")
    runner = create_model_session(
        level=1,
        adapter=adapter,
        output_dir=tmp_path,
    )
    runner.run()

    state_after = random.getstate()
    assert state_after == state_before, (
        "Global random.getstate() changed after ModelSessionRunner.run(). "
        "RNG isolation broken (D-11 discipline)."
    )
