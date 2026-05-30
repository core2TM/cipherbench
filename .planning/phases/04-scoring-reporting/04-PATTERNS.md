# Phase 4: Scoring & Reporting - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `cipherbench/scoring/__init__.py` | package-init | n/a | `cipherbench/session/__init__.py` | exact (empty `__init__`) |
| `cipherbench/scoring/scorer.py` | service | CRUD + transform | `cipherbench/session/model_runner.py` (`_find_resumable_session` glob pattern) | role-match |
| `cipherbench/scoring/reporter.py` | utility | request-response | `cipherbench/session/human_runner.py` (Rich Panel + Table display) | exact |
| `cipherbench/scoring/report_writer.py` | utility | file-I/O | `cipherbench/session/writer.py` (JSON write pattern) | exact |
| `cipherbench/cli/app.py` | controller | request-response | itself — extend existing `run_command`/`play_command` pattern | self-extension |
| `tests/unit/test_scoring/test_scorer.py` | test | batch + property | `tests/unit/test_session/test_model_runner.py` | role-match |
| `tests/unit/test_scoring/test_report_writer.py` | test | file-I/O | `tests/unit/test_session/test_writer.py` | exact |

---

## Pattern Assignments

### `cipherbench/scoring/__init__.py` (package-init)

**Analog:** `cipherbench/session/__init__.py` (empty, 1 line)

The `session/__init__.py` is a bare package marker — a single blank line. The `scoring/__init__.py` should export the public surface so callers can do `from cipherbench.scoring import load_sessions, compute_report`.

**Init pattern** — the `session/__init__.py` is empty (blank marker). For `scoring/__init__.py` follow the `cipherbench/__init__.py` docstring + `__all__` pattern instead, since scoring has a meaningful public API:

**Imports/exports pattern** (`cipherbench/__init__.py` lines 1-34):
```python
"""CipherBench scoring package — session loading, formula computation, and reporting.

Public names:
  load_sessions   — load and filter terminal sessions from a directory
  compute_report  — compute ScoreReport from a list of sessions + optional human baseline
  ScoreReport     — TypedDict: the structured scoring result
"""
from cipherbench.scoring.scorer import load_sessions, compute_report, ScoreReport

__all__ = [
    "load_sessions",
    "compute_report",
    "ScoreReport",
]
```

---

### `cipherbench/scoring/scorer.py` (service, CRUD + transform)

**Analog:** `cipherbench/session/model_runner.py`

The `_find_resumable_session` function (lines 255-273) demonstrates the canonical glob + JSON load + filter pattern used throughout the codebase. `scorer.py` extends this into a full-directory load rather than a single-file find.

**Module docstring pattern** (`model_runner.py` lines 1-22):
```python
"""CipherBench scoring — pure computation: session loading, filtering, and score formulas.

Public names:
  load_sessions   — glob sessions dir, filter to terminal sessions matching criteria
  efficiency_score — SCORE-02: per-session efficiency formula
  success_rate    — SCORE-01: fraction of successful sessions
  group_by_difficulty — SCORE-04: bucket sessions by difficulty tier
  agi_proximity   — SCORE-03: model_avg_efficiency / human_avg_efficiency; None if no baseline
  compute_report  — aggregate all metrics into a ScoreReport dict
  ScoreReport     — TypedDict for the complete scoring result

Design decisions implemented here:
  D-04  Session set = terminal sessions (outcome in {'success','failure'}) only
  D-06  attempts_used = count of attempts where extraction_failed=False
  D-08  Human baseline matched by difficulty tier, not exact seed
  D-09  AGI proximity = model_avg / human_avg; None when no human sessions or human_avg=0
  D-10  Empty or non-existent sessions directory: return [] (no error)
"""
```

**Imports pattern** (`model_runner.py` lines 23-40):
```python
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

MAX_ATTEMPTS: int = 5  # Fixed core mechanic — not configurable in v1 (D-06)
TERMINAL_OUTCOMES: frozenset[str] = frozenset({"success", "failure"})
```

