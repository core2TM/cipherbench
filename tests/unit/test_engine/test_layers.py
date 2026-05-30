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
from cipherbench.engine.layers import apply_state_layer, apply_cross_char_layer, count_correct, apply_cross_char_layer_multi, count_chars_present

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# apply_state_layer tests (RULE-01)
# ---------------------------------------------------------------------------


def test_apply_state_layer_round1_canonical():
    """Canonical regression: AAA + base_shifts [1,2,3] at round 1 returns [1,2,3].

    A=0, effective_shifts=[1,2,3], 0+1=1, 0+2=2, 0+3=3.
    """
    result = apply_state_layer("AAA", [1, 2, 3], round_num=1, alphabet=ALPHABET)
    assert result == [1, 2, 3]


def test_apply_state_layer_round2_doubles_shifts():
    """Canonical regression: BBB + base_shifts [1,2,3] at round 2 returns [3,5,7].

    B=1, effective_shifts=[2,4,6] (D-07: base * round_num), 1+2=3, 1+4=5, 1+6=7.
    """
    result = apply_state_layer("BBB", [1, 2, 3], round_num=2, alphabet=ALPHABET)
    assert result == [3, 5, 7]


def test_apply_state_layer_wraps_modulo():
    """Shift that overflows must wrap correctly via mod len(alphabet).

    Z=25, base_shift=1, round_num=1 → effective_shift=1, 25+1=26, 26 mod 26 = 0 = A.
    """
    result = apply_state_layer("Z", [1], round_num=1, alphabet=ALPHABET)
    assert result == [0]


def test_apply_state_layer_round_multiplier_changes_output():
    """Round multiplier produces different outputs for different round numbers.

    With non-zero base_shifts, round 1 and round 2 must diverge.
    """
    result_r1 = apply_state_layer("AAAAA", [1, 1, 1, 1, 1], round_num=1, alphabet=ALPHABET)
    result_r2 = apply_state_layer("AAAAA", [1, 1, 1, 1, 1], round_num=2, alphabet=ALPHABET)
    assert result_r1 != result_r2


def test_apply_state_layer_returns_list_of_ints():
    """Return type must be a list and all elements must be int."""
    result = apply_state_layer("ABC", [1, 1, 1], round_num=1, alphabet=ALPHABET)
    assert isinstance(result, list)
    assert all(isinstance(x, int) for x in result)


def test_apply_state_layer_alphabet_length_respected():
    """All returned indices must be in range 0..len(alphabet)-1."""
    result = apply_state_layer("ZZZZZ", [25, 25, 25, 25, 25], round_num=3, alphabet=ALPHABET)
    assert all(0 <= idx < len(ALPHABET) for idx in result)


# ---------------------------------------------------------------------------
# apply_cross_char_layer tests (RULE-02)
# ---------------------------------------------------------------------------


def test_cross_char_k0_vs_k1_differs():
    """k=0 and k=1 produce different output given non-uniform plaintext.

    With shifted=[0,0,0,0,0] and plaintext="AABAA", k=0 means each output position
    uses its own corresponding input (all A → add 0), while k=1 means output[0] uses
    input[(0-1) mod 5] = input[4] = A, output[1] uses input[0] = A, ..., output[3]
    uses input[2] = B — so position 3 differs between k=0 and k=1.
    """
    shifted = [0, 0, 0, 0, 0]
    result_k0 = apply_cross_char_layer(shifted, "AABAA", k=0, alphabet=ALPHABET)
    result_k1 = apply_cross_char_layer(shifted, "AABAA", k=1, alphabet=ALPHABET)
    assert result_k0 != result_k1


def test_cross_char_pull_model_direction():
    """Verify pull model: output[j] receives offset from input[(j-k) % N].

    With shifted=[0,0,0], plaintext="ABC", k=1, alphabet=ALPHABET:
      output[0]: source_pos = (0-1) mod 3 = 2, plaintext[2] = C (index 2),
                 new_idx = (0 + 2) % 26 = 2, alphabet[2] = 'C'
      output[1]: source_pos = (1-1) mod 3 = 0, plaintext[0] = A (index 0),
                 new_idx = (0 + 0) % 26 = 0, alphabet[0] = 'A'
      output[2]: source_pos = (2-1) mod 3 = 1, plaintext[1] = B (index 1),
                 new_idx = (0 + 1) % 26 = 1, alphabet[1] = 'B'
    Expected: "CAB"
    """
    result = apply_cross_char_layer([0, 0, 0], "ABC", k=1, alphabet=ALPHABET)
    assert result == "CAB"


def test_cross_char_single_char_change_affects_multiple_positions():
    """Changing one input character must change at least one non-corresponding output position.

    This verifies cross-char mixing is active: changing char at position 0 (which
    influences a different output position under pull model) changes output.
    """
    shifted = [0, 0, 0, 0, 0]
    result_base = apply_cross_char_layer(shifted, "AAAAA", k=1, alphabet=ALPHABET)
    # Change position 0 of plaintext; under pull model with k=1, this affects output[1]
    result_changed = apply_cross_char_layer(shifted, "BAAAA", k=1, alphabet=ALPHABET)
    assert result_base != result_changed


