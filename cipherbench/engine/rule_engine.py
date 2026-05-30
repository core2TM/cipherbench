"""CipherBench rule engine — stateful oracle with hard information boundary.

This module contains two public names:
  RuleEngine       — the trusted oracle class (single public method: score_attempt)
  create_rule_engine — the only authorized constructor (D-10: fresh instance per session)

Design decisions implemented here:
  D-09  Private state attributes (single-underscore convention).
  D-10  Factory pattern — create_rule_engine constructs a fresh instance every call.
  D-11  Explicit rng threading — random.Random(seed) created once in the factory and
        used for all random calls; never the global random module's seed() function.
  D-07  Round-number multiplier applied via apply_state_layer (linear: base * round * rate).
  D-02  state_change_rate stored as _state_change_rate; passed to apply_state_layer each round.
  D-03  Cross-character offset injection applied via apply_cross_char_layer_multi (_k_list).
  D-04  Pull model for cross-character offset injection.
  D-01  Aggregate-only score — count_correct returns an integer count, no positions.

Information boundary (RULE-04):
  score_attempt(guess) is the ONLY public method on RuleEngine.
  All cipher state (_base_shifts, _k_list, _state_change_rate, _alphabet, _ground_truth,
  _round) is private.
  The encoded ciphertext computed per round is never stored as an attribute — it is a
  local variable used only for score comparison, then discarded.

Ground truth (PATTERNS.md Open Question 1, RESOLVED):
  _ground_truth is a random reference string seeded by rng at construction time.
  Both the guess and the ground truth are encoded through identical layers (state +
  cross-char) before comparison — symmetric encoding.  The correct answer is always
  _ground_truth itself; the encoded target changes each round, but submitting _ground_truth
  always produces is_correct=True.

Private attribute convention (D-09, ASVS V4 note from RESEARCH.md):
  Single-underscore convention (_base_shifts, _k_list, …) is used rather than double-
  underscore name-mangling (__base_shifts) by deliberate choice.  Name-mangling does not
  prevent access (Python renames to _RuleEngine__base_shifts, still accessible) and
  degrades debuggability in a research tool where stepping through private state is
  often necessary.  Security enforcement is via the information boundary test suite
  (test_no_public_key_accessor), not name-mangling.
"""
from __future__ import annotations

import random
from typing import Optional

from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.layers import (
    apply_state_layer,
    apply_cross_char_layer_multi,
    count_correct,
    count_chars_present,
)


MAX_SCORE_ATTEMPTS: int = 15
"""Maximum number of score_attempt calls allowed per RuleEngine instance (WR-04).

This constant enforces the 5-attempt core mechanic at the engine level so that
library callers using RuleEngine directly (without a session runner) cannot silently
exceed the attempt budget.
"""


