# Phase 5: Session Inspector - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 4
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `cipherbench/session/inspector.py` | service | file-I/O + request-response | `cipherbench/scoring/scorer.py` (session loading) + `cipherbench/scoring/reporter.py` (Rich rendering) | exact (composite) |
| `cipherbench/cli/app.py` | controller | request-response | `cipherbench/cli/app.py` `score_command` | exact |
| `cipherbench/__init__.py` | config | n/a | `cipherbench/__init__.py` existing export block | exact |
| `tests/unit/test_session/test_inspector.py` | test | n/a | `tests/unit/test_scoring/test_reporter.py` + `tests/unit/test_cli/test_commands.py` | exact (composite) |

---

## Pattern Assignments

### `cipherbench/session/inspector.py` (service, file-I/O + request-response)

**Primary analogs:** `cipherbench/scoring/scorer.py` (glob + JSON load pattern) and `cipherbench/scoring/reporter.py` (Rich Panel + Table + `_console` module-level variable)
**Secondary analog:** `cipherbench/session/human_runner.py` (Rich Table columns and row styling)

---

#### Imports pattern

**Source:** `cipherbench/scoring/reporter.py` lines 1-24 combined with `cipherbench/scoring/scorer.py` lines 19-27

```python
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()
```

Key points:
- `from __future__ import annotations` is used in every module in the codebase — required.
- `_console = Console()` at module level (not inside a function) matches `reporter.py` line 24 and `human_runner.py` line 33. Tests monkeypatch this name.
- No `logging` import needed — inspector is read-only display logic, no state transitions to log.

---

#### Module-level `_console` pattern for testability

**Source:** `cipherbench/scoring/reporter.py` lines 24, 77-84 (usage) and `tests/unit/test_scoring/test_reporter.py` lines 77-84 (monkeypatch)

```python
# reporter.py line 24
_console = Console()

# reporter.py lines 38-43 — all output goes through _console, never print()
_console.print(
    Panel(
        f"Model: {model}  |  Sessions scored: {report['sessions_scored']}",
        title="[bold]CipherBench Score Report[/bold]",
    )
)

# reporter.py line 81
_console.print(table)
```

Test captures output by monkeypatching `_console`:

```python
# test_reporter.py lines 77-84
def _capture_render_score_report(report, model, monkeypatch):
    from rich.console import Console
    captured = io.StringIO()
    mock_console = Console(file=captured, force_terminal=False, width=120)
    monkeypatch.setattr(reporter_mod, "_console", mock_console)
    render_score_report(report, model)
    return captured.getvalue()
```

Inspector must follow the same pattern: all `console.print()` calls use the injected or module-level `_console`, never `print()`.

---

#### Session glob + JSON load pattern

**Source:** `cipherbench/scoring/scorer.py` lines 79-109

```python
# scorer.py lines 79-89 — glob then open; skip malformed silently
if not sessions_dir.exists():
    return []

sessions = []
for path in sessions_dir.glob("*.json"):
    try:
        with path.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # skip malformed or unreadable files silently
        continue
```

Inspector diverges at one point: match on `path.stem` before deserializing (faster; no need to open files just to match session_id):

```python
# Derived from scorer.py — stem match before JSON load
all_paths = list(sessions_dir.glob("*.json"))
matches = [p for p in all_paths if session_id.lower() in p.stem.lower()]
```

Only the single matched file is opened with `json.load()`.

---

#### Rich Panel header pattern

**Source:** `cipherbench/scoring/reporter.py` lines 38-43

```python
_console.print(
    Panel(
        f"Model: {model}  |  Sessions scored: {report['sessions_scored']}",
        title="[bold]CipherBench Score Report[/bold]",
    )
)
```

Also: `cipherbench/session/human_runner.py` lines 57-64:

```python
body = (
    f"Seed: {seed}\n"
    f"Difficulty: {difficulty_name}\n"
    f"Alphabet: {alphabet}\n\n"
    f"PROBE: submit as  PROBE: {'X' * output_length}\n"
    f"ANSWER: submit as  ANSWER: {'X' * output_length}"
)
_console.print(Panel(body, title="[bold]CipherBench[/bold]"))
```

