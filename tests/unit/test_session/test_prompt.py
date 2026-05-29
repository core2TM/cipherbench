"""Unit tests for PromptBuilder — D-03, D-04."""
from __future__ import annotations

import pytest

# Guard: skip entire module if prompt not yet implemented
pytest.importorskip("cipherbench.session.prompt")


# ---------------------------------------------------------------------------
# D-03: minimal prompt content
# ---------------------------------------------------------------------------


def test_system_prompt_contains_probe_format():
    """D-03: System prompt includes the PROBE: XXXXX format instruction."""
    pytest.fail("not implemented")


def test_system_prompt_contains_no_strategy_hints():
    """D-03: System prompt must not contain worked examples or strategy hints."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# D-04: full attempt history in user turn
# ---------------------------------------------------------------------------


def test_user_turn_contains_attempt_history():
    """D-04: User turn includes a running table of all prior attempts and scores."""
    pytest.fail("not implemented")


def test_user_turn_contains_no_per_position_breakdown():
    """D-04: User turn must not include per-position score breakdown (RULE-03 boundary)."""
    pytest.fail("not implemented")