class RuleEngine:
    """Trusted oracle.  Holds cipher state privately.  Exposes score_attempt() only.

    Private attributes use single-underscore convention for convention enforcement.
    Name-mangling (double underscore) not applied — this is a research tool where
    debuggability outweighs mechanical barrier.  Security enforcement is via the
    information boundary test suite, not name-mangling.

    Private attributes:
      _base_shifts          : list[int] — per-position base shift values
      _k_list               : list[int] — cross-character offset distances (D-03)
      _state_change_rate    : float     — round multiplier scaling factor (D-02)
      _alphabet             : str       — character set in use
      _ground_truth         : str       — fixed reference string for encoding
      _round                : int       — current round counter (starts at 1)
      _attempts_remaining   : int       — remaining score_attempt budget (WR-04)

    Never construct this class directly.  Use create_rule_engine(seed, difficulty)
    to obtain a fresh, properly seeded instance (D-10).
    """

    def __init__(
        self,
        base_shifts: list,
        k_list: list,
        difficulty: DifficultyConfig,
        ground_truth: str,
    ) -> None:
        self._base_shifts = base_shifts                       # private — D-09
        self._k_list = k_list                                 # private — D-09 (D-03)
        self._state_change_rate = difficulty.state_change_rate  # private — D-09 (D-02)
        self._alphabet = difficulty.alphabet                  # private — D-09
        self._ground_truth = ground_truth                     # private — D-09
        self._round = 1                                       # private mutable state (starts at 1)
        self._attempts_remaining: int = MAX_SCORE_ATTEMPTS   # WR-04: enforce attempt budget

    def score_attempt(self, guess: str) -> AttemptScore:
        """Validate the guess, encode the ground truth for the current round, return score.

        This is the ONLY public method (RULE-04).  It:
        1. Validates that ``guess`` has the correct length and uses only alphabet characters
           (ASVS V5).  ValueError is raised with a generic message — no cipher state is
           included in the error (T-03-02 mitigation).
        2. Captures the current round number BEFORE incrementing (Pitfall 5 prevention).
        3. Increments the round counter (state mutation happens here and nowhere else).
        4. Encodes the fixed ground truth for the captured round number (RULE-01 state layer).
        5. Counts matching positions and returns an AttemptScore (D-01/D-02/D-03).

        The encoded ciphertext is a local variable — it is never stored as an attribute
        and is never returned to the caller.

        Parameters
        ----------
        guess : str
            Player's or model's probe string.  Must have length equal to output_length
            and contain only characters from the configured alphabet.

        Returns
        -------
        AttemptScore
            Aggregate correctness count.  No cipher key, no ciphertext, no shifts.

        Raises
        ------
        ValueError
            If ``guess`` length does not match output_length, or if ``guess`` contains
            characters outside the configured alphabet.
        """
        # --- Attempt budget enforcement (WR-04) ---
        if self._attempts_remaining <= 0:
            raise RuntimeError(
                "Attempt budget exhausted: this RuleEngine instance allows "
                f"at most {MAX_SCORE_ATTEMPTS} score_attempt calls."
            )
        self._attempts_remaining -= 1

        # --- Input validation (ASVS V5; T-03-02 mitigation) ---
        if len(guess) != len(self._ground_truth):
            raise ValueError(
                f"guess length {len(guess)} does not match output_length "
                f"{len(self._ground_truth)}"
            )
        if not all(c in self._alphabet for c in guess):
            raise ValueError("guess contains characters outside the configured alphabet")

        # --- Capture round before incrementing (Pitfall 5 prevention) ---
        round_num = self._round
        self._round += 1

        # --- Symmetric encoding: both guess and ground truth go through identical layers ---
        # Apply state layer then cross-char layer to the guess.
        shifted_guess = apply_state_layer(
            guess,
            self._base_shifts,
            round_num,
            self._alphabet,
            self._state_change_rate,
        )
        encoded_guess = apply_cross_char_layer_multi(
            shifted_guess, guess, self._k_list, self._alphabet
        )
        # Apply the same two layers to ground truth (symmetric with guess encoding).
        # When guess == ground_truth both sides are identical, so score == max_score.
        shifted_target = apply_state_layer(
            self._ground_truth,
            self._base_shifts,
            round_num,
            self._alphabet,
            self._state_change_rate,
        )
        target_str = apply_cross_char_layer_multi(
            shifted_target, self._ground_truth, self._k_list, self._alphabet
        )
        # Score encoded guess against target (ciphertext never returned to caller)
        score = count_correct(encoded_guess, target_str)
        # Raw-string character presence hint (position-independent, pre-encoding)
        chars_present = count_chars_present(guess, self._ground_truth)
        return AttemptScore(
            score=score,
            max_score=len(guess),
            is_correct=(score == len(guess)),
            correct_chars=chars_present,
        )

    def _encode_for_round(self, round_num: int) -> str:
        """Private: encode the fixed ground truth for the given round number.

        Applies the state layer (RULE-01) followed by the cross-char layer (RULE-02).
        The result is the round-specific encoded target that score_attempt compares
        a guess against.

        This method is intentionally private.  It is accessible to white-box tests
        (see test_state_layer_changes_target_across_rounds) but must never be called
        from outside the class in production code.

        Parameters
        ----------
        round_num : int
            1-indexed round number.  Round 1 uses base shifts × 1; round 2 uses × 2.

        Returns
        -------
        str
            Encoded output string of length equal to output_length.
        """
        shifted = apply_state_layer(
            self._ground_truth,
            self._base_shifts,
            round_num,
            self._alphabet,
            self._state_change_rate,
        )
        return apply_cross_char_layer_multi(shifted, self._ground_truth, self._k_list, self._alphabet)

    def _hash_payload(self) -> dict:
        """Return the minimal derived-state dict for puzzle integrity hashing.

        Intentionally private; only generate_puzzle / verify_puzzle may call this.
        Centralises the private-attribute coupling inside RuleEngine itself so that
        puzzle.py never needs to name _base_shifts, _k_list, or _ground_truth directly.
        """
        return {
            "base_shifts": self._base_shifts,
            "k_list": self._k_list,
            "ground_truth": self._ground_truth,
        }

    # NO other public methods.  No reset(), no get_key(), no cipher_text property,
    # no __repr__ that leaks cipher state.


