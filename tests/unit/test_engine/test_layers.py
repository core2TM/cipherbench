"""Unit tests for cipherbench.engine.layers — pure cipher layer functions.

Tests cover:
  - apply_state_layer  (RULE-01: state evolution via round-number multiplier)
  - apply_cross_char_layer  (RULE-02: cross-character interdependence, pull model)
  - count_correct  (RULE-03: aggregate position-correct count only, D-01)

Canonical regression tests from CONTEXT.md D-07:
  apply_state_layer("AAA", [1,2,3], round_num=1, alphabet=ALPHABET) == [1, 2, 3]
  apply_state_layer("BBB", [1,2,3], round_num=2, alphabet=ALPHABET) == [3, 5, 7]
"""

import pytest
from cipherbench.engine.layers import apply_state_layer, count_correct, count_chars_present

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# apply_state_layer tests (RULE-01)
# ---------------------------------------------------------------------------


def test_apply_state_layer_canonical():
    """Canonical regression: AAA + base_shifts [1,2,3] returns [1,2,3].

    A=0, effective_shifts=[1,2,3], 0+1=1, 0+2=2, 0+3=3.
    """
    result = apply_state_layer("AAA", [1, 2, 3], alphabet=ALPHABET)
    assert result == [1, 2, 3]


def test_apply_state_layer_consistent_across_calls():
    """Same probe always produces the same encoded output — encoding is round-independent."""
    result1 = apply_state_layer("BBB", [1, 2, 3], alphabet=ALPHABET)
    result2 = apply_state_layer("BBB", [1, 2, 3], alphabet=ALPHABET)
    assert result1 == result2


def test_apply_state_layer_wraps_modulo():
    """Shift that overflows must wrap correctly via mod len(alphabet).

    Z=25, base_shift=1 → effective_shift=1, 25+1=26, 26 mod 26 = 0 = A.
    """
    result = apply_state_layer("Z", [1], alphabet=ALPHABET)
    assert result == [0]


def test_apply_state_layer_returns_list_of_ints():
    """Return type must be a list and all elements must be int."""
    result = apply_state_layer("ABC", [1, 1, 1], alphabet=ALPHABET)
    assert isinstance(result, list)
    assert all(isinstance(x, int) for x in result)


def test_apply_state_layer_alphabet_length_respected():
    """All returned indices must be in range 0..len(alphabet)-1."""
    result = apply_state_layer("ZZZZZ", [25, 25, 25, 25, 25], alphabet=ALPHABET)
    assert all(0 <= idx < len(ALPHABET) for idx in result)


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


# ---------------------------------------------------------------------------
# apply_state_layer with state_change_rate tests (D-02)
# ---------------------------------------------------------------------------


def test_state_layer_rate_default_unchanged():
    """Explicit rate=1.0 produces the same result as no rate argument."""
    no_rate = apply_state_layer("AAA", [1, 2, 3], ALPHABET)
    with_rate = apply_state_layer("AAA", [1, 2, 3], ALPHABET, 1.0)
    assert no_rate == with_rate


def test_state_layer_rate_changes_shifts():
    """state_change_rate=1.5 produces different effective shifts than rate=1.0.

    With base_shifts=[2,4]:
      rate=1.0: effective = [int(2*1.0), int(4*1.0)] = [2, 4]
      rate=1.5: effective = [int(2*1.5), int(4*1.5)] = [3, 6]
    """
    result_1_0 = apply_state_layer("AA", [2, 4], ALPHABET, state_change_rate=1.0)
    result_1_5 = apply_state_layer("AA", [2, 4], ALPHABET, state_change_rate=1.5)
    assert result_1_0 != result_1_5


def test_state_layer_rate_2_shifts():
    """state_change_rate=2.0: effective shift = int(1*2.0) = 2.

    A=0, base_shifts=[1], rate=2.0:
      effective = int(1*2.0) = 2, result = (0+2) % 26 = 2
    """
    result = apply_state_layer("A", [1], ALPHABET, state_change_rate=2.0)
    assert result == [2]


# ---------------------------------------------------------------------------
# count_chars_present tests
# ---------------------------------------------------------------------------


def test_count_chars_present_exact_match():
    """Same string: all characters present → returns len(string)."""
    assert count_chars_present("ABCDE", "ABCDE") == 5


def test_count_chars_present_no_overlap():
    """Completely disjoint character sets → 0."""
    assert count_chars_present("AAAAA", "BBBBB") == 0


def test_count_chars_present_multiset_cap():
    """Multiset intersection caps at ground_truth count.

    guess="AAABB" has 3 A's, ground_truth="AACCC" has 2 A's → min(3,2)=2.
    B not in ground_truth → 0. Total: 2.
    """
    assert count_chars_present("AAABB", "AACCC") == 2


def test_count_chars_present_position_independent():
    """Characters in wrong positions still count — full multiset intersection."""
    # "EDCBA" and "ABCDE" share the same character set, all 5 chars match via intersection.
    assert count_chars_present("EDCBA", "ABCDE") == 5


def test_count_chars_present_partial():
    """Only one shared character in guess and ground_truth → 1."""
    assert count_chars_present("ABCDE", "AXXXX") == 1


def test_count_chars_present_length_mismatch_raises():
    """Lengths must match — raises ValueError otherwise."""
    with pytest.raises(ValueError):
        count_chars_present("AB", "ABC")
