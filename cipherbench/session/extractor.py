"""Pure extraction functions — regex probe and answer parsing (ADAPT-04, D-01, D-02, D-05).

This module contains two public names:
  extract_probe   — extract a valid probe string from freeform model output
  extract_answer  — extract a valid final answer string from freeform model output

No state, no side effects — all inputs are explicit parameters.

Security note (T-03-02-03 mitigation):
  All regex patterns use bounded quantifiers ({5}) rather than greedy or possessive
  quantifiers (.+ or .*).  This prevents ReDoS attacks when processing adversarial
  model output.  Empty alphabet raises ValueError before any regex is constructed.
"""
from __future__ import annotations

import re

MAX_ATTEMPTS: int = 5
"""Maximum valid probe attempts per session (D-05 / RESEARCH.md open question 2).

Extraction failures do NOT consume an attempt count.  A hard cap of 2 * MAX_ATTEMPTS
total iterations (valid + invalid combined) prevents infinite loops against adversarial
models that never produce a valid PROBE: response.
"""


def extract_probe(text: str, alphabet: str, output_length: int = 5) -> str | None:
    """Extract a probe string from a model's freeform response (ADAPT-04, D-01, D-05).

    Tries the primary pattern (strict ``PROBE:`` tag) first.  Falls back to any
    ``output_length``-character run from the alphabet if the primary pattern fails.
    Returns None if both patterns fail — the session runner records
    ``extraction_failed=True`` and does NOT consume an attempt count (D-05).

    Parameters
    ----------
    text : str
        Raw freeform response string from the model.
    alphabet : str
        The puzzle's character set (e.g. 'ABCDEFGHIJKLMNOPQRSTUVWXYZ').
        Must be a non-empty string.
    output_length : int, optional
        Expected length of a valid probe string (default 5).  Must match the
        DifficultyConfig so that probes for non-default lengths are extracted
        correctly (WR-02).

    Returns
    -------
    str or None
        The extracted ``output_length``-character probe string if found; None otherwise.

    Raises
    ------
    ValueError
        If ``alphabet`` is empty — the regex character class would be undefined.
    """
    if not alphabet:
        raise ValueError("alphabet must be non-empty")

    pattern_chars = re.escape(alphabet)

    # Primary: strict PROBE: tag with exactly output_length alphabet characters (D-01)
    # Bounded quantifier {output_length} prevents ReDoS (T-03-02-03)
    primary = re.search(rf"PROBE:\s*([{pattern_chars}]{{{output_length}}})", text)
    if primary:
        return primary.group(1)

    # Fallback: any output_length-character run from the alphabet (D-05 loose pattern)
    # Bounded quantifier {output_length} prevents ReDoS (T-03-02-03)
    fallback = re.search(rf"([{pattern_chars}]{{{output_length}}})", text)
    if fallback:
        return fallback.group(1)

    return None


def extract_answer(text: str, alphabet: str, output_length: int = 5) -> str | None:
    """Extract a final answer string from a model's freeform response (ADAPT-04, D-02).

    Only the primary pattern (strict ``ANSWER:`` tag) is tried.  No fallback is
    applied for final answers (D-02) — the answer step requires explicit formatting.
    Returns None if the primary pattern fails.

    Parameters
    ----------
    text : str
        Raw freeform response string from the model.
    alphabet : str
        The puzzle's character set (e.g. 'ABCDEFGHIJKLMNOPQRSTUVWXYZ').
        Must be a non-empty string.
    output_length : int, optional
        Expected length of a valid answer string (default 5).  Must match the
        DifficultyConfig so that answers for non-default lengths are extracted
        correctly (WR-02).

    Returns
    -------
    str or None
        The extracted ``output_length``-character answer string if found; None otherwise.

    Raises
    ------
    ValueError
        If ``alphabet`` is empty — the regex character class would be undefined.
    """
    if not alphabet:
        raise ValueError("alphabet must be non-empty")

    pattern_chars = re.escape(alphabet)

    # Primary only: strict ANSWER: tag with exactly output_length alphabet characters (D-02)
    # No fallback for answers — explicit format required at the answer step
    # Bounded quantifier {output_length} prevents ReDoS (T-03-02-03)
    primary = re.search(rf"ANSWER:\s*([{pattern_chars}]{{{output_length}}})", text)
    if primary:
        return primary.group(1)

    return None
