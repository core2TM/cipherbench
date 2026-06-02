"""CipherBench model session runner — probe-attempt loop for LLM sessions.

Public names:
  ModelSessionRunner    — drives the attempt loop; call .run() -> dict
  create_model_session  — factory: builds engine, writer, and runner

Security:
  MAX_TOTAL_ITERATIONS = 2 * MAX_ATTEMPTS hard cap prevents an infinite
  loop when the model never produces a valid PROBE: response.
"""
import glob as _glob
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import litellm

from cipherbench.puzzle import (
    ALPHABET,
    OUTPUT_LENGTH,
    create_engine_for_level,
    get_ground_truth,
    get_max_attempts,
)
from cipherbench.session.extractor import extract_probe, extract_answer, extract_reason
from cipherbench.session.prompt import build_system_prompt, build_user_turn
from cipherbench.session.writer import SessionWriter, slugify_model, make_session_id

logger = logging.getLogger(__name__)


class ModelSessionRunner:
    """Drives the probe-attempt loop for a single LLM benchmark session.

    Do not instantiate directly — use :func:`create_model_session`.
    """

    def __init__(
        self,
        level: int,
        ground_truth: str,
        engine,
        adapter,
        writer: SessionWriter,
        session_record: dict,
        max_attempts: int = 5,
        valid_attempts_start: int = 0,
        total_iterations_start: int = 0,
    ) -> None:
        self._level = level
        self._ground_truth = ground_truth
        self._engine = engine
        self._adapter = adapter
        self._writer = writer
        self._session_record = session_record
        self._max_attempts = max_attempts
        self._valid_attempts_start = valid_attempts_start
        self._total_iterations_start = total_iterations_start

    def run(self) -> dict:
        """Execute the probe-attempt loop and return the final session record dict.

        Returns
        -------
        dict
            The final session_record with all fields.
        """
        alphabet = ALPHABET
        output_length = OUTPUT_LENGTH
        max_score = output_length

        system_prompt = build_system_prompt(alphabet, output_length, self._ground_truth, self._max_attempts)

        try:
            self._adapter.check_token_budget([{"role": "system", "content": system_prompt}])
        except Exception:
            logger.warning("Token budget check failed — continuing session")

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        valid_attempts: int = self._valid_attempts_start
        total_iterations: int = self._total_iterations_start
        max_total_iterations = 2 * self._max_attempts

        while valid_attempts < self._max_attempts and total_iterations < max_total_iterations:
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

            probe = extract_probe(raw, alphabet, output_length)

            if probe is None:
                entry: dict = {
                    "attempt_num": len(self._session_record["attempts"]) + 1,
                    "probe": None,
                    "encoded_output": None,
                    "score": None,
                    "max_score": max_score,
                    "is_correct": False,
                    "raw_response": raw,
                    "extraction_failed": True,
                    "reason": extract_reason(raw),
                }
                self._session_record["attempts"].append(entry)
                self._writer.write_checkpoint(self._session_record)
                continue

            attempt_score = self._engine.score_attempt(probe)
            entry = {
                "attempt_num": len(self._session_record["attempts"]) + 1,
                "probe": probe,
                "encoded_output": attempt_score.encoded_output,
                "score": attempt_score.score,
                "max_score": attempt_score.max_score,
                "is_correct": attempt_score.is_correct,
                "raw_response": raw,
                "extraction_failed": False,
                "reason": extract_reason(raw),
            }
            self._session_record["attempts"].append(entry)
            self._writer.write_checkpoint(self._session_record)
            valid_attempts += 1

            if attempt_score.is_correct:
                break

        # Final-answer step: only when no correct probe was found
        final_answer: Optional[str] = None
        if not any(a["is_correct"] for a in self._session_record["attempts"]):
            final_prompt = (
                f"You have used all your probe attempts. "
                f"Submit your final answer as: ANSWER: {'#' * output_length}"
            )
            try:
                raw_ans = self._adapter.complete(
                    messages + [{"role": "user", "content": final_prompt}]
                )
                final_answer = extract_answer(raw_ans, alphabet, output_length)
                self._session_record["final_answer_reason"] = extract_reason(raw_ans)
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
    level: int,
    adapter,
    output_dir: Path | str,
) -> "ModelSessionRunner":
    """Build a fresh ModelSessionRunner for a new benchmark session.

    Parameters
    ----------
    level : int
        Puzzle level: 1, 2, or 3.
    adapter :
        Any object satisfying the adapter interface: complete(messages)->str
        and check_token_budget(messages).
    output_dir : Path or str
        Directory for session JSON files.

    Returns
    -------
    ModelSessionRunner
        A fully initialised runner with the session 'in_progress' file already
        written to disk.
    """
    output_dir = Path(output_dir)
    ground_truth = get_ground_truth(level)
    max_attempts = get_max_attempts(level)

    model_str: str = getattr(adapter, "_model", None) or "unknown"
    model_slug = slugify_model(model_str)

    # Auto-detect rate_limited sessions for same model+level and resume
    existing = _find_resumable_session(output_dir, model_slug, level)
    if existing is not None:
        logger.info(
            "Resuming rate_limited session %s from %d recorded attempt(s)",
            existing["session_id"],
            len(existing["attempts"]),
        )
        engine = create_engine_for_level(level)
        already_used = 0
        for attempt in existing["attempts"]:
            if not attempt.get("extraction_failed") and attempt.get("probe"):
                engine.score_attempt(attempt["probe"])
                already_used += 1
        already_total = len(existing["attempts"])
        writer = SessionWriter(output_dir, existing["session_id"])
        existing["outcome"] = "in_progress"
        return ModelSessionRunner(
            level, ground_truth, engine, adapter, writer, existing,
            max_attempts=max_attempts,
            valid_attempts_start=already_used,
            total_iterations_start=already_total,
        )

    engine = create_engine_for_level(level)
    session_id = make_session_id(model_slug, output_dir)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    session_record: dict = {
        "session_id": session_id,
        "runner_type": "model",
        "model": model_str,
        "player_name": None,
        "level": level,
        "ground_truth": ground_truth,
        "outcome": "in_progress",
        "final_answer": None,
        "final_answer_reason": None,
        "attempts": [],
        "created_at": now_iso,
        "completed_at": None,
    }

    writer = SessionWriter(output_dir, session_id)
    writer.init_session(session_record)

    return ModelSessionRunner(level, ground_truth, engine, adapter, writer, session_record, max_attempts=max_attempts)


def _find_resumable_session(
    output_dir: Path, model_slug: str, level: int
) -> Optional[dict]:
    """Scan output_dir for a rate_limited session matching model_slug + level.

    Returns the parsed session dict if found, or None if no match.
    Silently skips files that cannot be parsed.
    """
    if not output_dir.exists():
        return None
    for json_file in output_dir.glob(f"*-{_glob.escape(model_slug)}.json"):
        try:
            with json_file.open(encoding="utf-8") as f:
                data = json.load(f)
            if (
                data.get("outcome") == "rate_limited"
                and data.get("level") == level
            ):
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None
