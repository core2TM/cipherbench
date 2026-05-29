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
from datetime import datetime, timezone
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
    raise NotImplementedError