**Session loading pattern** (`model_runner.py` `_find_resumable_session` lines 255-273 — adapted to load all):
```python
def load_sessions(
    sessions_dir: Path,
    runner_type: str,           # 'model' or 'human'
    model: str | None = None,   # None = all models / all players
    difficulty: str | None = None,  # None = all tiers
) -> list[dict]:
    """Load and filter terminal sessions from sessions_dir (D-04, D-05).

    Returns [] if sessions_dir does not exist or is empty (Pitfall 4 guard).
    """
    if not sessions_dir.exists():
        return []
    result: list[dict] = []
    for path in sessions_dir.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue  # Pitfall 2 guard: skip malformed or unreadable files
        if data.get("outcome") not in TERMINAL_OUTCOMES:
            continue  # skip in_progress and rate_limited (D-04)
        if data.get("runner_type") != runner_type:
            continue  # runner_type discriminator (D-07 Phase 3)
        if model is not None and data.get("model") != model:
            continue  # exact-match model string (Pitfall 3: no slug comparison)
        if difficulty is not None and data.get("difficulty") != difficulty:
            continue
        result.append(data)
    return result
```

**Efficiency score formula** (SCORE-02, from RESEARCH.md Pattern 2):
```python
def efficiency_score(session: dict) -> float:
    """SCORE-02: success × (max_attempts - attempts_used + 1) / max_attempts.

    attempts_used = count of attempts where extraction_failed=False (D-06).
    Division by zero is impossible: MAX_ATTEMPTS is a fixed positive integer.
    """
    success = 1 if session["outcome"] == "success" else 0
    attempts_used = sum(
        1 for a in session["attempts"] if not a.get("extraction_failed", False)
    )
    return success * (MAX_ATTEMPTS - attempts_used + 1) / MAX_ATTEMPTS
```

**Success rate** (SCORE-01):
```python
def success_rate(sessions: list[dict]) -> float:
    """SCORE-01: fraction of sessions with outcome='success'."""
    if not sessions:
        return 0.0
    return sum(1 for s in sessions if s["outcome"] == "success") / len(sessions)
```

**Grouping pattern** (SCORE-04):
```python
def group_by_difficulty(sessions: list[dict]) -> dict[str, list[dict]]:
    """SCORE-04: bucket sessions by difficulty tier string ('easy'|'medium'|'hard')."""
    groups: dict[str, list[dict]] = {}
    for s in sessions:
        tier = s.get("difficulty", "unknown")
        groups.setdefault(tier, []).append(s)
    return groups
```

**AGI proximity with N/A guard** (SCORE-03, from RESEARCH.md Pattern 3):
```python
def agi_proximity(
    model_sessions: list[dict],
    human_sessions: list[dict],
) -> float | None:
    """SCORE-03: model_avg_efficiency / human_avg_efficiency.

    Returns None when no human baseline (D-10) or human_avg == 0.0 (Pitfall 5).
    Terminal display shows 'N/A'; JSON stores null (D-12).
    """
    if not human_sessions:
        return None
    model_avg = sum(efficiency_score(s) for s in model_sessions) / len(model_sessions)
    human_avg = sum(efficiency_score(s) for s in human_sessions) / len(human_sessions)
    if human_avg == 0.0:
        return None
    return model_avg / human_avg
```

**TypedDict for ScoreReport** (mirrors `SessionRecord`/`AttemptEntry` pattern from `schema.py`):
```python
class TierStats(TypedDict):
    sessions: int
    success_rate: float
    avg_efficiency: float
    agi_proximity: Optional[float]  # None renders as null in JSON, "N/A" in terminal

class ScoreReport(TypedDict):
    model: Optional[str]
    sessions_scored: int
    by_difficulty: dict[str, TierStats]
    totals: TierStats
    generated_at: str
```

---

### `cipherbench/scoring/reporter.py` (utility, request-response)

**Analog:** `cipherbench/session/human_runner.py`

This is the closest exact analog — `human_runner.py` contains `_show_puzzle_header`, `_show_attempt_history`, and `_show_score_line`, all using `Console()`, `Panel()`, and `Table()` with `add_column`/`add_row`. `reporter.py` uses the same three Rich components in the same style.

