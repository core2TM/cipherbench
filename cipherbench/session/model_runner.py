"""CipherBench model session runner — probe-attempt loop for LLM sessions (SESS-01, SESS-04).

Public names:
  ModelSessionRunner    — drives the attempt loop; call .run() -> dict
  create_model_session  — factory: builds puzzle, engine, writer, and runner

Design decisions:
  D-04  Full attempt history in every user turn (no per-position breakdown)
  D-05  Extraction failures recorded but do NOT consume valid-attempt budget
  D-08  Attempt entry structure: attempt_num, probe, score, max_score, is_correct,
        raw_response, extraction_failed
  D-09  Outcome literals: 'in_progress' | 'success' | 'failure' | 'rate_limited'
  D-11  Top-level session schema — all fields defined in schema.py
  D-16  Hybrid rate-limit: adapter retries internally (tenacity); runner catches the
        re-raised RateLimitError and writes outcome='rate_limited'
  D-17  Inline checkpoint: write_checkpoint after every attempt (valid or invalid)
  D-18  Resume detection: scan output_dir for rate_limited sessions on same model+seed

Security:
  T-03-03-02  MAX_TOTAL_ITERATIONS = 2 * MAX_ATTEMPTS hard cap prevents an infinite
              loop when the model never produces a valid PROBE: response
"""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import litellm

from cipherbench.puzzle import generate_puzzle, get_tier
from cipherbench.types import DifficultyConfig
from cipherbench.session.extractor import extract_probe, extract_answer
from cipherbench.session.prompt import build_system_prompt, build_user_turn
from cipherbench.session.writer import SessionWriter, slugify_model, make_session_id

logger = logging.getLogger(__name__)

MAX_ATTEMPTS: int = 5
MAX_TOTAL_ITERATIONS: int = 2 * MAX_ATTEMPTS  # adversarial loop cap (T-03-03-02)


class ModelSessionRunner:
    """Drives the probe-attempt loop for a single LLM benchmark session (SESS-01).

    Do not instantiate directly — use :func:`create_model_session`.

    Private attributes (single-underscore convention, D-09):
      _puzzle         : Puzzle
      _engine         : RuleEngine  — fresh per session, never reused (D-05 from Phase 2)
      _adapter        : any adapter satisfying complete(messages)->str interface (ADAPT-01)
      _writer         : SessionWriter
      _session_record : dict        — the mutable session state; mutated in-place by run()
    """

    def __init__(
        self,
        puzzle,
        engine,
        adapter,
        writer: SessionWriter,
        session_record: dict,
        valid_attempts_start: int = 0,
    ) -> None:
        self._puzzle = puzzle
        self._engine = engine
        self._adapter = adapter
        self._writer = writer
        self._session_record = session_record
        self._valid_attempts_start = valid_attempts_start  # CR-02: restored budget for resume

    def run(self) -> dict:
        """Execute the probe-attempt loop and return the final session record dict.

        Loop invariants
        ---------------
        - valid_attempts counts only attempts where extraction_failed=False (D-05)
        - total_iterations counts every iteration; capped at MAX_TOTAL_ITERATIONS (T-03-03-02)
        - write_checkpoint is called after every attempt, valid or not (D-17)
        - litellm.RateLimitError (re-raised by tenacity) causes immediate finalize + return (D-16)

        Returns
        -------
        dict
            The final session_record with all D-11 fields.
        """
        alphabet = self._puzzle.difficulty.alphabet
        output_length = self._puzzle.difficulty.output_length
        max_score = output_length

        system_prompt = build_system_prompt(alphabet, output_length)

        # Token budget advisory (ADAPT-02) — warn only, never abort
        try:
            self._adapter.check_token_budget([{"role": "system", "content": system_prompt}])
        except Exception:
            logger.warning("Token budget check failed — continuing session")

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        valid_attempts: int = self._valid_attempts_start  # CR-02: start from restored budget
        total_iterations: int = 0

        while valid_attempts < MAX_ATTEMPTS and total_iterations < MAX_TOTAL_ITERATIONS:
            total_iterations += 1

            user_turn = build_user_turn(
                valid_attempts + 1,
                self._session_record["attempts"],
                max_score,
            )
            messages.append({"role": "user", "content": user_turn})

            try:
                raw = self._adapter.complete(messages)
            except litellm.RateLimitError:
                self._writer.finalize(self._session_record, "rate_limited")
                return self._session_record

            messages.append({"role": "assistant", "content": raw})

            probe = extract_probe(raw, alphabet)

            if probe is None:
                # D-05: extraction failure — record entry, do NOT increment valid_attempts
                entry: dict = {
                    "attempt_num": len(self._session_record["attempts"]) + 1,
                    "probe": None,
                    "score": None,
                    "max_score": max_score,
                    "is_correct": False,
                    "raw_response": raw,
                    "extraction_failed": True,
                }
                self._session_record["attempts"].append(entry)
                self._writer.write_checkpoint(self._session_record)
                continue

            attempt_score = self._engine.score_attempt(probe)
            entry = {
                "attempt_num": len(self._session_record["attempts"]) + 1,
                "probe": probe,
                "score": attempt_score.score,
                "max_score": attempt_score.max_score,
                "is_correct": attempt_score.is_correct,
                "raw_response": raw,
                "extraction_failed": False,
            }
            self._session_record["attempts"].append(entry)
            self._writer.write_checkpoint(self._session_record)
            valid_attempts += 1

            if attempt_score.is_correct:
                break

        # Final-answer step: only when no correct probe was found (D-02)
        final_answer: Optional[str] = None
        if not any(a["is_correct"] for a in self._session_record["attempts"]):
            final_prompt = (
                f"You have used all your probe attempts. "
                f"Submit your final answer as: ANSWER: {'X' * output_length}"
            )
            try:
                raw_ans = self._adapter.complete(
                    messages + [{"role": "user", "content": final_prompt}]
                )
                final_answer = extract_answer(raw_ans, alphabet)
            except litellm.RateLimitError:
                self._writer.finalize(self._session_record, "rate_limited")
                return self._session_record

        outcome = (
            "success"
            if any(a["is_correct"] for a in self._session_record["attempts"])
            else "failure"
        )
        self._writer.finalize(self._session_record, outcome, final_answer=final_answer)
        return self._session_record


