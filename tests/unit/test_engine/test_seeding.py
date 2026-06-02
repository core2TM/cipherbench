"""RNG discipline tests — GEN-04 and SESS-04 verification.

These tests verify:
  GEN-04: No global random.seed() calls anywhere in the generation path.
          All randomness goes through isolated random.Random(seed) instances.
  SESS-04: 50 sequential calls to create_engine_for_level(1) followed by
           score_attempt('ABCDE') × 5 all produce identical score sequences.

Source references:
  RESEARCH.md §Code Examples — 50-Run Determinism Test
  RESEARCH.md §Common Pitfalls — Pitfall 2 (RNG Non-Determinism)
  CONTEXT.md D-11 (explicit rng threading)
"""

import inspect
import random

import pytest

import cipherbench.engine.rule_engine as rule_engine_mod
import cipherbench.engine.layers as layers_mod
from cipherbench.puzzle import create_engine_for_level


# ---------------------------------------------------------------------------
# GEN-04: Source inspection — no global random.seed() calls
# ---------------------------------------------------------------------------


def test_no_global_random_seed_in_rule_engine_module():
    """GEN-04: random.seed() must not appear anywhere in rule_engine.py source."""
    src = inspect.getsource(rule_engine_mod)
    assert "random.seed(" not in src, (
        "Found forbidden 'random.seed(' in cipherbench.engine.rule_engine source. "
        "Use rng = random.Random(seed) instead."
    )


def test_no_global_random_seed_in_layers_module():
    """GEN-04: random.seed() must not appear anywhere in layers.py source."""
    src = inspect.getsource(layers_mod)
    assert "random.seed(" not in src, (
        "Found forbidden 'random.seed(' in cipherbench.engine.layers source. "
        "Layers are pure functions — they must not use the random module at all."
    )


def test_no_module_level_random_calls():
    """GEN-04: No module-level random.randint/random.choice/random.random() calls.

    All calls to random must go through an rng instance (e.g. rng.randint()), not
    the module directly (random.randint()). Checks both rule_engine and layers sources.
    """
    for mod in [rule_engine_mod, layers_mod]:
        src = inspect.getsource(mod)
        # These module-level calls are forbidden; rng.* equivalents are required
        forbidden_patterns = ["random.randint(", "random.choice(", "random.random("]
        for pattern in forbidden_patterns:
            assert pattern not in src, (
                f"Found module-level '{pattern}' in {mod.__name__} source. "
                f"Use rng.{pattern.split('.', 1)[1]} instead."
            )


# ---------------------------------------------------------------------------
# SESS-04: Determinism — 50 sequential runs from same level
# ---------------------------------------------------------------------------


def test_fifty_sequential_runs_are_deterministic():
    """SESS-04: 50 sequential calls to create_engine_for_level(1) must produce identical score sequences.

    Verifies that the fixed-level design is deterministic and that no state bleeds
    between calls (fresh instances only).
    """
    PROBE = "ABCDE"
    ROUNDS = 5
    reference_scores = None

    for run in range(50):
        engine = create_engine_for_level(1)
        scores = [engine.score_attempt(PROBE).score for _ in range(ROUNDS)]
        if reference_scores is None:
            reference_scores = scores
        assert scores == reference_scores, (
            f"Run {run}: got {scores}, expected {reference_scores}. State bleed detected."
        )


# ---------------------------------------------------------------------------
# Differentiation: different levels produce different scores
# ---------------------------------------------------------------------------


def test_different_seeds_produce_different_scores():
    """Different levels must produce different encoded outputs for the same probe.

    Level 1 and Level 2 use different cipher substitutions — same probe should
    encode to different outputs.
    """
    engine_1 = create_engine_for_level(1)
    engine_2 = create_engine_for_level(2)

    PROBE = "ABCDE"
    result_1 = engine_1.score_attempt(PROBE)
    result_2 = engine_2.score_attempt(PROBE)

    assert result_1.encoded_output != result_2.encoded_output, (
        "Level 1 and Level 2 produced identical encoded outputs. "
        "This indicates the levels are not using different ciphers."
    )


# ---------------------------------------------------------------------------
# D-11: Global random state is not polluted by create_engine_for_level
# ---------------------------------------------------------------------------


def test_rng_does_not_pollute_global_random():
    """D-11: create_engine_for_level must not touch the global random state.

    Saves the global random state before calling create_engine_for_level(1) and
    asserts it is unchanged afterward. The fixed-level design uses no RNG, so
    global state must be unaffected.
    """
    state_before = random.getstate()
    create_engine_for_level(1)
    state_after = random.getstate()
    assert state_after == state_before, (
        "Global random.getstate() changed after create_engine_for_level(). "
        "Factory must not touch global random state."
    )
