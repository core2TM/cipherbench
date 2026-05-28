"""Pure cipher layer functions — the functional core of CipherBench.

Three module-level pure functions implement each cipher layer independently.
No state, no side effects, no randomness — all inputs are explicit parameters.

These functions are called internally by RuleEngine (Plan 03) and are never
exposed in the top-level cipherbench namespace (internal implementation detail).

Design decisions implemented here:
  D-04  Pull model for cross-character offset injection.
  D-05  Alphabet is an explicit parameter — never hardcoded in function bodies.
  D-07  Linear round multiplier: effective_shift = base_shift * round_num.
  D-08  Round multiplier applies to base_shifts only, not to k.
  D-01  count_correct returns aggregate count only — no per-position breakdown.
"""

from __future__ import annotations


def apply_state_layer(
    plaintext: str,
    base_shifts: list,
    round_num: int,
    alphabet: str,
) -> list:
    """Apply round-number multiplier to base shifts and shift each plaintext character.

    Implements RULE-01 and D-07.  The effective shift for each position is
    ``base_shift * round_num`` (linear multiplier), ensuring a different encoded
    output every round even for the same probe string.

    Parameters
    ----------
    plaintext : str
        Input characters, each of which must be present in ``alphabet``.
    base_shifts : list[int]
        Per-position base shift values.  Must have the same length as ``plaintext``.
    round_num : int
        Current round number (1-indexed).  Multiplied with each base shift.
    alphabet : str
        Character set in use (D-05).  All arithmetic is modulo ``len(alphabet)``.

    Returns
    -------
    list[int]
        Shifted character indices in the range ``0..len(alphabet)-1``.
        Returns indices (not characters) so that ``apply_cross_char_layer``
        can take them directly as input without a second index lookup.
    """
    effective_shifts = [s * round_num for s in base_shifts]
    indices = [alphabet.index(c) for c in plaintext]
    return [(idx + eff) % len(alphabet) for idx, eff in zip(indices, effective_shifts)]


def apply_cross_char_layer(
    shifted_indices: list,
    plaintext: str,
    k: int,
    alphabet: str,
) -> str:
    """Apply cross-character offset injection using the pull model (D-04).

    Implements RULE-02.  For each output position ``j``, the extra offset is
    drawn from the plaintext character at position ``(j - k) % N`` (pull model —
    output position *j* pulls its influence from input position ``j - k``).

    Formula::

        source_pos = (j - k) % n
        extra_offset = alphabet.index(plaintext[source_pos])
        new_idx = (shifted_indices[j] + extra_offset) % len(alphabet)

    This is D-04's "pull model" interpretation of the ``(i + k) mod N`` formula:
    position ``j`` receives influence from position ``(j - k) mod N``, which is
    mathematically equivalent to saying position ``i`` pushes its value to
    position ``(i + k) mod N``, but the pull formulation is more natural in code.

    Parameters
    ----------
    shifted_indices : list[int]
        Output of ``apply_state_layer`` — integer indices in ``0..len(alphabet)-1``.
    plaintext : str
        The original probe string (same as passed to ``apply_state_layer``).
        Used to derive the cross-character extra offset.
    k : int
        Cross-character offset distance (puzzle-level parameter, D-04).
        ``k=0`` means each output position is influenced only by the same-index
        input position (no cross-character mixing).
    alphabet : str
        Character set in use (D-05).  All arithmetic is modulo ``len(alphabet)``.

    Returns
    -------
    str
        Encoded output string of the same length as ``shifted_indices``.
    """
    n = len(shifted_indices)
    result = []
    for j in range(n):
        source_pos = (j - k) % n
        extra_offset = alphabet.index(plaintext[source_pos])
        new_idx = (shifted_indices[j] + extra_offset) % len(alphabet)
        result.append(alphabet[new_idx])
    return "".join(result)


def count_correct(guess: str, ciphertext: str) -> int:
    """Count characters in the correct position — aggregate only (D-01, RULE-03).

    Returns the number of positions where ``guess[i] == ciphertext[i]``.
    No per-position breakdown is ever returned — only the aggregate count.
    This implements the "hidden feedback" layer: a model cannot determine
    *which* positions are correct without cross-character context.

    Parameters
    ----------
    guess : str
        The probe or final-answer string submitted by the player/model.
    ciphertext : str
        The round-specific encoded target produced by ``apply_cross_char_layer``.
        Never returned to the caller — consumed internally by RuleEngine.

    Returns
    -------
    int
        Number of correctly placed characters (0..len(guess)).
    """
    return sum(g == c for g, c in zip(guess, ciphertext))
