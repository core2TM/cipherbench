"""CipherBench session writer — atomic JSON checkpoint writes (D-17, T-03-03-01).

Public names:
  SessionWriter       — stateful writer: init_session, write_checkpoint, finalize
  slugify_model       — sanitise model string for filenames (D-06)
  make_session_id     — timestamp + slug with collision avoidance (D-06, Pitfall 3)

Private helpers:
  _atomic_write_json  — tempfile.mkstemp + os.replace atomic write (T-03-03-01)

Design decisions:
  D-06  File naming: {YYYYMMDD}T{HHMMSS}-{model-slug}.json
  D-09  Outcome literals: 'in_progress' | 'success' | 'failure' | 'rate_limited'
  D-10  Flat sessions/ directory; writer accepts caller-supplied output_dir
  D-17  Inline checkpoint: write in_progress at init, overwrite after every attempt
"""
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write *data* to *path* atomically via mkstemp + os.replace (T-03-03-01).

    Creates parent directories if needed.  If the write fails for any reason the
    temporary file is cleaned up and the exception is re-raised, leaving any
    previously committed file at *path* untouched.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def slugify_model(model: str) -> str:
    """Sanitise a LiteLLM model string for use in filenames (D-06).

    Replaces ``/``, ``\\``, ``:``, ``@``, ``.`` with ``-``, collapses repeated
    dashes, strips leading/trailing dashes, and truncates to 50 characters.

    Example: ``'anthropic/claude-opus-4-7'`` → ``'anthropic-claude-opus-4-7'``
    """
    slug = re.sub(r"[/\\:@.]", "-", model)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug[:50]


def make_session_id(model_slug: str, output_dir: Path) -> str:
    """Generate a unique session ID: ``{YYYYMMDD}T{HHMMSS}-{slug}`` (D-06, Pitfall 3).

    If the candidate path already exists (same-second write), appends ``-2``,
    ``-3``, … until a non-colliding name is found.
    """
    output_dir = Path(output_dir)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    candidate = f"{timestamp}-{model_slug}"
    if not (output_dir / f"{candidate}.json").exists():
        return candidate
    suffix = 2
    while (output_dir / f"{candidate}-{suffix}.json").exists():
        suffix += 1
    return f"{candidate}-{suffix}"


class SessionWriter:
    """Atomic JSON session writer with inline checkpoint support (D-17).

    Lifecycle::

        writer = SessionWriter(output_dir, session_id)
        writer.init_session(record)          # writes outcome='in_progress'
        writer.write_checkpoint(record)      # called after each attempt
        writer.finalize(record, outcome)     # overwrites with terminal state

    Private attributes (single-underscore convention, mirrors rule_engine.py D-09):
      _output_dir : Path
      _session_id : str
      _path       : Path  — the canonical session file path
    """

    def __init__(self, output_dir: Path | str, session_id: str) -> None:
        self._output_dir = Path(output_dir)
        self._session_id = session_id
        self._path = self._output_dir / f"{session_id}.json"

    @property
    def path(self) -> Path:
        """Read-only path to the session JSON file."""
        return self._path

    def init_session(self, record: dict) -> None:
        """Write the initial session file with ``outcome='in_progress'`` (D-17).

        Mutates *record* in-place: sets ``outcome`` and ``completed_at``.
        """
        record["outcome"] = "in_progress"
        record["completed_at"] = None
        _atomic_write_json(self._path, record)

    def write_checkpoint(self, record: dict) -> None:
        """Overwrite the session file with the current attempt state (D-17).

        Called after every attempt (valid or extraction-failed).  The caller is
        responsible for updating *record* before this call.
        """
        _atomic_write_json(self._path, record)

    def finalize(self, record: dict, outcome: str, final_answer: str | None = None) -> None:
        """Write the terminal session state and timestamp (D-09).

        Mutates *record* in-place: sets ``outcome``, ``completed_at``, and
        optionally ``final_answer``.
        """
        record["outcome"] = outcome
        record["completed_at"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        if final_answer is not None:
            record["final_answer"] = final_answer
        _atomic_write_json(self._path, record)
