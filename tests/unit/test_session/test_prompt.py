"""Unit tests for PromptBuilder — D-03, D-04."""

import pytest

# Guard: skip entire module if prompt not yet implemented
prompt_mod = pytest.importorskip("cipherbench.session.prompt")
build_system_prompt = prompt_mod.build_system_prompt
build_user_turn = prompt_mod.build_user_turn

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# D-03: minimal prompt content
# ---------------------------------------------------------------------------


def test_system_prompt_contains_probe_format():
    """D-03: System prompt includes the PROBE: XXXXX format instruction."""
    prompt = build_system_prompt(ALPHABET, 5, "ABCDE")
    assert "PROBE:" in prompt


def test_system_prompt_contains_no_strategy_hints():
    """D-03: System prompt must not contain worked examples or strategy hints."""
    prompt = build_system_prompt(ALPHABET, 5, "ABCDE")
    prompt_lower = prompt.lower()
    forbidden_words = ["example", "strategy", "hint", "tip", "suggest"]
    for word in forbidden_words:
        assert word not in prompt_lower, f"System prompt contains forbidden word: {word!r}"


# ---------------------------------------------------------------------------
# D-04: full attempt history in user turn
# ---------------------------------------------------------------------------


def test_user_turn_contains_attempt_history():
    """D-04: User turn includes a running table of all prior attempts and scores."""
    attempts = [
        {
            "attempt_num": 1,
            "probe": "ABCDE",
            "score": 2,
            "max_score": 5,
            "is_correct": False,
        }
    ]
    result = build_user_turn(2, attempts, 5)
    assert "ABCDE" in result
    assert "2/5" in result


def test_user_turn_contains_no_per_position_breakdown():
    """D-04: User turn must not include per-position score breakdown (RULE-03 boundary)."""
    attempts = [
        {
            "attempt_num": 1,
            "probe": "ABCDE",
            "score": 2,
            "max_score": 5,
            "is_correct": False,
        }
    ]
    result = build_user_turn(2, attempts, 5)
    result_lower = result.lower()
    forbidden_phrases = ["position 1", "position 2", "pos 1", "pos 2"]
    for phrase in forbidden_phrases:
        assert phrase not in result_lower, f"User turn contains per-position breakdown: {phrase!r}"