**Module docstring pattern** (`human_runner.py` lines 1-13):
```python
"""CipherBench scoring reporter — Rich terminal output for score reports (D-11).

Public names:
  render_score_report  — print Rich Panel + Table for a ScoreReport
  render_live_summary  — print one-line summary for end of cipherbench run (D-03)

Design decisions:
  D-11  Rich Panel header: model name + session count
  D-11  Rich Table columns: Difficulty | Sessions | Success Rate | Avg Efficiency | AGI Proximity
  D-03  Live summary: one typer.echo line only — no Rich components
"""
```

**Imports pattern** (`human_runner.py` lines 17-30):
```python
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()
```

**Panel + Table core pattern** (`human_runner.py` `_show_puzzle_header` lines 43-64, `_show_attempt_history` lines 67-105):
```python
def render_score_report(report: "ScoreReport", model: str) -> None:
    """Print Rich Panel header + per-difficulty Table to terminal (D-11)."""
    # Panel header — matches _show_puzzle_header style
    _console.print(
        Panel(
            f"Model: {model}  |  Sessions scored: {report['sessions_scored']}",
            title="[bold]CipherBench Score Report[/bold]",
        )
    )

    # Table — matches _show_attempt_history style (show_header=True, header_style="bold")
    table = Table(title="Score Breakdown", show_header=True, header_style="bold")
    table.add_column("Difficulty", min_width=10)
    table.add_column("Sessions", justify="right", min_width=8)
    table.add_column("Success Rate", justify="right", min_width=12)
    table.add_column("Avg Efficiency", justify="right", min_width=14)
    table.add_column("AGI Proximity", justify="right", min_width=13)

    for tier, stats in report["by_difficulty"].items():
        proximity_str = (
            f"{stats['agi_proximity']:.2f}x"
            if stats["agi_proximity"] is not None
            else "N/A"
        )
        table.add_row(
            tier,
            str(stats["sessions"]),
            f"{stats['success_rate']:.0%}",
            f"{stats['avg_efficiency']:.2f}",
            proximity_str,
        )

    # Totals row — bold to distinguish
    totals = report["totals"]
    proximity_str = (
        f"{totals['agi_proximity']:.2f}x"
        if totals["agi_proximity"] is not None
        else "N/A"
    )
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{totals['sessions']}[/bold]",
        f"[bold]{totals['success_rate']:.0%}[/bold]",
        f"[bold]{totals['avg_efficiency']:.2f}[/bold]",
        f"[bold]{proximity_str}[/bold]",
    )
    _console.print(table)

    # D-10 hint when no baseline available
    if totals["agi_proximity"] is None:
        _console.print(
            "[dim]Hint: Run `cipherbench play` to record a human baseline.[/dim]"
        )
```

**Color pattern** (`human_runner.py` `_show_score_line` lines 108-125 — same inline Rich markup style):
```python
# Row color convention (matches human_runner.py):
# green  → success rows
# yellow → partial / mid-tier
# dim    → totals label or hints
# red    → N/A or failure-heavy tiers
```

**Live summary pattern** (`human_runner.py` uses `typer.echo` for single-line output, `app.py` lines 103-106):
```python
def render_live_summary(
    sessions: list[dict],
    human_sessions: list[dict],
) -> None:
    """Print one-line summary at end of cipherbench run (D-03).

    Format: "3/5 success (60%) | avg efficiency: 0.72 | AGI proximity: 0.85x"
    Uses typer.echo (not Rich console) to keep run output clean.
    """
    # Import here to avoid circular dependency if needed
    from cipherbench.scoring.scorer import success_rate, efficiency_score, agi_proximity

    total = len(sessions)
    successes = sum(1 for s in sessions if s["outcome"] == "success")
    sr = success_rate(sessions)
    avg_eff = (
        sum(efficiency_score(s) for s in sessions) / total if total else 0.0
    )
    proximity = agi_proximity(sessions, human_sessions)
    proximity_str = f"{proximity:.2f}x" if proximity is not None else "N/A"
    typer.echo(
        f"{successes}/{total} success ({sr:.0%}) | "
        f"avg efficiency: {avg_eff:.2f} | AGI proximity: {proximity_str}"
    )
```