Inspector Panel pattern (D-03): multi-line body string passed to `Panel(body, title="[bold]...[/bold]")`. Title uses `[bold]` Rich markup. Body uses `\n`-joined f-string lines, not Rich markup inside the body.

---

#### Rich Table pattern

**Source:** `cipherbench/scoring/reporter.py` lines 46-65 (columns + rows) and `cipherbench/session/human_runner.py` lines 80-105

```python
# reporter.py lines 46-51 — Table constructor and column definitions
table = Table(title="Score Breakdown", show_header=True, header_style="bold")
table.add_column("Difficulty", min_width=10)
table.add_column("Sessions", justify="right", min_width=8)
table.add_column("Success Rate", justify="right", min_width=12)
table.add_column("Avg Efficiency", justify="right", min_width=14)
table.add_column("AGI Proximity", justify="right", min_width=13)

# reporter.py lines 53-65 — row addition
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
```

```python
# human_runner.py lines 80-105 — table with row styling
table = Table(title="Attempt History", show_header=True, header_style="bold")
table.add_column("#", style="dim", width=4)
table.add_column("Probe", min_width=8)
table.add_column("Score", min_width=8)

for a in attempts:
    probe_str = a.get("probe") or "INVALID"
    score = a.get("score")
    is_correct = a.get("is_correct", False)

    if score is None:
        score_str = "N/A"
        row_style = "red"
    elif is_correct:
        score_str = f"[green]{score}/{max_score}[/green]"
        row_style = "green"
    elif score > 0:
        score_str = f"[yellow]{score}/{max_score}[/yellow]"
        row_style = "yellow"
    else:
        score_str = f"[red]{score}/{max_score}[/red]"
        row_style = "red"

    table.add_row(str(a["attempt_num"]), probe_str, score_str, style=row_style if not is_correct else None)

_console.print(table)
```

Inspector table (D-04, D-05): same `Table(title=..., show_header=True, header_style="bold")` constructor. Row styling uses `style=` keyword on `add_row()`, same as `human_runner.py` line 103. Extraction-failure rows use `style="red"`; successful-probe rows use `style="green"`.

---

#### Error handling pattern

**Source:** `cipherbench/cli/app.py` lines 175-177

```python
if not model_sessions:
    typer.echo("No terminal sessions found matching the given filters.", err=True)
    raise typer.Exit(code=1)
```

Inspector module (`inspector.py`) uses `SystemExit(1)` instead of `typer.Exit` (which is a Typer-layer construct). The `console.print(..., style="red")` call precedes the raise. This keeps `app.py` thin — it passes `Console()` in and the inspector module handles all output and error exits:

```python
# Pattern for inspector.py error branches
console.print("Error message here", style="red")
raise SystemExit(1)
```

---

#### `AttemptEntry` field access pattern

**Source:** `cipherbench/session/schema.py` lines 23-54 (field definitions) and `cipherbench/scoring/scorer.py` line 120 (dict `.get()` usage)

```python
# scorer.py line 120 — .get() with default for optional fields
attempts_used = sum(
    1 for a in session.get("attempts", []) if not a.get("extraction_failed", False)
)
```

Since sessions are loaded from JSON (plain `dict`, not `TypedDict` instances), all field access uses `.get()` with defaults. The authoritative field for extraction failures is `extraction_failed` (bool), not `probe is None`. Key fields:

- `entry.get("extraction_failed")` — authoritative flag for D-05
- `entry.get("attempt_num", "?")` — 1-indexed
- `entry.get("probe")` — `Optional[str]`, None when extraction failed
- `entry.get("score")` — `Optional[int]`
- `entry.get("max_score", "?")` — int
- `entry.get("is_correct", False)` — bool

---

### `cipherbench/cli/app.py` — MODIFY: add `inspect` subcommand (controller, request-response)

