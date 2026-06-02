"""Pure cipher layer functions — the functional core of CipherBench.

Two module-level pure functions implement the cipher and scoring.
No state, no side effects, no randomness — all inputs are explicit parameters.

Available substitution tables (pass to apply_cipher):
  ATBASH       — reverses the alphabet: A↔Z, B↔Y, ..., Z↔A
  ALTERNATING7 — even-indexed chars shift +7, odd-indexed shift -7 mod 26:
                 A→H  B→U  C→J  D→W  E→L  F→Y  G→N  H→A  I→P  J→C  K→R  L→E  M→T
                 N→G  O→V  P→I  Q→X  R→K  S→Z  T→M  U→B  V→O  W→D  X→Q  Y→F  Z→S

Scoring:
  count_correct compares encode(probe) against the ground_truth string directly.
  The player is shown the ground_truth target upfront and must find the probe
  whose encoding matches it position by position.
"""

# Atbash: SUBSTITUTION[i] = 25 - i  (A↔Z, B↔Y, ..., Z↔A)
ATBASH: list[int] = [25 - i for i in range(26)]

# Alternating ±7: even-indexed positions shift +7 mod 26, odd-indexed shift +19 mod 26 (= -7).
ALTERNATING7: list[int] = [7, 20, 9, 22, 11, 24, 13, 0, 15, 2, 17, 4, 19, 6, 21, 8, 23, 10, 25, 12, 1, 14, 3, 16, 5, 18]

# Cyclic shift [+7,+8,+9,+10,+0] repeating through the alphabet (position i shifts by [7,8,9,10,0][i%5]).
# Not a bijection: H/J/O/T/Y each have two inputs; I/K/P/U/Z are unreachable outputs.
CYCLIC5: list[int] = [(i + (7, 8, 9, 10, 0)[i % 5]) % 26 for i in range(26)]

# Grouped many-to-one: A/B/C→L, D/E→N, F/G→C, K/L→O, V/W→Q, Z→Z (fixed), others 1-to-1.
GROUPED: list[int] = [11, 11, 11, 13, 13, 2, 2, 17, 21, 0, 14, 14, 8, 19, 6, 23, 1, 10, 5, 12, 4, 16, 16, 7, 9, 25]

# Staircase: A-I shift +1..+9, J-O wrap back (-5..-0), P-S shift +1..+4, T-Z wrap back (-10..-4).
# Not a bijection: J/L/N/P/R each have two inputs; A/C/X/Y/Z are unreachable outputs.
STAIRCASE: list[int] = [1, 3, 5, 7, 9, 11, 13, 15, 17, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 9, 11, 13, 15, 17, 19, 21]


def apply_cipher(plaintext: str, alphabet: str, substitution: list[int]) -> list:
    """Apply a substitution cipher to a plaintext string.

    Parameters
    ----------
    plaintext : str
        Input characters, each of which must be present in ``alphabet``.
    alphabet : str
        Character set in use.
    substitution : list[int]
        Substitution table where substitution[i] is the output index for input index i.
        Must cover all indices 0..len(alphabet)-1.

    Returns
    -------
    list[int]
        Encoded character indices.
    """
    return [substitution[alphabet.index(c)] for c in plaintext]


def count_correct(encoded_probe: str, ground_truth: str) -> int:
    """Count positions where encoded_probe[i] == ground_truth[i] (aggregate only).

    Returns the number of positions where ``encoded_probe[i] == ground_truth[i]``.
    No per-position breakdown is ever returned — only the aggregate count.

    Parameters
    ----------
    encoded_probe : str
        The cipher-encoded form of the player's probe.
    ground_truth : str
        The level's fixed target string. Never returned to the caller.

    Returns
    -------
    int
        Number of correctly placed characters (0..len(encoded_probe)).
    """
    if len(encoded_probe) != len(ground_truth):
        raise ValueError(
            f"encoded_probe length {len(encoded_probe)} != ground_truth length {len(ground_truth)}"
        )
    return sum(e == g for e, g in zip(encoded_probe, ground_truth))


