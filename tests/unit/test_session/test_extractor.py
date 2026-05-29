"""Unit tests for ProbeExtractor and AnswerExtractor — ADAPT-04."""
from __future__ import annotations

import pytest

# Guard: skip entire module if extractor not yet implemented (Plan 02/03)
pytest.importorskip("cipherbench.session.extractor")


# ---------------------------------------------------------------------------
# ADAPT-04: probe extraction
# ---------------------------------------------------------------------------


def test_extract_probe_primary_pattern():
    """ADAPT-04: Primary regex 'PROBE: XXXXX' extracts the probe string."""
    pytest.fail("not implemented")


def test_extract_probe_fallback_pattern():
    """ADAPT-04: Fallback regex extracts a 5-char alphabet run when PROBE: tag is absent."""
    pytest.fail("not implemented")


def test_extract_probe_returns_none_on_no_match():
    """ADAPT-04: Returns None when neither primary nor fallback pattern matches."""
    pytest.fail("not implemented")


def test_extract_answer_primary_pattern():
    """ADAPT-04: Primary regex 'ANSWER: XXXXX' extracts the final answer string."""
    pytest.fail("not implemented")


def test_extract_answer_returns_none_on_missing_tag():
    """ADAPT-04: Returns None when ANSWER: tag is absent from response."""
    pytest.fail("not implemented")


def test_extract_probe_raises_on_empty_alphabet():
    """ADAPT-04: Raises ValueError when alphabet is empty string."""
    pytest.fail("not implemented")