def create_model_session(
    seed: Optional[int],
    difficulty: DifficultyConfig,
    adapter,
    output_dir: Path | str,
) -> ModelSessionRunner:
    """Build a fresh :class:`ModelSessionRunner` for a new benchmark session.

    Parameters
    ----------
    seed : int or None
        RNG seed for puzzle generation.  ``None`` generates a random seed using
        an isolated ``random.Random()`` instance (never touches global state, D-11).
    difficulty : DifficultyConfig
        Difficulty preset (EASY, MEDIUM, HARD, or custom).
    adapter :
        Any object satisfying the adapter interface: ``complete(messages)->str``
        and ``check_token_budget(messages)``.
    output_dir : Path or str
        Directory for session JSON files (D-10).

    Returns
    -------
    ModelSessionRunner
        A fully initialised runner with the session ``in_progress`` file already
        written to disk (D-17).
    """
    output_dir = Path(output_dir)

    # RNG isolation: never call global random.seed() or random.randint() (D-11)
    if seed is None:
        seed = random.Random().randint(0, 2**32 - 1)

    model_str: str = getattr(adapter, "_model", None) or "unknown"
    model_slug = slugify_model(model_str)

    # D-18: auto-detect rate_limited sessions for same model+seed and resume
    existing = _find_resumable_session(output_dir, model_slug, seed)
    if existing is not None:
        logger.info(
            "Resuming rate_limited session %s from %d recorded attempt(s)",
            existing["session_id"],
            len(existing["attempts"]),
        )
        puzzle = generate_puzzle(seed, difficulty)
        engine = puzzle.create_engine()
        # Replay engine state to match already-scored attempts
        already_used = 0
        for attempt in existing["attempts"]:
            if not attempt.get("extraction_failed") and attempt.get("probe"):
                engine.score_attempt(attempt["probe"])
                already_used += 1  # CR-02: count valid attempts consumed before rate-limit
        writer = SessionWriter(output_dir, existing["session_id"])
        # Reset outcome to in_progress so the loop continues
        existing["outcome"] = "in_progress"
        return ModelSessionRunner(puzzle, engine, adapter, writer, existing,
                                  valid_attempts_start=already_used)  # CR-02

    puzzle = generate_puzzle(seed, difficulty)
    engine = puzzle.create_engine()
    session_id = make_session_id(model_slug, output_dir)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    session_record: dict = {
        "session_id": session_id,
        "runner_type": "model",
        "model": model_str,
        "player_name": None,
        "seed": seed,
        "difficulty": get_tier(difficulty),
        "puzzle_hash": puzzle.puzzle_hash,
        "outcome": "in_progress",
        "final_answer": None,
        "attempts": [],
        "created_at": now_iso,
        "completed_at": None,
    }

    writer = SessionWriter(output_dir, session_id)
    writer.init_session(session_record)

    return ModelSessionRunner(puzzle, engine, adapter, writer, session_record)


def _find_resumable_session(
    output_dir: Path, model_slug: str, seed: int
) -> Optional[dict]:
    """Scan *output_dir* for a ``rate_limited`` session matching *model_slug* + *seed*.

    Returns the parsed session dict if found, or ``None`` if no match.
    Silently skips files that cannot be parsed.
    """
    if not output_dir.exists():
        return None
    for json_file in output_dir.glob(f"*-{model_slug}.json"):
        try:
            with json_file.open(encoding="utf-8") as f:
                data = json.load(f)
            if data.get("outcome") == "rate_limited" and data.get("seed") == seed:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None