def test_cross_char_returns_string_of_correct_length():
    """Output is a str with len == len(shifted_indices)."""
    shifted = [0, 1, 2, 3, 4]
    result = apply_cross_char_layer(shifted, "ABCDE", k=1, alphabet=ALPHABET)
    assert isinstance(result, str)
    assert len(result) == 5


def test_cross_char_output_chars_in_alphabet():
    """All output characters must be in the provided alphabet."""
    shifted = [10, 15, 20, 3, 7]
    result = apply_cross_char_layer(shifted, "HELLO", k=2, alphabet=ALPHABET)
    assert all(c in ALPHABET for c in result)


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
    """Explicit rate=1.0 produces the same result as no rate argument (backward compat)."""
    no_rate = apply_state_layer("AAA", [1, 2, 3], 1, ALPHABET)
    with_rate = apply_state_layer("AAA", [1, 2, 3], 1, ALPHABET, 1.0)
    assert no_rate == with_rate


def test_state_layer_rate_changes_shifts():
    """state_change_rate=1.5 produces different effective shifts than rate=1.0.

    With base_shifts=[2,4], round_num=1:
      rate=1.0: effective = [int(2*1*1.0), int(4*1*1.0)] = [2, 4]
      rate=1.5: effective = [int(2*1*1.5), int(4*1*1.5)] = [3, 6]
    """
    result_1_0 = apply_state_layer("AA", [2, 4], 1, ALPHABET, state_change_rate=1.0)
    result_1_5 = apply_state_layer("AA", [2, 4], 1, ALPHABET, state_change_rate=1.5)
    assert result_1_0 != result_1_5


def test_state_layer_rate_2_doubles_shifts():
    """state_change_rate=2.0 with round_num=2: effective shift = int(1*2*2.0) = 4.

    A=0, base_shifts=[1], round_num=2, rate=2.0:
      effective = int(1*2*2.0) = 4, result = (0+4) % 26 = 4
    """
    result = apply_state_layer("A", [1], 2, ALPHABET, state_change_rate=2.0)
    assert result == [4]


# ---------------------------------------------------------------------------
# apply_cross_char_layer_multi tests (D-03)
# ---------------------------------------------------------------------------


def test_multi_depth1_matches_single():
    """apply_cross_char_layer_multi with k_list=[1] matches apply_cross_char_layer(k=1).

    With shifted=[0,0,0], plaintext="ABC", k=1:
      pull model: output[0] ← plaintext[(0-1) mod 3]=plaintext[2]=C(2), (0+2)%26=2 → C
                  output[1] ← plaintext[(1-1) mod 3]=plaintext[0]=A(0), (0+0)%26=0 → A
                  output[2] ← plaintext[(2-1) mod 3]=plaintext[1]=B(1), (0+1)%26=1 → B
    Expected: "CAB"
    """
    result_multi = apply_cross_char_layer_multi([0, 0, 0], "ABC", [1], ALPHABET)
    result_single = apply_cross_char_layer([0, 0, 0], "ABC", 1, ALPHABET)
    assert result_multi == result_single == "CAB"


def test_multi_depth2_differs_depth1():
    """apply_cross_char_layer_multi with k_list=[1,2] produces different output than k_list=[1]."""
    result_depth1 = apply_cross_char_layer_multi([0, 0, 0, 0, 0], "ABCDE", [1], ALPHABET)
    result_depth2 = apply_cross_char_layer_multi([0, 0, 0, 0, 0], "ABCDE", [1, 2], ALPHABET)
    assert result_depth1 != result_depth2


def test_multi_accumulates_additively():
    """Manually verify depth=2 additive accumulation for k_list=[1,2] on 3-char input.

    shifted=[0,0,0], plaintext="ABC", k_list=[1,2], alphabet=ALPHABET
    For j=0:
      base = 0
      k=1: source_pos=(0-1)%3=2, extra=alphabet.index('C')=2, base=(0+2)%26=2
      k=2: source_pos=(0-2)%3=1, extra=alphabet.index('B')=1, base=(2+1)%26=3
      result[0] = ALPHABET[3] = 'D'
    For j=1:
      base = 0
      k=1: source_pos=(1-1)%3=0, extra=alphabet.index('A')=0, base=(0+0)%26=0
      k=2: source_pos=(1-2)%3=2, extra=alphabet.index('C')=2, base=(0+2)%26=2
      result[1] = ALPHABET[2] = 'C'
    For j=2:
      base = 0
      k=1: source_pos=(2-1)%3=1, extra=alphabet.index('B')=1, base=(0+1)%26=1
      k=2: source_pos=(2-2)%3=0, extra=alphabet.index('A')=0, base=(1+0)%26=1
      result[2] = ALPHABET[1] = 'B'
    Expected: "DCB"
    """
    result = apply_cross_char_layer_multi([0, 0, 0], "ABC", [1, 2], ALPHABET)
    assert result == "DCB"


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