**Analog:** `cipherbench/cli/app.py` `score_command` (lines 155-189)

---

#### Imports pattern (existing — no new imports needed at module level)

**Source:** `cipherbench/cli/app.py` lines 14-27

```python
import random
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from cipherbench.puzzle import EASY, MEDIUM, HARD
from cipherbench.types import DifficultyConfig
from cipherbench.session.model_runner import create_model_session
from cipherbench.session.human_runner import create_human_session
from cipherbench.adapters.litellm_adapter import LiteLLMAdapter
```

`inspect_command` uses lazy imports inside the function body (same as `score_command` lines 164-167), so no new top-level imports are needed. `Path` and `Annotated` and `typer` are already imported.

---

#### Typer `Annotated[]` command pattern

**Source:** `cipherbench/cli/app.py` lines 155-162 (`score_command` signature)

```python
@app.command(name="score")
def score_command(
    model: Annotated[Optional[str], typer.Option("--model", help="LiteLLM model string to score")] = None,
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
    difficulty: Annotated[Optional[Difficulty], typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = None,
    output_file: Annotated[Optional[str], typer.Option("--output-file", help="Write JSON report to this path")] = None,
    human: Annotated[bool, typer.Option("--human/--no-human", help="Score human sessions instead of model sessions")] = False,
) -> None:
    """Compute scoring report for a model or human player (SCORE-01 through SCORE-04). No business logic here — delegates to scorer + reporter + report_writer."""
```

`inspect_command` signature difference: `session_id` is a positional argument (`typer.Argument`), not a flag. Only `score_command`-equivalent for `sessions_dir` is `typer.Option`. Pattern:

```python
@app.command(name="inspect")
def inspect_command(
    session_id: Annotated[str, typer.Argument(help="Session ID or substring to match")],
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
) -> None:
    """Replay a stored session trace, displaying all probe attempts and final outcome (SESS-03)."""
```

---

#### Path resolution + lazy import pattern

**Source:** `cipherbench/cli/app.py` lines 163-169

```python
from cipherbench.scoring.scorer import load_sessions, compute_report
from cipherbench.scoring.reporter import render_score_report
from cipherbench.scoring.report_writer import write_json_report

runner_type = "human" if human else "model"
sessions_path = Path(sessions_dir).resolve()  # ASVS V5: resolve prevents path traversal (T-04-06)
```

Inspector follows exactly the same two-step pattern: lazy import inside function body, then `Path(...).resolve()` before passing to the module:

```python
def inspect_command(...) -> None:
    """..."""
    from cipherbench.session.inspector import inspect_session
    from rich.console import Console

    resolved = Path(sessions_dir).resolve()  # ASVS V5: path traversal prevention (T-04-06)
    inspect_session(session_id, resolved, Console())
```

The comment `# ASVS V5: resolve prevents path traversal (T-04-06)` is used verbatim in `score_command` (line 169) — use the same comment text in `inspect_command` for consistency.

---

#### Error exit pattern in CLI layer

**Source:** `cipherbench/cli/app.py` lines 175-177 and lines 185-189

```python
if not model_sessions:
    typer.echo("No terminal sessions found matching the given filters.", err=True)
    raise typer.Exit(code=1)
```

```python
except OSError as exc:
    typer.echo(f"Error: could not write report: {exc}", err=True)
    raise typer.Exit(code=1)
```

Inspector error exits come from `SystemExit(1)` raised inside `inspector.py` — the CLI layer (`inspect_command`) does NOT need its own `raise typer.Exit` because `SystemExit` propagates through Typer's `CliRunner` as `exit_code=1`.

---

### `cipherbench/__init__.py` — MODIFY: export `inspect_session` (config)

**Analog:** `cipherbench/__init__.py` lines 17-24 and lines 25-41 (existing export block)

---

#### Existing export pattern

**Source:** `cipherbench/__init__.py` lines 1-41

