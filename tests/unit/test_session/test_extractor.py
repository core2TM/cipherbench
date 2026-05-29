"""Unit tests for ProbeExtractor and AnswerExtractor — ADAPT-04."""
from __future__ import annotations

import pytest

# Guard: skip entire module if extractor not yet implemented (Plan 02/03)
extractor_mod = pytest.importorskip("cipherbench.session.extractor")
extract_probe = extractor_mod.extract_probe
extract_answer = extractor_mod.extract_answer

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# ADAPT-04: probe extraction
# ---------------------------------------------------------------------------


def test_extract_probe_primary_pattern():
    """ADAPT-04: Primary regex 'PROBE: XXXXX' extracts the probe string."""
    result = extract_probe("PROBE: ABCDE", ALPHABET)
    assert result == "ABCDE"


def test_extract_probe_fallback_pattern():
    """ADAPT-04: Fallback regex extracts a 5-char alphabet run when PROBE: tag is absent."""
    result = extract_probe("The answer is ABCDE I think", ALPHABET)
    assert result == "ABCDE"


def test_extract_probe_returns_none_on_no_match():
    """ADAPT-04: Returns None when neither primary nor fallback pattern matches."""
    result = extract_probe("no valid probe here 123", ALPHABET)
    assert result is None


def test_extract_answer_primary_pattern():
    """ADAPT-04: Primary regex 'ANSWER: XXXXX' extracts the final answer string."""
    result = extract_answer("ANSWER: XYZAB", ALPHABET)
    assert result == "XYZAB"


def test_extract_answer_returns_none_on_missing_tag():
    """ADAPT-04: Returns None when ANSWER: tag is absent from response (no fallback for answers)."""
    result = extract_answer("XYZAB", ALPHABET)
    assert result is None


def test_extract_probe_raises_on_empty_alphabet():
    """ADAPT-04: Raises ValueError when alphabet is empty string."""
    with pytest.raises(ValueError):
        extract_probe("PROBE: ABCDE", "")
