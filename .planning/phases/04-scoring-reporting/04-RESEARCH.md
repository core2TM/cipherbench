# Phase 4: Scoring & Reporting - Research

**Researched:** 2026-05-29
**Domain:** Python statistical scoring, Rich terminal reporting, Typer CLI extension
**Confidence:** HIGH

## Summary

Phase 4 is an internal-data-only phase — no new external packages are required. The scorer reads session JSON files already on disk (written by Phase 3), applies three pure-math formulas (SCORE-01 success rate, SCORE-02 efficiency, SCORE-03 AGI proximity), groups results by difficulty tier (SCORE-04), and renders output via Rich components and a JSON file writer. Every tool in the required stack is already installed and verified.

The session JSON schema is fully locked (D-08/D-11 from Phase 3). The exact fields the scorer needs — `runner_type`, `outcome`, `difficulty`, `model`, `attempts`, and `extraction_failed` on each attempt — are confirmed from `cipherbench/session/schema.py`. The `cipherbench/cli/app.py` module is a clean Typer app with two existing subcommands (`run`, `play`) that the `score` subcommand follows exactly: `@app.command(name="score")`, flags via `Annotated[type, typer.Option()]`, no business logic in the CLI layer, and the `Difficulty` enum already defined and reusable.

The formula edge cases are analytically solved: when `attempts_used = 0` (all extraction failures), the efficiency score is 1.0 for a successful session (best-case) and 0.0 for a failed one; division-by-zero is impossible because `max_attempts = 5` is a fixed positive integer. The AGI proximity N/A case (no human baseline) is a clean guard, not an exception.

**Primary recommendation:** Implement `cipherbench/scoring/` as three pure modules (scorer.py, reporter.py, report_writer.py) with no business logic in the CLI layer. No new package installs required.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Scoring exposed two ways: (1) standalone `cipherbench score` subcommand reads sessions after the fact, and (2) a summary line is printed at the end of `cipherbench run` after all sessions complete. Both surfaces are required.
- **D-02:** `cipherbench score` flags: `--model TEXT` (required), `--sessions-dir PATH` (optional, default: `./sessions`), `--difficulty ENUM` (optional), `--output-file PATH` (optional), `--human` (flag, optional).
- **D-03:** Live summary is one line only: e.g., `"3/5 success (60%) | avg efficiency: 0.72 | AGI proximity: 0.85x"`. Full breakdown via `cipherbench score`.
- **D-04:** Session set = terminal sessions where `outcome` is `'success'` or `'failure'`, `runner_type='model'` (or `'human'` if `--human`), and `model` matches `--model`. `in_progress` and `rate_limited` sessions are skipped.
- **D-05:** If `--difficulty` given, additionally filter by `difficulty` field matching tier name string.
- **D-06:** `attempts_used` in SCORE-02 = count of attempt entries where `extraction_failed=False`. Extraction failures are not counted as reasoning steps.
- **D-07:** Multiple sessions for same seed all contribute individually. No deduplication.
- **D-08:** Human baseline matching by difficulty tier. All human sessions for same difficulty tier form the baseline pool. Does not require exact seed overlap.
- **D-09:** Composite score for AGI proximity = average efficiency score (mean of SCORE-02 values). AGI proximity = `model_avg_efficiency / human_avg_efficiency`.
- **D-10:** No human baseline: show `N/A (no human baseline)` in terminal; `null` in JSON. Include hint: "Run `cipherbench play` to record a human baseline." No error, no exit.
- **D-11:** Terminal output: Rich Panel header (model name + session count), Rich Table (Difficulty | Sessions | Success Rate | Avg Efficiency | AGI Proximity) with totals row.
- **D-12:** JSON report structure (see CONTEXT.md D-12 for exact schema). `agi_proximity` is `null` (not the string `"N/A"`) in JSON.
- **D-13:** Three modules in `cipherbench/scoring/`: `scorer.py` (pure computation), `reporter.py` (Rich terminal), `report_writer.py` (JSON file writer).

### Claude's Discretion