---

### `cipherbench/scoring/report_writer.py` (utility, file-I/O)

**Analog:** `cipherbench/session/writer.py`

`writer.py` owns all `json.dump` + `pathlib` write logic. `report_writer.py` uses the same `json.dump` with `indent=2, ensure_ascii=False`. No atomic write needed here (report is a one-shot write, not a checkpoint), but `pathlib.Path` construction is identical.

**Module docstring pattern** (`writer.py` lines 1-16):
```python
"""CipherBench scoring report writer — JSON file output for score reports (D-12).

Public names:
  write_json_report  — write a ScoreReport dict to a file as JSON

Design decisions:
  D-12  JSON report structure: model, sessions_scored, by_difficulty, totals, generated_at
  D-12  agi_proximity stored as null (not the string "N/A") in JSON output
"""
```

**Imports pattern** (`writer.py` lines 17-27):
```python
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
```

**JSON write pattern** (`writer.py` `_atomic_write_json` lines 30-48 — simplified, no atomic needed):
```python
def write_json_report(report: dict, output_file: Path) -> None:
    """Write *report* to *output_file* as JSON (D-12).

    Creates parent directories if needed (matches writer.py pattern).
    agi_proximity values that are None are serialized as JSON null (D-12).
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Score report written to %s", output_file)
```

**Timestamp pattern** (`writer.py` lines 72-73, 130-133):
```python
# ISO 8601 UTC timestamp for generated_at field (matches completed_at in writer.py)
generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
```

---

### `cipherbench/cli/app.py` (controller — modification, adding `score` subcommand)

**Analog:** itself — the existing `run_command` (lines 74-106) and `play_command` (lines 114-132)

The `score_command` must follow the exact same Typer pattern: `@app.command(name=...)`, `Annotated[]` flags, `= None` defaults for optional flags, no business logic inside the function body.

**Existing subcommand pattern to copy exactly** (`app.py` lines 74-106):
```python
@app.command(name="run")
def run_command(
    model: Annotated[str, typer.Option("--model", help="LiteLLM model string, e.g. anthropic/claude-opus-4-7")],
    seed: Annotated[Optional[int], typer.Option("--seed", help="RNG seed (default: random)")] = None,
    num_puzzles: Annotated[int, typer.Option("--num-puzzles", help="Number of distinct puzzles to run")] = 1,
    runs_per_puzzle: Annotated[int, typer.Option("--runs-per-puzzle", help="Independent sessions per puzzle")] = 1,
    difficulty: Annotated[Difficulty, typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = Difficulty.medium,
    output_dir: Annotated[str, typer.Option("--output-dir", help="Directory to write session JSON files")] = "./sessions",
    litellm_config: Annotated[Optional[str], typer.Option("--litellm-config", help="Path to LiteLLM config.yaml")] = None,
) -> None:
    """Run a model benchmark session on a cipher puzzle (SESS-01)."""
```

**Score subcommand to add** (`app.py` — new block after `play_command`):
```python
@app.command(name="score")
def score_command(
    model: Annotated[Optional[str], typer.Option("--model", help="LiteLLM model string to score")] = None,
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
    difficulty: Annotated[Optional[Difficulty], typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = None,
    output_file: Annotated[Optional[str], typer.Option("--output-file", help="Write JSON report to this path")] = None,
    human: Annotated[bool, typer.Option("--human/--no-human", help="Score human sessions instead of model sessions")] = False,
) -> None:
    """Compute scoring report for a model or human player (SCORE-01 through SCORE-04)."""
    # No business logic here — delegate entirely to scorer + reporter + report_writer
    from cipherbench.scoring.scorer import load_sessions, compute_report
    from cipherbench.scoring.reporter import render_score_report
    from cipherbench.scoring.report_writer import write_json_report

    runner_type = "human" if human else "model"
    sessions_path = Path(sessions_dir).resolve()  # ASVS V5: resolve path traversal
    diff_str = difficulty.value if difficulty is not None else None

    model_sessions = load_sessions(sessions_path, runner_type=runner_type, model=model, difficulty=diff_str)
    human_sessions = load_sessions(sessions_path, runner_type="human", difficulty=diff_str) if not human else []

    if not model_sessions:
        typer.echo("No terminal sessions found matching the given filters.", err=True)
        raise typer.Exit(code=1)

    report = compute_report(model_sessions, human_sessions, model_str=model)
    render_score_report(report, model=model or "human")

    if output_file:
        write_json_report(report, Path(output_file))
```

