"""CipherBench rule engine — stateful oracle with hard information boundary.

This module contains two public names:
  RuleEngine           — the trusted oracle class (single public method: score_attempt)
  create_rule_engine   — the only authorized constructor

Cipher design (no randomness):
  A fixed substitution table maps each character to another (see layers.py).
  Even-indexed alphabet chars shift +7 mod 26; odd-indexed shift -7 mod 26.
  No fixed points — every character maps to a different character.

  Scoring: the player's probe is encoded and compared directly against ground_truth.
  The player is shown the ground_truth as the target from the start, and must find
  the probe whose encoding matches it position by position.

Information boundary:
  score_attempt(guess) is the ONLY public method on RuleEngine.
  ground_truth is private. The encoded probe is returned to the caller as
  encoded_output so the player can observe the cipher behaviour.
"""
from cipherbench.types import AttemptScore
from cipherbench.engine.layers import apply_cipher, count_correct


class RuleEngine:
    """Trusted oracle. Holds cipher state privately. Exposes score_attempt() only.

    The cipher rule is the same for every level and every position:
    each character shifts by its own index (A=+0, B=+1, ..., J=+9).
    What differs between levels is the ground_truth target and attempt limit.

    Private attributes use single-underscore convention.

    Private attributes:
      _alphabet     : str — character set in use (A-Z)
      _ground_truth : str — fixed target encoding for this level
      _substitution : list[int] — cipher substitution table for this level
      _max_attempts : int — attempt budget for this level
      _attempts_remaining : int — remaining score_attempt budget

    Never construct this class directly. Use create_rule_engine() or
    puzzle.create_engine_for_level(level).
    """

    def __init__(self, alphabet: str, ground_truth: str, substitution: list[int], max_attempts: int = 5) -> None:
        self._alphabet = alphabet
        self._ground_truth = ground_truth
        self._substitution = substitution
        self._max_attempts = max_attempts
        self._attempts_remaining: int = max_attempts

    def score_attempt(self, guess: str) -> AttemptScore:
        """Encode the guess, compare against ground_truth, return score + encoded_output.

        This is the ONLY public method.  It:
        1. Validates guess length and alphabet membership.
        2. Encodes the guess through the fixed cipher.
        3. Counts positions where encode(guess)[i] == ground_truth[i].
        4. Returns AttemptScore with score, is_correct, encoded_output.

        The encoded_output is always included so the player can observe the
        cipher mapping for each probe.

        Parameters
        ----------
        guess : str
            Player's or model's probe string. Must have length equal to
            output_length and contain only characters from the configured alphabet.

        Returns
        -------
        AttemptScore
            Aggregate correctness count and encoded output.

        Raises
        ------
        ValueError
            If guess length does not match output_length, or if guess contains
            characters outside the configured alphabet.
        RuntimeError
            If the attempt budget is exhausted.
        """
        if self._attempts_remaining <= 0:
            raise RuntimeError(
                f"Attempt budget exhausted: at most {self._max_attempts} score_attempt calls."
            )
        self._attempts_remaining -= 1

        if len(guess) != len(self._ground_truth):
            raise ValueError(
                f"guess length {len(guess)} does not match output_length "
                f"{len(self._ground_truth)}"
            )
        if not all(c in self._alphabet for c in guess):
            raise ValueError("guess contains characters outside the configured alphabet")

        shifted = apply_cipher(guess, self._alphabet, self._substitution)
        encoded = "".join(self._alphabet[i] for i in shifted)

        score = count_correct(encoded, self._ground_truth)

        return AttemptScore(
            score=score,
            max_score=len(guess),
            is_correct=(score == len(guess)),
            encoded_output=encoded,
        )

    # NO other public methods. No reset(), no get_key(), no cipher_text property,
    # no __repr__ that leaks cipher state.


def create_rule_engine(alphabet: str, ground_truth: str, substitution: list[int], max_attempts: int = 5) -> RuleEngine:
    """Construct a fresh RuleEngine for a given level configuration.

    This is the only authorized way to construct a RuleEngine. Calling
    RuleEngine(...) directly is an implementation detail.

    Parameters
    ----------
    alphabet : str
        Character set in use.
    ground_truth : str
        The level's fixed target encoding string.
    substitution : list[int]
        Cipher substitution table for this level (e.g. ATBASH or ALTERNATING7).
    max_attempts : int, optional
        Probe budget for this engine instance (default 5).

    Returns
    -------
    RuleEngine
        Fresh engine ready for up to max_attempts score_attempt calls.
    """
    return RuleEngine(alphabet=alphabet, ground_truth=ground_truth, substitution=substitution, max_attempts=max_attempts)
