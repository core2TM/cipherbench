"""CipherBench scoring report writer — JSON file output for score reports (D-12).

Public names:
  write_json_report  — write a ScoreReport dict to a file as JSON

Design decisions:
  D-12  JSON report structure: model, sessions_scored, by_difficulty, totals, generated_at
  D-12  agi_proximity stored as null (not the string "N/A") in JSON output
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def write_json_report(report: dict, output_file: Path) -> None:
    """Write *report* to *output_file* as JSON (D-12).

    Creates parent directories if needed (matches writer.py pattern).
    agi_proximity values that are None are serialized as JSON null (D-12).

    Parameters
    ----------
    report : dict
        ScoreReport dict produced by compute_report().
    output_file : Path
        Destination file path. Parent directories are created if needed.
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        # WR-03: atomic write via mkstemp + os.replace, consistent with writer.py pattern
        fd, tmp = tempfile.mkstemp(dir=output_file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            os.replace(tmp, output_file)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        logger.info("Score report written to %s", output_file)
    except OSError as exc:
        logger.error("Failed to write score report to %s: %s", output_file, exc)
        raise