**Optional enum flag pattern** (verified from `app.py` line 82 — `litellm_config: Annotated[Optional[str], typer.Option(...)] = None`):
```python
# Optional[Difficulty] with None default — Typer handles this via Annotated[]
difficulty: Annotated[Optional[Difficulty], typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = None
```

**Live summary injection point** (`app.py` `run_command` lines 95-106 — inject AFTER the outer loop):
```python
    for puzzle_idx in range(num_puzzles):
        puzzle_seed = ...
        for run_idx in range(runs_per_puzzle):
            ...
            typer.echo(f"Puzzle {puzzle_idx + 1}/...")

    # INJECT HERE — after both loops:
    from cipherbench.scoring.scorer import load_sessions, compute_report
    from cipherbench.scoring.reporter import render_live_summary
    completed_sessions = load_sessions(out_path, runner_type="model", model=model)
    human_baseline = load_sessions(out_path, runner_type="human")
    render_live_summary(completed_sessions, human_baseline)
```

---

### `tests/unit/test_scoring/test_scorer.py` (test, batch + property)

**Analog:** `tests/unit/test_session/test_model_runner.py` (role-match) + `tests/conftest.py` (fixtures)

**Module header pattern** (`test_model_runner.py` lines 1-16):
```python
"""Unit tests for scoring formulas — SCORE-01, SCORE-02, SCORE-03, SCORE-04."""
from __future__ import annotations

import json
import pytest

scorer_mod = pytest.importorskip("cipherbench.scoring.scorer")
load_sessions = scorer_mod.load_sessions
efficiency_score = scorer_mod.efficiency_score
success_rate = scorer_mod.success_rate
group_by_difficulty = scorer_mod.group_by_difficulty
agi_proximity = scorer_mod.agi_proximity
compute_report = scorer_mod.compute_report
```

**`tmp_sessions_dir` fixture** — already available in `tests/conftest.py` (line 66-68):
```python
@pytest.fixture
def tmp_sessions_dir(tmp_path):
    """Temporary sessions directory, unique per test."""
    return tmp_path / "sessions"
```

**Session fixture pattern** (build minimal `SessionRecord` dicts for formula tests — no disk I/O needed):
```python
def _make_session(outcome: str, attempts_used: int, extraction_failures: int = 0, difficulty: str = "easy") -> dict:
    """Build a minimal SessionRecord dict for unit testing formulas."""
    attempts = []
    for i in range(extraction_failures):
        attempts.append({
            "attempt_num": i + 1,
            "probe": None,
            "score": None,
            "max_score": 5,
            "is_correct": False,
            "raw_response": "invalid",
            "extraction_failed": True,
        })
    for i in range(attempts_used):
        attempts.append({
            "attempt_num": extraction_failures + i + 1,
            "probe": "AAAAA",
            "score": 0,
            "max_score": 5,
            "is_correct": (outcome == "success" and i == attempts_used - 1),
            "raw_response": "PROBE: AAAAA",
            "extraction_failed": False,
        })
    return {
        "session_id": "test-session",
        "runner_type": "model",
        "model": "test/model",
        "player_name": None,
        "seed": 42,
        "difficulty": difficulty,
        "puzzle_hash": "abc123",
        "outcome": outcome,
        "final_answer": None,
        "attempts": attempts,
        "created_at": "2026-05-29T00:00:00Z",
        "completed_at": "2026-05-29T00:01:00Z",
    }
```

