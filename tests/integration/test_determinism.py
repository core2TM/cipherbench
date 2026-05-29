"""Integration tests — SESS-04: 50 sequential sessions from seed=42 produce identical outcomes."""
from __future__ import annotations

import random

import pytest

# Guard: skip entire module if model_runner not yet implemented
pytest.importorskip("cipherbench.session.model_runner")

from cipherbench.puzzle import EASY
from cipherbench.session.model_runner import create_model_session
from tests.conftest import FixedResponseAdapter


# ---------------------------------------------------------------------------
# SESS-04: 50-run determinism — session-level analogue of engine test_seeding.py
# ---------------------------------------------------------------------------


def test_fifty_sequential_sessions_are_deterministic(tmp_path):
    """SESS-04: 50 sequential sessions from seed=42 with FixedResponseAdapter all have identical outcomes."""
    SEED = 42
    RESPONSE = "PROBE: ABCDE"
    reference_outcome = None

    for run in range(50):
        adapter = FixedResponseAdapter(RESPONSE)
        runner = create_model_session(
            seed=SEED,
            difficulty=EASY,
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
    """SESS-04: Different seeds must produce different internal puzzle configurations.

    Verifies seed isolation at the engine level: base_shifts must differ between
    seeds. After CR-01 fix the encoded-guess scoring means aggregate scores can
    collide for some probe/seed pairs even when base_shifts differ (the mapping is
    many-to-one).  The meaningful isolation guarantee is that the cipher parameters
    themselves are distinct, not that every probe produces a different score.
    """
    from cipherbench.engine.rule_engine import create_rule_engine

    SEED_A = 42
    SEED_B = 99

    engine_a = create_rule_engine(seed=SEED_A, difficulty=EASY)
    engine_b = create_rule_engine(seed=SEED_B, difficulty=EASY)

    assert engine_a._base_shifts != engine_b._base_shifts, (
        f"Seeds {SEED_A} and {SEED_B} produced identical base_shifts {engine_a._base_shifts}. "
        "Seed isolation may be broken."
    )


def test_session_runner_does_not_pollute_global_random(tmp_path):
    """D-11: ModelSessionRunner.run() must not touch the global random state."""
    state_before = random.getstate()

    adapter = FixedResponseAdapter("PROBE: ABCDE")
    runner = create_model_session(
        seed=42,
        difficulty=EASY,
        adapter=adapter,
        output_dir=tmp_path,
    )
    runner.run()

    state_after = random.getstate()
    assert state_after == state_before, (
        "Global random.getstate() changed after ModelSessionRunner.run(). "
        "RNG isolation broken (D-11 discipline)."
    )