```python
"""CipherBench — AGI Proximity Benchmark.

Public API surface. Import from here; internal module paths are implementation detail.

Available:
    ...
    load_sessions     — load and filter terminal sessions from a directory
    compute_report    — aggregate all metrics into a ScoreReport dict
    ScoreReport       — TypedDict: the structured scoring result
"""
from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
from cipherbench.puzzle import Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD
from cipherbench.scoring.scorer import load_sessions, compute_report, ScoreReport

__all__ = [
    "AttemptScore",
    "DifficultyConfig",
    "RuleEngine",
    "create_rule_engine",
    "Puzzle",
    "generate_puzzle",
    "verify_puzzle",
    "get_tier",
    "EASY",
    "MEDIUM",
    "HARD",
    "load_sessions",
    "compute_report",
    "ScoreReport",
]
```

Add `inspect_session` by appending:
1. One line to the module docstring's "Available:" list: `    inspect_session   — replay a stored session trace to terminal (SESS-03)`
2. One import line: `from cipherbench.session.inspector import inspect_session`
3. One entry in `__all__`: `"inspect_session",`

The import goes after the `scorer` import line (alphabetical by module path: `session` comes before `scoring` alphabetically but after in practice — match the existing ordering convention, which is by layer: types → engine → puzzle → scoring → session).

---

### `tests/unit/test_session/test_inspector.py` (test)

**Primary analog:** `tests/unit/test_scoring/test_reporter.py` (monkeypatch `_console` for Rich output capture)
**Secondary analog:** `tests/unit/test_cli/test_commands.py` (`CliRunner().invoke(app, [...])` pattern)

---

#### Module guard pattern

**Source:** `tests/unit/test_scoring/test_reporter.py` lines 10-12 and `tests/unit/test_cli/test_commands.py` lines 6-9

```python
# test_reporter.py lines 10-12
reporter_mod = pytest.importorskip("cipherbench.scoring.reporter")
render_score_report = reporter_mod.render_score_report
render_live_summary = reporter_mod.render_live_summary
```

```python
# test_commands.py lines 6-9
pytest.importorskip("cipherbench.cli.app")
from typer.testing import CliRunner
from cipherbench.cli.app import app
```

Inspector test file should use `pytest.importorskip` to guard against the module not existing yet:

```python
import pytest
inspector_mod = pytest.importorskip("cipherbench.session.inspector")
inspect_session = inspector_mod.inspect_session
display_session = inspector_mod.display_session
```

---

#### Session fixture factory pattern

**Source:** `tests/unit/test_scoring/test_reporter.py` lines 15-51

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

Reuse `_make_session` verbatim in `test_inspector.py` (copy from `test_reporter.py`). Extend it with a `final_answer` parameter to test D-06 footer variations.

---

#### `_console` monkeypatch capture pattern

**Source:** `tests/unit/test_scoring/test_reporter.py` lines 77-84

```python
def _capture_render_score_report(report, model, monkeypatch):
    from rich.console import Console
    captured = io.StringIO()
    mock_console = Console(file=captured, force_terminal=False, width=120)
    monkeypatch.setattr(reporter_mod, "_console", mock_console)
    render_score_report(report, model)
    return captured.getvalue()
```

Inspector capture helper follows the same pattern:

```python
import io
from rich.console import Console

def _capture_display_session(session, monkeypatch):
    captured = io.StringIO()
    mock_console = Console(file=captured, force_terminal=False, width=120)
    monkeypatch.setattr(inspector_mod, "_console", mock_console)
    display_session(session, mock_console)
    return captured.getvalue()
```

Note: `display_session` takes `console` as a required parameter (not optional), so pass `mock_console` directly rather than relying on the monkeypatched module-level `_console`. Both approaches are valid; the direct-parameter approach is simpler for `display_session` tests.

---

#### CliRunner integration test pattern

**Source:** `tests/unit/test_cli/test_commands.py` lines 17-56

```python
def test_run_command_help_exits_zero():
    result = CliRunner().invoke(app, ["run", "--help"])
    assert result.exit_code == 0

def test_run_command_shows_model_flag():
    result = CliRunner().invoke(app, ["run", "--help"])
    assert "--model" in result.output
```

