"""Pure prompt builder functions — cipher challenge prompt.

This module contains two public names:
  build_system_prompt  — construct the system prompt for the cipher challenge
  build_user_turn      — construct a user turn with full attempt history

The system prompt reveals the cipher target (ground_truth) to the player from
the start. The cipher rule (A=+0, B=+1, ...) is hidden — the player must
discover it through probing.

Per the design: the system prompt must contain only rules and format instructions.
It must NOT contain 'example', 'strategy', 'hint', 'tip', 'suggest', or any
demonstration of how to solve the cipher.
"""
def build_system_prompt(
    alphabet: str,
    output_length: int,
    ground_truth: str,
    max_attempts: int = 5,
) -> str:
    """Build the system prompt for the cipher challenge.

    The prompt tells the model:
      1. It is solving a cipher (rules only, no strategy)
      2. The target encoding (ground_truth) it must match
      3. It has exactly max_attempts probe attempts
      4. Each probe returns the encoded output and a position-correct count
      5. Probe and answer format instructions

    Parameters
    ----------
    alphabet : str
        The puzzle's character set (e.g. 'ABCDEFGHIJ').
    output_length : int
        Length of each probe and answer string (e.g. 5).
    ground_truth : str
        The fixed target encoding shown to the player.
    max_attempts : int, optional
        Number of probe attempts allowed (default 5).

    Returns
    -------
    str
        System prompt string.
    """
    return (
        f"You are playing a cipher-decoding game.\n\n"
        f"Objective:\n"
        f"- Find the {output_length}-character input string that, when passed through\n"
        f"  the cipher, produces this exact target output: {ground_truth}\n"
        f"- The alphabet is: {alphabet}\n\n"
        f"Rules:\n"
        f"- You have exactly {max_attempts} probe attempts.\n"
        f"- After each probe, you will receive:\n"
        f"  * Encoded output: what your probe encodes to through the cipher.\n"
        f"  * Score: the number of positions where encoded_output[i] == target[i] (0 to {output_length}).\n"
        f"- No information about which positions are correct is given — only the total counts.\n"
        f"- After all {max_attempts} probes, submit your final answer.\n\n"
        f"Format:\n"
        f"- Each probe must be submitted exactly as: PROBE: {'#' * output_length}\n"
        f"  where each # is replaced by a character from the alphabet.\n"
        f"- Your final answer must be submitted exactly as: ANSWER: {'#' * output_length}\n"
        f"  where each # is replaced by a character from the alphabet.\n"
    )


def build_user_turn(attempt_num: int, attempts: list[dict], max_score: int) -> str:
    """Build the user turn for the current probe request.

    Includes a running table of all prior attempts with their encoded output
    and scores so the model has full history in every turn. Never includes
    per-position score breakdown.

    Parameters
    ----------
    attempt_num : int
        The probe number being requested (1-indexed).
    attempts : list[dict]
        List of prior AttemptEntry dicts. Empty list for the first probe.
    max_score : int
        Maximum possible score per attempt (equals output_length, e.g. 5).

    Returns
    -------
    str
        User turn string with attempt history table and probe request.
    """
    if not attempts:
        return f"Please submit your first probe (PROBE: {'#' * max_score})."

    lines = ["Attempt history:", ""]
    lines.append(f"{'#':<6}{'Probe':<10}{'Encoded':<10}{'Score':<10}")
    lines.append("-" * 36)
    for a in attempts:
        probe_str = a.get("probe") or "INVALID"
        encoded_str = a.get("encoded_output") or "N/A"
        score = a.get("score")
        score_str = f"{score}/{max_score}" if score is not None else "N/A"
        lines.append(
            f"{a['attempt_num']:<6}{probe_str:<10}{encoded_str:<10}{score_str:<10}"
        )

    lines.append("")
    lines.append(f"Please submit probe number {attempt_num} (PROBE: {'#' * max_score}).")

    return "\n".join(lines)