**Test function style** (`test_model_runner.py` lines 23-46 — function name, docstring, assert pattern):
```python
def test_efficiency_score_success_first_attempt():
    """SCORE-02: success on attempt 1 → efficiency = (5-1+1)/5 = 1.0."""
    session = _make_session(outcome="success", attempts_used=1)
    assert efficiency_score(session) == 1.0

def test_efficiency_score_failure():
    """SCORE-02: any failed session → efficiency = 0.0 regardless of attempts_used."""
    session = _make_session(outcome="failure", attempts_used=5)
    assert efficiency_score(session) == 0.0

def test_efficiency_extraction_failures_excluded():
    """SCORE-02: D-06 — extraction_failed=True attempts not counted in attempts_used."""
    session = _make_session(outcome="failure", attempts_used=5, extraction_failures=3)
    # 3 extraction failures + 5 valid → attempts_used=5, not 8
    assert efficiency_score(session) == 0.0
```

**Hypothesis property-based test pattern** (from RESEARCH.md Validation Architecture):
```python
from hypothesis import given, strategies as st

@given(
    outcome=st.sampled_from(["success", "failure"]),
    attempts_used=st.integers(min_value=0, max_value=5),
)
def test_efficiency_score_in_range(outcome, attempts_used):
    """SCORE-02 property: efficiency is always in [0.0, 1.0]."""
    session = _make_session(outcome=outcome, attempts_used=attempts_used)
    result = efficiency_score(session)
    assert 0.0 <= result <= 1.0
```

**`load_sessions` disk-based test pattern** (`test_writer.py` lines 18-23 — use `tmp_sessions_dir` + write JSON then assert):
```python
def test_load_sessions_skips_non_terminal(tmp_sessions_dir):
    """D-04: load_sessions skips in_progress and rate_limited sessions."""
    tmp_sessions_dir.mkdir(parents=True)
    for outcome in ("in_progress", "rate_limited"):
        path = tmp_sessions_dir / f"{outcome}.json"
        path.write_text(json.dumps({
            "outcome": outcome, "runner_type": "model", "model": "test/model",
            "difficulty": "easy", "attempts": [],
        }))
    result = load_sessions(tmp_sessions_dir, runner_type="model", model="test/model")
    assert result == []
```

**CLI help test pattern** (`test_commands.py` lines 17-19):
```python
def test_score_command_help_exits_zero():
    """cipherbench score --help exits with code 0."""
    result = CliRunner().invoke(app, ["score", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.output
    assert "--sessions-dir" in result.output
    assert "--difficulty" in result.output
    assert "--output-file" in result.output
    assert "--human" in result.output
```

---

### `tests/unit/test_scoring/test_report_writer.py` (test, file-I/O)

**Analog:** `tests/unit/test_session/test_writer.py` (exact match — both test JSON file writing)

**Module header pattern** (`test_writer.py` lines 1-9):
```python
"""Unit tests for report_writer — D-12 JSON report file output."""
from __future__ import annotations

import json
import pytest

writer_mod = pytest.importorskip("cipherbench.scoring.report_writer")
write_json_report = writer_mod.write_json_report
```

**File write + read-back pattern** (`test_writer.py` lines 18-23):
```python
def test_write_json_report_creates_file(tmp_path):
    """write_json_report creates the file and writes valid JSON."""
    report = {
        "model": "test/model",
        "sessions_scored": 3,
        "by_difficulty": {
            "easy": {"sessions": 3, "success_rate": 0.67, "avg_efficiency": 0.6, "agi_proximity": None}
        },
        "totals": {"sessions": 3, "success_rate": 0.67, "avg_efficiency": 0.6, "agi_proximity": None},
        "generated_at": "2026-05-29T00:00:00Z",
    }
    out = tmp_path / "report.json"
    write_json_report(report, out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["model"] == "test/model"
    assert data["totals"]["agi_proximity"] is None  # D-12: null not string "N/A"
```