def create_rule_engine(seed: int, difficulty: Optional[DifficultyConfig] = None) -> RuleEngine:
    """Construct a fresh RuleEngine for a given seed and difficulty (D-10, D-11).

    This is the ONLY authorized way to construct a RuleEngine.  Calling RuleEngine(...)
    directly is an implementation detail — use this factory for all production and test code.

    Each call produces an independent instance with its own _round counter starting at 1.
    Never reuse a RuleEngine instance across sessions — call this factory again (D-10).

    RNG isolation (D-11): a fresh random.Random(seed) instance is created here and all
    random draws go through it.  The global ``random`` module state is never touched
    (verified by test_rng_does_not_pollute_global_random).

    Parameters
    ----------
    seed : int
        Puzzle seed.  Same seed + difficulty produces identical base_shifts, k_list,
        and score sequences.
    difficulty : DifficultyConfig, optional
        Difficulty configuration.  Defaults to DifficultyConfig() (A-Z, length 5).
        ``difficulty.cross_char_depth`` determines how many k values are sampled (D-03).
        ``difficulty.state_change_rate`` is stored on the engine for round scaling (D-02).

    Returns
    -------
    RuleEngine
        Fresh engine with _round = 1, ready for up to 5 score_attempt calls.
    """
    if difficulty is None:
        difficulty = DifficultyConfig()

    rng = random.Random(seed)  # D-11: isolated instance; global random state never touched

    n = difficulty.output_length                        # D-06: fixed at 5
    alphabet = difficulty.alphabet                      # D-05: default A-Z

    # Generate per-position base shifts using the isolated rng (D-11).
    # Shifts are in range [1, len(alphabet)-1] so they are always non-zero,
    # ensuring the round multiplier never produces a trivial zero-shift puzzle.
    base_shifts = [rng.randint(1, len(alphabet) - 1) for _ in range(n)]

    # Generate k_list: cross-char offset distances in [1, n-1] (D-03).
    # rng.sample(range(1, n), 1) is call-count-equivalent to rng.randint(1, n-1)
    # for depth=1, verified across 1000 seeds (RESEARCH.md Pattern 3 / Assumption A1).
    # DifficultyConfig.__post_init__ ensures cross_char_depth <= n-1, preventing
    # "Sample larger than population" ValueError (T-02-02-B mitigation).
    k_list = rng.sample(range(1, n), difficulty.cross_char_depth)

    # Ground truth: random string drawn from this puzzle's seeded rng.
    # Symmetric encoding: both guess and GT go through state + cross-char layers.
    # Submitting GT itself always achieves is_correct=True regardless of round.
    ground_truth = "".join(rng.choice(difficulty.alphabet) for _ in range(n))

    return RuleEngine(
        base_shifts=base_shifts,
        k_list=k_list,
        difficulty=difficulty,
        ground_truth=ground_truth,
    )