Inspector CLI tests follow the same pattern with `tmp_path` for sessions directories:

```python
from typer.testing import CliRunner
from cipherbench.cli.app import app
import json

def _write_session(tmp_dir, session_id: str, session: dict):
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / f"{session_id}.json").write_text(json.dumps(session))

def test_inspect_command_help_exits_zero():
    result = CliRunner().invoke(app, ["inspect", "--help"])
    assert result.exit_code == 0
    assert "--sessions-dir" in result.output
```

---

#### `tmp_sessions_dir` fixture

**Source:** `tests/conftest.py` lines 65-68

```python
@pytest.fixture
def tmp_sessions_dir(tmp_path):
    """Temporary sessions directory, unique per test."""
    return tmp_path / "sessions"
```

This fixture is already available to all tests without import. Use it in inspector tests that need a sessions directory:

```python
def test_inspect_missing_dir_exits_one(tmp_sessions_dir):
    result = CliRunner().invoke(app, ["inspect", "any", "--sessions-dir", str(tmp_sessions_dir)])
    assert result.exit_code == 1
```

---

## Shared Patterns

### Authentication
**Not applicable.** CipherBench is a single-user local CLI with no authentication layer.

### Error handling with exit code 1
**Source:** `cipherbench/cli/app.py` lines 175-177 (CLI layer) and established discipline in `scorer.py` lines 79-89 (service layer)
**Apply to:** `cipherbench/session/inspector.py` (all D-08, D-09, D-10 branches) and `cipherbench/cli/app.py` `inspect_command`

```python
# Service layer (inspector.py) — SystemExit(1) after console.print with style="red"
console.print("Sessions directory not found: ...", style="red")
raise SystemExit(1)

# CLI layer (app.py) — typer.Exit(code=1) for CLI-originated errors only
typer.echo("...", err=True)
raise typer.Exit(code=1)
```

Inspector module uses `SystemExit(1)` (not `typer.Exit`) because it is not a Typer callback — it is a service module callable from both CLI and library contexts.

### `from __future__ import annotations`
**Source:** `cipherbench/scoring/scorer.py` line 19, `cipherbench/scoring/reporter.py` line 13, `cipherbench/session/human_runner.py` line 14
**Apply to:** `cipherbench/session/inspector.py` (first line of every module)

```python
from __future__ import annotations
```

### `Path(...).resolve()` path traversal prevention
**Source:** `cipherbench/cli/app.py` line 169
**Apply to:** `cipherbench/cli/app.py` `inspect_command`

```python
sessions_path = Path(sessions_dir).resolve()  # ASVS V5: resolve prevents path traversal (T-04-06)
```

Use identical comment text to `score_command` for audit consistency.

### Lazy imports inside command functions
**Source:** `cipherbench/cli/app.py` lines 118-120 (run_command) and lines 164-167 (score_command)

```python
from cipherbench.scoring.scorer import load_sessions as _load_sessions
from cipherbench.scoring.reporter import render_live_summary as _render_live_summary
```

`inspect_command` must use lazy imports for `inspect_session` and `Console`, same as all other commands.

### Module docstring format
**Source:** `cipherbench/scoring/reporter.py` lines 1-11, `cipherbench/session/human_runner.py` lines 1-13

```python
"""CipherBench <component name> — <one-line description>.

Public names:
  <name>  — <description>

Design decisions implemented here:
  D-XX  <decision summary>
"""
```

`inspector.py` module docstring must list `inspect_session` and `display_session` under "Public names" and cite D-01 through D-10 decisions under "Design decisions".

---

## No Analog Found

All four files have close analogs in the codebase. No files require fallback to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `cipherbench/scoring/`, `cipherbench/session/`, `cipherbench/cli/`, `tests/unit/test_scoring/`, `tests/unit/test_cli/`, `tests/conftest.py`, `cipherbench/__init__.py`
**Files scanned:** 8
**Pattern extraction date:** 2026-05-30