**Overwrite/idempotency test** (`test_writer.py` lines 26-32):
```python
def test_write_json_report_overwrites_existing(tmp_path):
    """write_json_report overwrites an existing file without error."""
    out = tmp_path / "report.json"
    write_json_report({"model": "first"}, out)
    write_json_report({"model": "second"}, out)
    assert json.loads(out.read_text())["model"] == "second"
```

**Parent directory creation test** (`test_writer.py` analog — `_atomic_write_json` creates parents via `path.parent.mkdir`):
```python
def test_write_json_report_creates_parent_dirs(tmp_path):
    """write_json_report creates intermediate directories if needed."""
    out = tmp_path / "nested" / "deep" / "report.json"
    write_json_report({"model": "test"}, out)
    assert out.exists()
```

---

## Shared Patterns

### Package Init (empty marker)
**Source:** `cipherbench/session/__init__.py` (1-line empty file)
**Apply to:** `cipherbench/scoring/__init__.py` — use as empty marker OR add docstring + `__all__` (follow `cipherbench/__init__.py` pattern for public API exports)

### Logging
**Source:** `cipherbench/session/writer.py` lines 27-27, `model_runner.py` lines 40-40
**Apply to:** `scorer.py`, `report_writer.py`
```python
import logging
logger = logging.getLogger(__name__)
```

### `from __future__ import annotations`
**Source:** Every existing module in `cipherbench/` (lines 1 of `writer.py`, `model_runner.py`, `human_runner.py`, `schema.py`)
**Apply to:** All new `scoring/` modules and test files

### Path safety (ASVS V5)
**Source:** `model_runner.py` line 201 (`output_dir = Path(output_dir)`) + RESEARCH.md security section
**Apply to:** `cli/app.py` `score_command` — `Path(sessions_dir).resolve()` to prevent path traversal
```python
sessions_path = Path(sessions_dir).resolve()
```

### `pytest.importorskip` guard
**Source:** `test_model_runner.py` line 10, `test_writer.py` line 8, `test_commands.py` lines 7-8
**Apply to:** All new `tests/unit/test_scoring/` files — guard the import so missing modules skip gracefully:
```python
scorer_mod = pytest.importorskip("cipherbench.scoring.scorer")
```

### JSON dump options
**Source:** `writer.py` line 41 — `json.dump(data, f, indent=2, ensure_ascii=False)`
**Apply to:** `report_writer.py` `write_json_report` — same flags for human-readable, unicode-safe output

### `typer.echo` for CLI output (not `print`)
**Source:** `app.py` lines 103-106, `human_runner.py` `run()` lines 238, 248
**Apply to:** `render_live_summary` in `reporter.py` — use `typer.echo` not `print` for single-line output; `_console.print` for Rich-formatted output

### Module-private Rich console singleton
**Source:** `human_runner.py` line 33 — `_console = Console()` at module level
**Apply to:** `reporter.py` — single `_console = Console()` instance, module-private

### `Optional[str] = None` flag pattern
**Source:** `app.py` line 82 — `litellm_config: Annotated[Optional[str], typer.Option(...)] = None`
**Apply to:** `score_command` `--output-file`, `--model`, `--difficulty` flags

### Docstring no-business-logic contract
**Source:** `app.py` line 3 — `"""No business logic here — this module is a coordinator that delegates to session runners."""`
**Apply to:** `score_command` docstring must include: "No business logic here — delegates to scorer + reporter + report_writer"

---

## No Analog Found

All 7 files have close analogs. No new patterns are required from RESEARCH.md only.

| File | Role | Data Flow | Status |
|------|------|-----------|--------|
| `tests/unit/test_scoring/__init__.py` | package-init | n/a | Empty marker — copy `tests/unit/test_session/__init__.py` exactly (zero bytes) |

---

## Metadata

**Analog search scope:** `cipherbench/session/`, `cipherbench/cli/`, `tests/unit/test_session/`, `tests/unit/test_cli/`, `tests/conftest.py`, `cipherbench/__init__.py`
**Files scanned:** 11 source files read in full
**Pattern extraction date:** 2026-05-29
