"""Unit tests for cipherbench.engine.layers — pure cipher layer functions.

Tests cover:
  - apply_cipher  (substitution cipher application)
  - count_correct (RULE-03: aggregate position-correct count only, D-01)
"""

import pytest
from cipherbench.engine.layers import apply_cipher, count_correct, CYCLIC5

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# apply_cipher tests
# ---------------------------------------------------------------------------


def test_apply_cipher_identity():
    """Identity substitution: apply_cipher with list(range(26)) returns index 0 for 'A'."""
    result = apply_cipher("A", ALPHABET, list(range(26)))
    assert result == [0]


def test_apply_cipher_shift():
    """Single-char shift: substitution[0]=1 maps 'A' to index 1."""
    sub = [1] + list(range(1, 26))
    result = apply_cipher("A", ALPHABET, sub)
    assert result == [1]


def test_apply_cipher_returns_list_of_ints():
    """Return type must be a list and all elements must be int."""
    result = apply_cipher("ABC", ALPHABET, list(range(26)))
    assert isinstance(result, list)
    assert all(isinstance(x, int) for x in result)


def test_apply_cipher_wraps_modulo():
    """All returned indices must be within [0, len(alphabet)-1]."""
    result = apply_cipher("ABCDE", ALPHABET, CYCLIC5)
    assert all(0 <= idx < len(ALPHABET) for idx in result)


def test_apply_cipher_consistent():
    """Same inputs always produce the same output (determinism)."""
    result1 = apply_cipher("ABCDE", ALPHABET, CYCLIC5)
    result2 = apply_cipher("ABCDE", ALPHABET, CYCLIC5)
    assert result1 == result2


def test_apply_cipher_cyclic5_known_value():
    """CYCLIC5 applies known shifts: A(0) +7 = 7 = H."""
    result = apply_cipher("A", ALPHABET, CYCLIC5)
    assert result == [7]  # A -> index 7 -> H


# ---------------------------------------------------------------------------
# count_correct tests (RULE-03, D-01)
# ---------------------------------------------------------------------------


def test_count_correct_perfect_match():
    """Perfect match returns length of the strings."""
    assert count_correct("ABCDE", "ABCDE") == 5


def test_count_correct_one_wrong():
    """One character wrong returns length minus 1."""
    assert count_correct("ABCDE", "XBCDE") == 4


def test_count_correct_all_wrong():
    """No character in correct position returns 0."""
    assert count_correct("AAAAA", "BBBBB") == 0


def test_count_correct_middle_match():
    """Only the middle character matches (position 2)."""
    # ABCDE vs EDCBA: A!=E, B!=D, C==C, D!=B, E!=A → 1
    assert count_correct("ABCDE", "EDCBA") == 1


def test_count_correct_returns_int():
    """Return type must be int."""
    result = count_correct("ABCDE", "ABCDE")
    assert isinstance(result, int)