- Exact Rich table styling (column widths, color scheme, border style) — must match the visual quality of the Phase 3 human play display but exact colors are planner's choice.
- How `--human` flag resolves "which human" when multiple players exist — planner may add `--player-name TEXT` if needed, or aggregate all human sessions.
- Whether `agi_proximity` in JSON is a float or the string `"N/A"` — use `null` (resolved by D-12).
- Session count shown in the terminal header (total sessions found vs sessions that passed filtering).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCORE-01 | Scorer computes success rate (% of sessions where model produced correct final answer) across all sessions for a given run config | `outcome == 'success'` field in `SessionRecord`; success_rate = successes / total_terminal |
| SCORE-02 | Scorer computes efficiency score per session: `success × (max_attempts - attempts_used + 1) / max_attempts`; reports alongside success rate | `attempts` list with `extraction_failed` field; `attempts_used` = len(filter extraction_failed=False); max_attempts=5 constant |
| SCORE-03 | Scorer computes AGI proximity: model composite score normalized by human baseline composite score for same puzzle set (requires at least one recorded human baseline) | `runner_type` field discriminates human vs model sessions; D-08 match by difficulty tier; D-10 N/A handling |
| SCORE-04 | Reporter breaks down all scores by difficulty tier (easy / medium / hard) derived from puzzle config parameters | `difficulty` string field in `SessionRecord`; `Difficulty` enum already in `cli/app.py`; group sessions by this field |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session loading & filtering | `scoring/scorer.py` (library layer) | — | Pure I/O + filter logic; no display concerns; reusable from both CLI surfaces |
| Success rate computation (SCORE-01) | `scoring/scorer.py` | — | Pure math; takes a list of `SessionRecord` dicts, returns float |
| Efficiency score per session (SCORE-02) | `scoring/scorer.py` | — | Pure math on AttemptEntry list; depends on no display or I/O |
| Per-difficulty grouping (SCORE-04) | `scoring/scorer.py` | — | Group-by on `difficulty` field; returns dict keyed by tier string |
| AGI proximity normalization (SCORE-03) | `scoring/scorer.py` | — | Ratio of two avg-efficiency values; None when human pool is empty |
| Rich terminal output | `scoring/reporter.py` | — | Owns all `Console`, `Panel`, `Table` calls; no computation |
| JSON report file writing | `scoring/report_writer.py` | — | Owns `json.dump` + `pathlib` write; no computation or display |
| CLI subcommand wiring | `cli/app.py` | — | Existing Typer app; `@app.command(name="score")` added here; delegates entirely to scorer + reporter + report_writer |
| Live summary line in `cipherbench run` | `cli/app.py` `run_command()` | `scoring/scorer.py` | Injected after outer loop; calls scorer functions on just-written session files; formats one-line `typer.echo` |

---

## Standard Stack

Phase 4 introduces **no new packages**. All tooling is already installed and locked in `pyproject.toml`.

### Core (already installed)

| Library | Installed Version | Purpose | Source |
|---------|------------------|---------|--------|
| Python stdlib `json` | n/a (stdlib) | Session JSON loading; JSON report writing | [VERIFIED: codebase — writer.py uses `json.dump`] |
| Python stdlib `pathlib` | n/a (stdlib) | File path operations, glob for session discovery | [VERIFIED: codebase — writer.py, model_runner.py use `pathlib.Path`] |
| Python stdlib `glob` via `pathlib.Path.glob` | n/a (stdlib) | `sessions/*.json` discovery | [VERIFIED: codebase — `_find_resumable_session` uses `output_dir.glob`] |
| `rich` | 15.0.0 | `Console`, `Panel`, `Table` for terminal report | [VERIFIED: PyPI registry — installed 15.0.0, latest is 15.0.0] |
| `typer` | 0.23.2 | `@app.command(name="score")`, `Annotated[]` flags, `Difficulty` enum reuse | [VERIFIED: PyPI registry — installed 0.23.2, latest is 0.23.2] |
| `pytest` | 8.4.2 | Test runner for all scoring unit tests | [VERIFIED: PyPI registry — installed 8.4.2, latest is 8.4.2] |
| `hypothesis` | 6.141.1 (installed) / >=6.100 (required) | Property-based tests for scoring formulas | [VERIFIED: PyPI registry — installed 6.114.1 per CLAUDE.md; actual installed 6.141.1 per pip] |

**Installation:** No new installs needed. All packages are already in the virtual environment.

---

## Package Legitimacy Audit

Phase 4 introduces no new package installs. All packages used are pre-existing project dependencies verified in prior phases.

slopcheck was run against the 7 existing packages as a confirming check:

| Package | Registry | slopcheck | Disposition |
|---------|----------|-----------|-------------|
| rich | PyPI | [OK] | Approved (pre-existing) |
| typer | PyPI | [OK] | Approved (pre-existing) |
| pytest | PyPI | [OK] | Approved (pre-existing) |
| hypothesis | PyPI | [OK] | Approved (pre-existing) |
| litellm | PyPI | [OK] | Approved (pre-existing) |
| pytest-asyncio | PyPI | [OK] | Approved (pre-existing) |
| tenacity | PyPI | [OK] | Approved (pre-existing) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
sessions/*.json (disk)
        |
        | pathlib.Path.glob("*.json") + json.load()
        v
  scorer.load_sessions(sessions_dir, runner_type, model, difficulty)
        |
        | returns List[SessionRecord]
        v
  scorer.compute_report(sessions, human_sessions)
        |
        |-- success_rate(sessions)                 -> float       [SCORE-01]
        |-- efficiency_score(session)              -> float       [SCORE-02, per session]
        |-- group_by_difficulty(sessions)          -> dict[str, List]  [SCORE-04]
        |-- agi_proximity(model_avg, human_avg)    -> float|None  [SCORE-03]
        |
        | returns ScoreReport dataclass/dict
        v
   ┌────────────────┬──────────────────────┐
   |                |                      |
reporter.py    report_writer.py      cli/app.py (live summary)
(Rich Panel     (json.dump to         (one-line typer.echo
 + Table)       --output-file)         after run loop)
```

### Recommended Project Structure

```
cipherbench/
├── scoring/
│   ├── __init__.py          # exports: load_sessions, compute_report, ScoreReport
│   ├── scorer.py            # pure computation: load, filter, formulas, grouping
│   ├── reporter.py          # Rich Panel + Table rendering
│   └── report_writer.py     # json.dump to file
├── cli/
│   └── app.py               # adds @app.command(name="score"); calls scoring/ functions
tests/
└── unit/
    └── test_scoring/
        ├── __init__.py
        ├── test_scorer.py       # pure formula unit tests
        ├── test_reporter.py     # Rich output via CliRunner / Console capture
        └── test_report_writer.py # JSON file writing
```

### Pattern 1: Session Loading and Filtering

The existing `_find_resumable_session` in `model_runner.py` demonstrates the glob + JSON load pattern. The scorer uses the same idiom but loads ALL matching sessions rather than finding one:

```python
# Source: derived from cipherbench/session/model_runner.py _find_resumable_session pattern
# [VERIFIED: codebase]
from pathlib import Path
import json

TERMINAL_OUTCOMES = {"success", "failure"}

def load_sessions(
    sessions_dir: Path,
    runner_type: str,           # 'model' or 'human'
    model: str | None = None,   # filter by model field; None = all
    difficulty: str | None = None,  # 'easy'|'medium'|'hard'; None = all
) -> list[dict]:
    sessions = []
    for path in sessions_dir.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("outcome") not in TERMINAL_OUTCOMES:
            continue
        if data.get("runner_type") != runner_type:
            continue
        if model is not None and data.get("model") != model:
            continue
        if difficulty is not None and data.get("difficulty") != difficulty:
            continue
        sessions.append(data)
    return sessions
```

### Pattern 2: Efficiency Score Formula

The exact formula from REQUIREMENTS.md SCORE-02 and CONTEXT.md specifics section:

```python
# Source: REQUIREMENTS.md SCORE-02 + CONTEXT.md D-06
# [VERIFIED: codebase — REQUIREMENTS.md line 39, CONTEXT.md lines 133-136]
MAX_ATTEMPTS = 5  # fixed core mechanic, not configurable in v1

def efficiency_score(session: dict) -> float:
    """
    efficiency = success × (max_attempts - attempts_used + 1) / max_attempts
    attempts_used = count of attempts where extraction_failed=False (D-06)
    success = 1 if outcome='success', else 0
    """
    success = 1 if session["outcome"] == "success" else 0
    attempts_used = sum(
        1 for a in session["attempts"] if not a["extraction_failed"]
    )
    return success * (MAX_ATTEMPTS - attempts_used + 1) / MAX_ATTEMPTS
```

**Edge case analysis — extraction_failed=True for all attempts:**
- If every attempt has `extraction_failed=True`, then `attempts_used = 0`.
- For a successful session (which cannot happen if no valid probe was scored): efficiency = `1 × (5 - 0 + 1) / 5 = 1.2`. This case is mechanically impossible — the session cannot be `outcome='success'` without at least one `is_correct=True` attempt, which requires a valid probe.
- For a failed session: efficiency = `0 × 6 / 5 = 0.0`. Correct — complete failure.
- Division by zero is impossible: `MAX_ATTEMPTS = 5` is a constant positive integer. [VERIFIED: codebase — `MAX_ATTEMPTS: int = 5` in both `model_runner.py` and `human_runner.py`]

### Pattern 3: AGI Proximity with N/A Guard

```python
# Source: CONTEXT.md D-09, D-10
# [VERIFIED: codebase — CONTEXT.md]
def agi_proximity(
    model_sessions: list[dict],
    human_sessions: list[dict],
) -> float | None:
    """
    Returns model_avg_efficiency / human_avg_efficiency.
    Returns None when no human baseline exists (D-10).
    """
    if not human_sessions:
        return None  # rendered as "N/A" in terminal, null in JSON (D-12)
    model_avg = sum(efficiency_score(s) for s in model_sessions) / len(model_sessions)
    human_avg = sum(efficiency_score(s) for s in human_sessions) / len(human_sessions)
    if human_avg == 0.0:
        return None  # avoid division by zero when all human sessions scored 0
    return model_avg / human_avg
```

**Edge case: `human_avg == 0.0`** — if every human session scored 0 efficiency (all failed on attempt 5), the ratio is undefined. Treat as N/A rather than returning `inf`. [ASSUMED — planner should confirm this is the desired behavior; alternatives: return 0.0, raise, or document as expected N/A]

### Pattern 4: Typer Subcommand Addition (matching existing style exactly)

```python
# Source: cipherbench/cli/app.py — existing run_command pattern
# [VERIFIED: codebase]
from typing import Annotated, Optional
import typer
from cipherbench.cli.app import app, Difficulty, _difficulty_to_config

@app.command(name="score")
def score_command(
    model: Annotated[str, typer.Option("--model", help="LiteLLM model string to score")],
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
    difficulty: Annotated[Optional[Difficulty], typer.Option("--difficulty", case_sensitive=False, help="easy | medium | hard")] = None,
    output_file: Annotated[Optional[str], typer.Option("--output-file", help="Write JSON report to this path")] = None,
    human: Annotated[bool, typer.Option("--human/--no-human", help="Score human sessions instead of model sessions")] = False,
) -> None:
    """Compute scoring report for a model or human player (SCORE-01 through SCORE-04)."""
    # delegate entirely to scorer + reporter + report_writer — no business logic here
    ...
```

**Key constraint verified from codebase:** The existing `app.py` docstring states "No business logic here — this module is a coordinator that delegates to session runners." The `score` subcommand must follow the same discipline. [VERIFIED: codebase — cli/app.py line 5]

### Pattern 5: Rich Panel + Table (matching Phase 3 human_runner.py style)

```python
# Source: cipherbench/session/human_runner.py — _show_attempt_history, _show_puzzle_header
# [VERIFIED: codebase]
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()

def render_score_report(report: dict, model: str) -> None:
    # Panel header
    _console.print(Panel(f"Model: {model}", title="[bold]CipherBench Score Report[/bold]"))

    # Table with per-difficulty rows + totals
    table = Table(title="Score Breakdown", show_header=True, header_style="bold")
    table.add_column("Difficulty")
    table.add_column("Sessions", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Efficiency", justify="right")
    table.add_column("AGI Proximity", justify="right")
    # ... add rows per difficulty + totals row
    _console.print(table)
```

**Style match requirement:** The Phase 3 human runner uses `Console()`, `Panel(body, title=...)`, `Table(title=..., show_header=True, header_style="bold")` with `add_column` and `add_row`. The reporter.py must use the same components. [VERIFIED: codebase — human_runner.py lines 64, 80-105]

### Pattern 6: Live Summary Injection Point in `cipherbench run`

The live summary is injected at the end of the outer loop body in `run_command()`, after all `puzzle_idx / run_idx` iterations complete. The current code ends with a `typer.echo` per run. The live summary is a SINGLE call after the entire double-loop:

```python
# Source: cipherbench/cli/app.py run_command — lines 95-106
# [VERIFIED: codebase]
# Current structure:
for puzzle_idx in range(num_puzzles):
    puzzle_seed = ...
    for run_idx in range(runs_per_puzzle):
        adapter = LiteLLMAdapter(model, ...)
        runner = create_model_session(puzzle_seed, config, adapter, out_path)
        session_record = runner.run()
        typer.echo(f"Puzzle {puzzle_idx + 1}/... ...")

# INJECT HERE — after both loops, before function return:
# from cipherbench.scoring.scorer import load_sessions, compute_report
# from cipherbench.scoring.reporter import render_live_summary
# sessions = load_sessions(out_path, runner_type='model', model=model)
# render_live_summary(sessions, out_path)  # prints one line
```

### Anti-Patterns to Avoid

- **Business logic in `cli/app.py`:** The CLI layer must only wire flags and delegate. All scoring math belongs in `scorer.py`. This is an explicit docstring constraint in the existing codebase. [VERIFIED: codebase]
- **Using `global` `sessions/` path hardcoded in scorer:** The scorer must accept `sessions_dir` as a parameter so it is testable with `tmp_path` fixtures.
- **String "N/A" in JSON output:** D-12 explicitly says use `null` in JSON. Terminal uses the string "N/A". Do not conflate.
- **Counting extraction-failed attempts in `attempts_used`:** D-06 is explicit — `extraction_failed=True` attempts are not reasoning steps. The formula only counts `extraction_failed=False`.
- **Merging human sessions into model sessions accidentally:** The `runner_type` discriminator is the canonical guard (D-07 from Phase 3). Always filter by `runner_type` before any computation.
- **Accessing `sessions/` before it exists:** `sessions/` is not created until the first `cipherbench run`. The scorer must handle a non-existent or empty sessions directory gracefully (return empty result set, not raise).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON file reads | Custom deserializer | `json.load()` stdlib | SessionRecord is a plain dict; TypedDict is only a type hint, not a runtime class |
| File path construction | String concatenation | `pathlib.Path / filename` | Already established in writer.py and model_runner.py; cross-platform |
| Terminal table rendering | ASCII character loops | `rich.table.Table` | Already used in human_runner.py; column alignment, color, borders handled automatically |
| Terminal panel rendering | `print()` + borders | `rich.panel.Panel` | Already used in human_runner.py; consistent visual language |
| Float formatting | Manual `f"{x:.2%}"` scattering | Helper function in reporter.py | Centralizes display format so it's consistent across all rows |

**Key insight:** This phase is data transformation + display. The hard problems (file I/O atomicity, JSON schema, Rich layout) are already solved by Phase 3. Phase 4 adds formula application and a new display surface only.

---

## Common Pitfalls

### Pitfall 1: Counting Extraction Failures as Attempts

**What goes wrong:** Naive implementation counts `len(session["attempts"])` for `attempts_used`, which includes extraction-failed entries and deflates the efficiency score.

**Why it happens:** The `attempts` list in the session JSON contains ALL attempt entries, including those with `extraction_failed=True`. These have `probe=null`, `score=null`, and did not consume the model's 5-attempt budget (D-05 from Phase 3).

**How to avoid:** Filter before counting: `attempts_used = sum(1 for a in session["attempts"] if not a["extraction_failed"])`. [VERIFIED: codebase — D-06, CONTEXT.md]

**Warning signs:** Efficiency score for a session with extraction failures comes out lower than expected.

### Pitfall 2: Skipping Non-Terminal Sessions

**What goes wrong:** Including `in_progress` or `rate_limited` sessions in the scoring pool inflates the denominator (sessions scored) with incomplete data.

**Why it happens:** The sessions directory contains all session files, including those written mid-session or interrupted by rate limiting (D-17 from Phase 3 — the file is always present).

**How to avoid:** Filter `outcome` to `{"success", "failure"}` before any computation. [VERIFIED: codebase — D-04, CONTEXT.md; D-09, Phase 3 CONTEXT.md]

**Warning signs:** Success rate drops unexpectedly when many sessions are in-flight.

### Pitfall 3: Model String Exact-Match vs Slug

**What goes wrong:** The `--model` flag receives `"anthropic/claude-opus-4-7"` but the session JSON stores the full LiteLLM string. `slugify_model` transforms it for the filename but the JSON `model` field stores the RAW model string.

**Why it happens:** `session_record["model"] = model_str` where `model_str = getattr(adapter, "_model", None) or "unknown"` — this is the raw model string, not the slug. [VERIFIED: codebase — model_runner.py lines 207, 237]

**How to avoid:** Compare `session["model"] == model_arg` directly (not slug-to-slug). The `--model` CLI flag value is the LiteLLM model string which matches the stored `model` field exactly.

**Warning signs:** `cipherbench score --model anthropic/claude-opus-4-7` returns 0 sessions found even though session files exist.

### Pitfall 4: Empty Session Directory (sessions/ Not Yet Created)

**What goes wrong:** `Path("./sessions").glob("*.json")` raises `FileNotFoundError` or returns no results, and the scorer propagates a confusing error.

**Why it happens:** `sessions/` is created by `SessionWriter` on first write. If `cipherbench score` is run before any `cipherbench run` or `cipherbench play`, the directory does not exist.

**How to avoid:** Guard with `if not sessions_dir.exists(): return []` at the top of `load_sessions`. [VERIFIED: codebase — `_find_resumable_session` in model_runner.py does the same: `if not output_dir.exists(): return None`]

**Warning signs:** FileNotFoundError or empty result with no user-facing explanation.

### Pitfall 5: AGI Proximity Division by Zero (human_avg = 0)

**What goes wrong:** If every human session is a failure on the last attempt, `human_avg_efficiency = 0.0`. Dividing by it produces `inf` or `ZeroDivisionError`.

**Why it happens:** A human who never found the correct probe in 5 attempts gets efficiency = 0 per session; the average of zeros is 0.

**How to avoid:** Guard `if human_avg == 0.0: return None` (treat as N/A). [ASSUMED — the alternative of returning 0.0 or infinity would be misleading; null/N/A is cleaner]

**Warning signs:** AGI proximity shows `inf` or raises exception with an all-failure human baseline.

### Pitfall 6: Typer Optional Enum Flag

**What goes wrong:** `Optional[Difficulty]` with `None` as default behaves differently from `Difficulty` with a non-None default in Typer. Using `Optional[Difficulty] = None` requires `typer.Option` to accept `None` as a valid sentinel.

**Why it happens:** Typer handles `Optional[Enum]` as a nullable enum flag. Without explicit handling, Typer may reject `None` as a default or require `--difficulty` to always be provided.

**How to avoid:** Use `Annotated[Optional[Difficulty], typer.Option(...)] = None`. This is the established pattern in Phase 3's `--litellm-config: Optional[str] = None`. [VERIFIED: codebase — cli/app.py line 82]

**Warning signs:** `cipherbench score --model X` (without `--difficulty`) fails with a Typer validation error.

---

## Code Examples

### Loading and Filtering Sessions (verified pattern)

```python
# Source: cipherbench/session/model_runner.py _find_resumable_session + D-04 filtering
# [VERIFIED: codebase]
from pathlib import Path
import json

TERMINAL_OUTCOMES = frozenset({"success", "failure"})

def load_sessions(
    sessions_dir: Path,
    runner_type: str,
    model: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    if not sessions_dir.exists():
        return []
    result = []
    for path in sessions_dir.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("outcome") not in TERMINAL_OUTCOMES:
            continue
        if data.get("runner_type") != runner_type:
            continue
        if model is not None and data.get("model") != model:
            continue
        if difficulty is not None and data.get("difficulty") != difficulty:
            continue
        result.append(data)
    return result
```

### Efficiency Score (verified formula)

```python
# Source: REQUIREMENTS.md SCORE-02 + CONTEXT.md D-06
# [VERIFIED: codebase — REQUIREMENTS.md line 39, CONTEXT.md lines 133-136]
MAX_ATTEMPTS = 5

def efficiency_score(session: dict) -> float:
    success = 1 if session["outcome"] == "success" else 0
    attempts_used = sum(
        1 for a in session["attempts"] if not a.get("extraction_failed", False)
    )
    return success * (MAX_ATTEMPTS - attempts_used + 1) / MAX_ATTEMPTS
```

### Success Rate (SCORE-01)

```python
# Source: REQUIREMENTS.md SCORE-01 definition
# [ASSUMED — simple ratio, no verification needed]
def success_rate(sessions: list[dict]) -> float:
    if not sessions:
        return 0.0
    successes = sum(1 for s in sessions if s["outcome"] == "success")
    return successes / len(sessions)
```

### JSON Report Structure (locked by D-12)

```json
{
    "model": "anthropic/claude-opus-4-7",
    "sessions_scored": 15,
    "by_difficulty": {
        "easy": {"sessions": 5, "success_rate": 0.80, "avg_efficiency": 0.72, "agi_proximity": 0.85},
        "medium": {"sessions": 7, "success_rate": 0.57, "avg_efficiency": 0.48, "agi_proximity": null},
        "hard": {"sessions": 3, "success_rate": 0.33, "avg_efficiency": 0.27, "agi_proximity": null}
    },
    "totals": {"sessions": 15, "success_rate": 0.60, "avg_efficiency": 0.52, "agi_proximity": 0.85},
    "generated_at": "2026-05-29T14:30:22Z"
}
```

### Live Summary Line Format (D-03)

```python
# Source: CONTEXT.md D-03
# [VERIFIED: codebase — CONTEXT.md]
# After the outer run loop:
summary = f"{successes}/{total} success ({success_rate:.0%}) | avg efficiency: {avg_eff:.2f} | AGI proximity: {proximity_str}"
typer.echo(summary)
# Where proximity_str = f"{proximity:.2f}x" if proximity is not None else "N/A"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `optparse`/`argparse` for CLI | Typer with `Annotated[]` + enum validation | Typer 0.9+ | CLI subcommand flags are type-safe; `Difficulty` enum reused across `run`, `play`, `score` |
| `print()` for terminal output | `rich.Console` + `Panel` + `Table` | Phase 3 established | Consistent visual language; column alignment; color semantic (green/yellow/red) |
| In-file scoring logic | Separate `scoring/` package | Phase 4 design | Scoring is testable without invoking CLI; same data available to both CLI surfaces |

**No deprecated patterns apply to this phase.** All required patterns are established by Phase 3 and confirmed in the codebase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | When `human_avg_efficiency == 0.0`, AGI proximity should return `None` (N/A), not `inf` or `0.0` | Code Examples — AGI proximity | Planner must explicitly handle the zero-denominator case; if user expects a different sentinel, the formula output will be wrong |
| A2 | The live summary in `cipherbench run` reads session files from disk (re-load after writing) rather than accumulating in memory during the run loop | Architecture Patterns — live summary injection | If sessions directory is not flushed by the time the summary runs, results could be stale; but the atomic write pattern ensures files are committed before `runner.run()` returns |
| A3 | `--human` without `--model` filters to ALL human sessions (any player_name) | Code Examples — session loading | If the user expects `--human` without `--model` to require `--player-name`, the aggregation behavior would be wrong |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

---

## Open Questions

1. **`--human` with no `--model`: aggregate all players or require `--player-name`?**
   - What we know: D-02 says `--model` is required for model scoring; D-02 also says `--human` filters by `player_name` matching `--model` value, OR all human sessions if `--model` omitted.
   - What's unclear: CONTEXT.md Claude's Discretion says "planner may add `--player-name TEXT` if needed, or aggregate all human sessions."
   - Recommendation: Planner chooses. Aggregating all is simpler and immediately useful; `--player-name` is additive if needed.

2. **Session count in terminal header: total found or post-filter count?**
   - What we know: CONTEXT.md Claude's Discretion says this is at the planner's discretion.
   - Recommendation: Show post-filter count (sessions actually scored). More honest for the user — they can see what was included.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | `pyproject.toml requires-python` | Partial | 3.9.6 installed | uv manages correct venv; system Python 3.9 is the system interpreter but the project runs in the venv where the package is installed |
| `rich` | reporter.py | Yes | 15.0.0 | — |
| `typer` | cli/app.py score subcommand | Yes | 0.23.2 | — |
| `pytest` | test suite | Yes | 8.4.2 | — |
| `hypothesis` | property-based tests | Yes | 6.141.1 | — |
| `sessions/` directory | session loading | Does not exist yet | — | `load_sessions` must guard with `if not sessions_dir.exists(): return []` |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** The `sessions/` directory does not exist until the first `cipherbench run`. The scorer must handle this gracefully (empty result, no error).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + hypothesis 6.141.1 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-v --tb=short"` |
| Quick run command | `python3 -m pytest tests/unit/test_scoring/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCORE-01 | success_rate returns correct ratio for mix of success/failure sessions | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_success_rate -x` | No — Wave 0 gap |
| SCORE-01 | success_rate = 0.0 for empty session list | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_success_rate_empty -x` | No — Wave 0 gap |
| SCORE-02 | efficiency_score = (max_attempts - attempts_used + 1) / max_attempts for success | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_score_success -x` | No — Wave 0 gap |
| SCORE-02 | efficiency_score = 0.0 for failure regardless of attempts_used | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_score_failure -x` | No — Wave 0 gap |
| SCORE-02 | extraction_failed attempts are NOT counted in attempts_used | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_extraction_failures_excluded -x` | No — Wave 0 gap |
| SCORE-03 | agi_proximity = model_avg / human_avg when baseline present | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_agi_proximity_with_baseline -x` | No — Wave 0 gap |
| SCORE-03 | agi_proximity = None when no human sessions | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_agi_proximity_no_baseline -x` | No — Wave 0 gap |
| SCORE-04 | group_by_difficulty returns correct tier buckets | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_group_by_difficulty -x` | No — Wave 0 gap |
| SCORE-01/04 | compute_report totals match per-difficulty aggregation | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_compute_report_totals_consistent -x` | No — Wave 0 gap |
| SCORE-01–04 | `cipherbench score --help` exits 0 and shows all flags | unit (CLI) | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_score_command_help -x` | No — Wave 0 gap |
| SCORE-01–04 | load_sessions skips in_progress and rate_limited sessions | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_load_sessions_skips_non_terminal -x` | No — Wave 0 gap |
| SCORE-02 | Hypothesis property: efficiency always in [0.0, 1.0] | property | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_score_in_range -x` | No — Wave 0 gap |
| D-03 | Live summary line printed after run_command outer loop | integration | manual — requires live model or mock; verify via CliRunner with FixedResponseAdapter | No — Wave 0 gap |
| D-12 | JSON report written to --output-file with correct structure | unit | `python3 -m pytest tests/unit/test_scoring/test_report_writer.py -x` | No — Wave 0 gap |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/unit/test_scoring/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green (all prior phases + Phase 4) before `/gsd-verify-work`

### Wave 0 Gaps

- `tests/unit/test_scoring/__init__.py` — package marker
- `tests/unit/test_scoring/test_scorer.py` — covers SCORE-01, SCORE-02, SCORE-03, SCORE-04
- `tests/unit/test_scoring/test_reporter.py` — covers terminal output (Rich capture)
- `tests/unit/test_scoring/test_report_writer.py` — covers JSON file write
- `cipherbench/scoring/__init__.py` — package marker
- `cipherbench/scoring/scorer.py` — skeleton with function signatures
- `cipherbench/scoring/reporter.py` — skeleton
- `cipherbench/scoring/report_writer.py` — skeleton

---

## Security Domain

Security enforcement is enabled (`security_enforcement: true` in `.planning/config.json`). ASVS level 1 applies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in scoring; reads local files only |
| V3 Session Management | No | No sessions in the web-security sense; benchmark sessions are data files |
| V4 Access Control | No | Local CLI tool; no multi-user access control |
| V5 Input Validation | Yes — low severity | `--model` and `--sessions-dir` are user-supplied strings used as file paths and JSON filter keys |
| V6 Cryptography | No | No cryptographic operations in scoring |

### Known Threat Patterns for CLI file-path inputs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--sessions-dir` | Tampering | Resolve to absolute path with `Path(sessions_dir).resolve()`; do not use the raw string in any shell execution |
| Malformed JSON in sessions directory | Denial of Service (degraded output) | Already mitigated: `try/except (json.JSONDecodeError, OSError): continue` — skip malformed files silently |
| `--output-file` writing to system paths | Tampering | The file is written with `json.dump`; no shell execution; risk is low for a local research tool at ASVS L1 |
| Injection via `model` field in session JSON | Tampering | The `model` string is compared as a literal string, never executed or interpolated into shell commands |

**ASVS Level 1 verdict:** Phase 4 has a low attack surface. The only user-controlled input that touches the filesystem is `--sessions-dir` and `--output-file`. Both should use `pathlib.Path` (not `os.system` or `subprocess`) — already established by the project's file I/O patterns. No high-severity threats identified.

---

## Sources

### Primary (HIGH confidence)
- `cipherbench/session/schema.py` — exact `SessionRecord` and `AttemptEntry` TypedDict fields confirmed
- `cipherbench/cli/app.py` — exact Typer pattern, `Difficulty` enum, `Annotated[]` flag style, no-business-logic constraint
- `cipherbench/session/model_runner.py` — glob pattern, `_find_resumable_session`, `MAX_ATTEMPTS = 5` constant, `runner_type` usage
- `cipherbench/session/human_runner.py` — Rich `Console`, `Panel`, `Table` usage patterns
- `cipherbench/session/writer.py` — `slugify_model`, `make_session_id`, atomic write patterns
- `.planning/phases/04-scoring-reporting/04-CONTEXT.md` — all locked decisions D-01 through D-13
- `.planning/REQUIREMENTS.md` — SCORE-01 through SCORE-04 exact formulas and acceptance criteria
- PyPI registry via `pip3 index versions` — all installed package versions verified current

### Secondary (MEDIUM confidence)
- `.planning/phases/03-session-infrastructure-model-adapters/03-CONTEXT.md` — Phase 3 decisions that constrain Phase 4 (D-06, D-07, D-08, D-09, D-10, D-11)
- `tests/unit/test_session/test_model_runner.py` — test patterns for parameterized session fixtures
- `tests/unit/test_cli/test_commands.py` — CLI test patterns using `typer.testing.CliRunner`
- `tests/conftest.py` — shared fixtures (`tmp_sessions_dir`, `FixedResponseAdapter`, `mock_adapter`)

### Tertiary (LOW confidence / assumptions)
- AGI proximity = `None` when `human_avg == 0.0` — analytically derived, not specified in CONTEXT.md
- `--human` without `--model` aggregates all human sessions — inferred from D-02 text; marked [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages installed and version-verified via PyPI
- Architecture: HIGH — derived directly from reading existing codebase (schema.py, app.py, model_runner.py, human_runner.py)
- Formula correctness: HIGH — exact formulas quoted from REQUIREMENTS.md and CONTEXT.md; edge cases analytically solved
- Pitfalls: HIGH — derived from direct codebase inspection of field names and filter patterns
- Test patterns: HIGH — existing test files provide exact fixture and assertion patterns to follow

**Research date:** 2026-05-29
**Valid until:** 2026-06-28 (30 days — stable stdlib + well-established Rich/Typer stack)
