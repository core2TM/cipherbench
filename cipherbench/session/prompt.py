"""Pure prompt builder functions — minimal cipher challenge prompt (D-03, D-04).

This module contains two public names:
  build_system_prompt  — construct the minimal system prompt for the cipher challenge
  build_user_turn      — construct a user turn with full attempt history

No strategy hints, worked examples, or per-position breakdown — tests pure model
reasoning (D-03).  Full attempt history is included in every user turn (D-04).

Per D-03: the system prompt must contain only rules and format instructions.
It must NOT contain 'example', 'strategy', 'hint', 'tip', 'suggest', or any
demonstration of how to solve the cipher.
"""
from __future__ import annotations


def build_system_prompt(alphabet: str, output_length: int, max_attempts: int = 5) -> str:
    """Build the minimal system prompt for the cipher challenge (D-03).

    The prompt tells the model:
      1. It is solving a cipher (rules only, no strategy)
      2. It has exactly ``max_attempts`` probe attempts
      3. Each probe is scored by number of characters in the correct position
         (aggregate count only — no per-position breakdown, RULE-03 boundary)
      4. Each probe must be submitted as ``PROBE: XXXXX``
      5. After all probes, it must submit a final answer as ``ANSWER: XXXXX``

    Parameters
    ----------
    alphabet : str
        The puzzle's character set (e.g. 'ABCDEFGHIJKLMNOPQRSTUVWXYZ').
    output_length : int
        Length of each probe and answer string (e.g. 5).
    max_attempts : int, optional
        Number of probe attempts allowed (default 5, matching MAX_ATTEMPTS).
        WR-06: parameterised so callers with non-standard attempt limits produce
        a consistent prompt rather than silently showing the wrong count.

    Returns
    -------
    str
        System prompt string.  Contains 'PROBE:' and 'ANSWER:' literally.
        Does not contain 'example', 'strategy', 'hint', 'tip', or 'suggest'.
    """
    return (
        f"You are playing a cipher-decoding game.\n\n"
        f"Rules:\n"
        f"- The cipher produces a secret {output_length}-character string using "
        f"characters from the alphabet: {alphabet}\n"
        f"- You have exactly {max_attempts} probe attempts to gather information about the cipher.\n"
        f"- After each probe, you will receive two scores:\n"
        f"  * Score: the number of characters in the correct position (0 to {output_length}).\n"
        f"  * Correct Letters: the number of characters in your probe that appear anywhere\n"
        f"    in the secret string, regardless of position (0 to {output_length}).\n"
        f"- No information about which positions are correct is given — only the total counts.\n"
        f"- After all {max_attempts} probes, submit your final answer.\n\n"
        f"Format:\n"
        f"- Each probe must be submitted exactly as: PROBE: {'#' * output_length}\n"
        f"  where each # is replaced by a character from the alphabet.\n"
        f"- Your final answer must be submitted exactly as: ANSWER: {'#' * output_length}\n"
        f"  where each # is replaced by a character from the alphabet.\n\n"
        f"The cipher rule changes each round based on the probe number.\n"
        f"Use the scored feedback from each probe to deduce the pattern.\n"
    )


def build_user_turn(attempt_num: int, attempts: list[dict], max_score: int) -> str:
    """Build the user turn for the current probe request (D-04).

    Includes a running table of all prior attempts and their scores so the
    model has full history available in every turn (D-04).  Never includes
    per-position score breakdown (RULE-03 boundary).

    Parameters
    ----------
    attempt_num : int
        The probe number being requested (1-indexed).
    attempts : list[dict]
        List of prior AttemptEntry dicts.  Empty list for the first probe.
        Each entry must have 'attempt_num', 'probe', 'score', 'max_score' fields.
    max_score : int
        Maximum possible score per attempt (equals output_length, e.g. 5).

    Returns
    -------
    str
        User turn string with attempt history table and probe request.
    """
    if not attempts:
        return f"Please submit your first probe (PROBE: XXXXX)."

    # Build plain-text attempt history table (D-04: full history every turn)
    lines = ["Attempt history:", ""]
    lines.append(f"{'#':<6}{'Probe':<10}{'Score':<10}{'Correct Letters':<16}")
    lines.append("-" * 42)
    for a in attempts:
        probe_str = a.get("probe") or "INVALID"
        score = a.get("score")
        score_str = f"{score}/{max_score}" if score is not None else "N/A"
        cc = a.get("correct_chars")
        cc_str = str(cc) if cc is not None else "N/A"
        lines.append(f"{a['attempt_num']:<6}{probe_str:<10}{score_str:<10}{cc_str:<16}")

    lines.append("")
    lines.append(f"Please submit probe number {attempt_num} (PROBE: XXXXX).")

    return "\n".join(lines)
