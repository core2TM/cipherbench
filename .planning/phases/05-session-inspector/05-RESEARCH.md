# Phase 5: Session Inspector - Research

**Researched:** 2026-05-29
**Domain:** Python CLI read-only session replay (Typer + Rich + stdlib JSON)
**Confidence:** HIGH — all findings verified directly from the live codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Prefix/substring match strategy — `inspect` searches `./sessions/*.json` (or `--sessions-dir`) and matches any file whose stem (filename without `.json`) contains the given `<session-id>` argument as a substring (case-insensitive).
- **D-02:** Exactly 1 match → load and display the session. 0 matches → error with list of all available session IDs. 2+ matches → error with "Ambiguous: matched N sessions" plus the list of matching IDs so the user can narrow down.
- **D-03:** Header: Rich Panel at the top showing: `session_id`, `runner_type` (model/human), `seed`, `difficulty`, `outcome`. Matches the visual language of `cipherbench score` and `cipherbench play`.
- **D-04:** Attempts body: Rich Table with columns — `Attempt | Probe | Score | Correct?`. One row per attempt entry in order of `attempt_num`.
- **D-05:** Extraction failures: shown in the table with `Probe = — (extraction failed)`, `Score = —`, `Correct? = ✗`. Not hidden — they are part of the session record.
- **D-06:** Footer: one line below the table showing the final answer and outcome — e.g., `Final answer: XYZAB — ✓ Success` or `Final answer: XYZAB — ✗ Failure`. If `final_answer` is null (e.g., session was rate-limited before reaching the answer step), show `Final answer: — (not reached)`.
- **D-07:** `inspect` accepts `--sessions-dir PATH` (optional, default `./sessions`). Parity with `cipherbench score`. Path is resolved via `Path(...).resolve()` to prevent path traversal (consistent with T-04-06 discipline in `score` command).
- **D-08:** Session not found: print `Session not found: '<session-id>'` and list all available session IDs in the directory (one per line). Exit code 1.
- **D-09:** Sessions directory missing: print `Sessions directory not found: <path>\nRun 'cipherbench run' or 'cipherbench play' to record sessions first.` Exit code 1.
- **D-10:** Sessions directory exists but is empty: print `No sessions found in: <path>` and exit 1.
- No business logic in `cli/app.py` — inspector logic in `cipherbench/session/inspector.py`.

### Claude's Discretion

- Exact Rich table column widths and color scheme — must feel consistent with the `score` command's Rich output but exact styling is planner's choice.
- Whether to show `runner_type`-specific fields in the panel (e.g., `model` for model sessions, `player_name` for human sessions) or always show both (with `null` for the inapplicable one).
- Whether `inspector.py` lives in `cipherbench/session/` or `cipherbench/cli/` — planner picks the location that best matches existing patterns.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SESS-03 | `cipherbench inspect <session-id>` command replays a stored session trace, displaying each probe attempt, the score returned, and the final answer with outcome | Fully supported: schema fields in `schema.py`, glob+JSON pattern in `scorer.py`, Rich Panel+Table pattern in `reporter.py` + `human_runner.py`, Typer `Annotated[]` pattern in `app.py` |

</phase_requirements>

---

## Summary

Phase 5 adds a single CLI subcommand — `cipherbench inspect <session-id>` — that reads a stored session JSON and replays it visually in the terminal. All underlying infrastructure is already in place from Phases 3 and 4: the session schema (`schema.py`) defines every field, the glob+JSON loading pattern is established in `scorer.py`, and Rich Panel+Table rendering is established in both `reporter.py` and `human_runner.py`. This is purely an additive phase: one new module (`cipherbench/session/inspector.py`), one new command wired into the existing `app` Typer instance, and a corresponding test file.

The display logic is straightforward. Session lookup uses a case-insensitive substring match on filename stems — no JSON deserialization needed for the match step. The Panel header shows six fields from `SessionRecord`; the Table shows four columns derived from `AttemptEntry` fields, with `extraction_failed=True` rows rendered as em-dashes per D-05. The footer line is a single `_console.print()` call. Error branches (not-found, missing dir, empty dir) each call `typer.Exit(code=1)` after printing to stderr — exactly mirroring the `score_command` pattern.

The only design decision left to the planner is whether to show `model` and `player_name` side-by-side in the Panel (always, with `null` for the non-applicable one) versus a single runner-type-aware label. The "no schema divergence" success criterion (criterion 2) is best honored by a single unified display path that renders identically regardless of `runner_type` — branching on `runner_type` for display would introduce exactly the divergence the requirement forbids.

**Primary recommendation:** Place `inspector.py` in `cipherbench/session/` (consistent with `human_runner.py`, `model_runner.py`, `writer.py`, `schema.py`). Implement `display_session(session: dict, console: Console) -> None` and `inspect_session(session_id: str, sessions_dir: Path, console: Console) -> None` as the two public functions. Wire `inspect_command` in `app.py` as a thin delegate — no logic there. Export `inspect_session` from `cipherbench/__init__.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session file lookup (glob + substring match) | `cipherbench/session/inspector.py` | — | Pure Python I/O, no CLI concerns; mirrors `scorer.py` load_sessions pattern |
| JSON deserialization | `cipherbench/session/inspector.py` | — | Already established in `scorer.py`; stdlib json, no adapter needed |
| Rich Panel + Table rendering | `cipherbench/session/inspector.py` | — | Display logic belongs in the module, not the CLI layer (enforced by app.py docstring) |
| CLI flag wiring (`inspect` subcommand) | `cipherbench/cli/app.py` | — | All commands added to the single `app` Typer instance here |
| Path traversal prevention | `cipherbench/cli/app.py` | — | `Path(...).resolve()` applied at the CLI boundary before passing to inspector |
| Error message formatting | `cipherbench/session/inspector.py` | — | Inspector raises `SystemExit` or returns an error signal; CLI layer calls `typer.Exit` |
| Public API export | `cipherbench/__init__.py` | — | `inspect_session` added alongside `load_sessions` and `compute_report` |

---

## Standard Stack

Phase 5 introduces **no new dependencies**. All required libraries are already declared in `pyproject.toml` and installed.

### Core (all already installed)

| Library | Installed Version | Purpose | Source |
|---------|------------------|---------|--------|
| `typer` | 0.23.2 | `@app.command(name="inspect")` subcommand, `Annotated[]` flags, `typer.Exit` | [VERIFIED: PyPI registry] |
| `rich` | 15.0.0 | `Panel`, `Table`, `Console` for terminal display | [VERIFIED: PyPI registry] |
| `json` (stdlib) | n/a | Deserialize session JSON files | [VERIFIED: stdlib] |
| `pathlib.Path` (stdlib) | n/a | `Path(...).resolve()`, `glob("*.json")`, existence checks | [VERIFIED: stdlib] |

### No New Packages

This phase reads existing session files and renders them. No HTTP clients, no new data formats, no new test frameworks.

**Installation:** No installation step required.

**Version verification:**
- `typer 0.23.2` — confirmed via `pip3 index versions typer` (latest as of 2026-05-29) [VERIFIED: PyPI registry]
- `rich 15.0.0` — confirmed via `pip3 index versions rich` (latest as of 2026-05-29) [VERIFIED: PyPI registry]
- `pytest 8.4.2` — confirmed via `pip3 index versions pytest` (latest as of 2026-05-29) [VERIFIED: PyPI registry]

---

## Package Legitimacy Audit

All packages were verified with `python3 -m slopcheck install typer rich litellm pytest hypothesis pytest-asyncio hatchling` on 2026-05-29. All 7 packages returned `[OK]`.

| Package | Registry | slopcheck | Disposition |
|---------|----------|-----------|-------------|
| typer | PyPI | [OK] | Approved — already in pyproject.toml |
| rich | PyPI | [OK] | Approved — already in pyproject.toml |
| pytest | PyPI | [OK] | Approved — already in pyproject.toml dev dep |
| hypothesis | PyPI | [OK] | Approved — already in pyproject.toml dev dep |
| litellm | PyPI | [OK] | Approved — already in pyproject.toml |
| pytest-asyncio | PyPI | [OK] | Approved — already in pyproject.toml dev dep |
| hatchling | PyPI | [OK] | Approved — already in pyproject.toml build backend |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
CLI invocation
  cipherbench inspect <session-id> [--sessions-dir PATH]
        │
        ▼
  app.py inspect_command()
  ├─ Path(sessions_dir).resolve()          ← ASVS V5: path traversal prevention
  └─ calls inspect_session(session_id, resolved_path, console)
        │
        ▼
  inspector.py inspect_session()
  ├─ check dir exists → error D-09 if missing
  ├─ glob("*.json")  → error D-10 if empty
  ├─ filter stems by case-insensitive substring match
  │    ├─ 0 matches → list all stems, error D-08, exit 1
  │    ├─ 2+ matches → list matching stems, "Ambiguous" error, exit 1
  │    └─ 1 match → json.load()
  └─ display_session(session_dict, console)
        ├─ console.print(Panel(...))         ← D-03 header
        ├─ console.print(Table(...))         ← D-04 attempt rows
        │    └─ for each AttemptEntry:
        │         extraction_failed=True → D-05 em-dash row
        │         else → probe / score / is_correct
        └─ console.print(footer_line)        ← D-06 final answer
```

### Recommended Project Structure

```
cipherbench/
├── session/
│   ├── __init__.py
│   ├── schema.py          # AttemptEntry, SessionRecord (unchanged)
│   ├── inspector.py       # NEW: inspect_session(), display_session()
│   ├── writer.py          # unchanged
│   ├── model_runner.py    # unchanged
│   └── human_runner.py    # unchanged
└── cli/
    └── app.py             # add @app.command(name="inspect") inspect_command()

tests/
└── unit/
    └── test_session/
        └── test_inspector.py  # NEW: all inspector unit tests
```

### Pattern 1: Typer `Annotated[]` Command — Exact Style to Replicate

Every command in `app.py` uses `Annotated[Type, typer.Option(...)]` syntax with a docstring as the command description. The `inspect` command must match this exactly.

```python
# Source: cipherbench/cli/app.py (verified from codebase)
@app.command(name="inspect")
def inspect_command(
    session_id: Annotated[str, typer.Argument(help="Session ID or substring to inspect")],
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
) -> None:
    """Replay a stored session trace, displaying all probe attempts and final outcome (SESS-03)."""
    from cipherbench.session.inspector import inspect_session
    from rich.console import Console

    resolved = Path(sessions_dir).resolve()   # ASVS V5: path traversal prevention (T-04-06)
    inspect_session(session_id, resolved, Console())
```

Note: `session_id` uses `typer.Argument` (positional), not `typer.Option` (flag). The `score_command` uses `typer.Option` for everything; `inspect` takes a positional argument per the CLI design `cipherbench inspect <session-id>`.

### Pattern 2: Rich Panel Header — Exact Style to Replicate

From `reporter.py` (verified from codebase):

```python
# Source: cipherbench/scoring/reporter.py
from rich.console import Console
from rich.panel import Panel

_console = Console()

_console.print(
    Panel(
        f"Model: {model}  |  Sessions scored: {report['sessions_scored']}",
        title="[bold]CipherBench Score Report[/bold]",
    )
)
```

Inspector Panel should follow the same `Panel(body_str, title="[bold]...[/bold]")` form:

```python
# Derived pattern for inspector (verified against codebase style)
body = (
    f"Session ID: {session['session_id']}\n"
    f"Runner: {session['runner_type']}  |  Seed: {session['seed']}  |  Difficulty: {session['difficulty']}\n"
    f"Outcome: {session['outcome']}"
)
console.print(Panel(body, title="[bold]CipherBench Session Inspect[/bold]"))
```

### Pattern 3: Rich Table — Exact Style to Replicate

From `reporter.py` and `human_runner.py` (verified from codebase):

```python
# Source: cipherbench/scoring/reporter.py
table = Table(title="Score Breakdown", show_header=True, header_style="bold")
table.add_column("Difficulty", min_width=10)
table.add_column("Sessions", justify="right", min_width=8)
# ...
table.add_row(tier, str(stats["sessions"]), ...)
_console.print(table)

# Source: cipherbench/session/human_runner.py
table = Table(title="Attempt History", show_header=True, header_style="bold")
table.add_column("#", style="dim", width=4)
table.add_column("Probe", min_width=8)
table.add_column("Score", min_width=8)
```

Inspector table pattern:

```python
# Derived from codebase style — show_header=True, header_style="bold"
table = Table(title="Attempt Trace", show_header=True, header_style="bold")
table.add_column("Attempt", justify="right", min_width=8)
table.add_column("Probe", min_width=8)
table.add_column("Score", justify="right", min_width=8)
table.add_column("Correct?", justify="center", min_width=9)

for entry in session["attempts"]:
    if entry.get("extraction_failed"):
        table.add_row(
            str(entry["attempt_num"]),
            "— (extraction failed)",
            "—",
            "✗",
            style="red",
        )
    else:
        score_str = f"{entry['score']}/{entry['max_score']}" if entry.get("score") is not None else "—"
        correct_str = "✓" if entry.get("is_correct") else "✗"
        style = "green" if entry.get("is_correct") else None
        table.add_row(str(entry["attempt_num"]), entry.get("probe") or "—", score_str, correct_str, style=style)

console.print(table)
```

### Pattern 4: Session Glob Loading — Exact Style to Replicate

From `scorer.py` (verified from codebase):

```python
# Source: cipherbench/scoring/scorer.py
for path in sessions_dir.glob("*.json"):
    try:
        with path.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        continue  # skip malformed or unreadable files silently
```

Inspector uses same glob but matches on stem before deserializing (faster):

```python
# Derived from scorer.py pattern — stem match before JSON load
matches = [
    p for p in sessions_dir.glob("*.json")
    if session_id.lower() in p.stem.lower()
]
```

### Pattern 5: Error Handling with Exit Code 1

From `score_command` in `app.py` (verified from codebase):

```python
# Source: cipherbench/cli/app.py
if not model_sessions:
    typer.echo("No terminal sessions found matching the given filters.", err=True)
    raise typer.Exit(code=1)
```

Inspector raises `SystemExit(1)` (or a custom exception the CLI catches) from `inspector.py`, or the CLI layer does the `typer.Exit`. Given the "no business logic in `app.py`" constraint, the inspector module should signal errors through a raised exception or return value, with the CLI doing `raise typer.Exit(code=1)`. The simplest pattern matching existing code: inspector prints the error message and raises `SystemExit(1)` directly, since `typer.Exit` is a Typer-layer concern. Alternatively, inspector returns an error sentinel and the CLI raises `typer.Exit`. Either is acceptable — the planner should pick the approach that keeps `app.py` thinnest.

### Pattern 6: `_console` Module-Level Variable for Testability

From `reporter.py` (verified from codebase):

```python
# Source: cipherbench/scoring/reporter.py
_console = Console()

# Tests monkeypatch it:
monkeypatch.setattr(reporter_mod, "_console", mock_console)
```

Inspector should follow the same pattern: a `_console = Console()` at module level in `inspector.py`, so tests can monkeypatch it to capture output. The `inspect_session` function then accepts an optional `console` parameter defaulting to `_console`, or takes it as a required parameter and the CLI passes `Console()` — either pattern works, the first is simpler for tests.

### Anti-Patterns to Avoid

- **Business logic in `app.py`:** The `app.py` docstring explicitly states "No business logic here." Putting substring matching, JSON loading, or display logic in `inspect_command` would violate this invariant.
- **Opening every JSON file to match session_id:** The `session_id` is the filename stem. Match on stem before deserializing. Opening all files to read the `session_id` field is O(n) unnecessary I/O.
- **Branching on `runner_type` in display logic:** Success criterion 2 requires equivalent trace formats for model and human sessions. A single display path that renders all `SessionRecord` fields identically (with `null` shown as `—` for non-applicable fields) satisfies this without divergence.
- **Using `global random.seed()`:** Not applicable here (read-only module), but maintain general discipline.
- **Not resolving the path:** `Path(sessions_dir).resolve()` must happen before any filesystem operation. Missing this leaves the path traversal guard incomplete.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal table formatting | Custom string padding with spaces | `rich.table.Table` | Column alignment, Unicode width, ANSI color — all handled automatically |
| Terminal panel/box drawing | Manual `─`, `│` characters | `rich.panel.Panel` | Box-drawing chars, title placement, width calculation are non-trivial |
| JSON file read | Custom deserializer | `json.load()` (stdlib) | Already established pattern in `scorer.py` |
| Path safety | Manual `..` detection | `Path(...).resolve()` | Canonicalizes symlinks and `..` — established T-04-06 discipline |
| CLI argument parsing | `argparse` or `sys.argv` | `typer.Argument` / `typer.Option` | Consistent with all other commands; auto-generates `--help` |

**Key insight:** This phase is deliberately thin — its value is the composition of existing patterns, not new infrastructure. The entire feature should fit in ~100 lines of production code.

---

## Common Pitfalls

### Pitfall 1: Case Sensitivity in Substring Match

**What goes wrong:** `'20260529T143022-CLAUDE' in '20260529t143022-claude'` returns False when the user supplies mixed case.
**Why it happens:** Python string `in` operator is case-sensitive by default.
**How to avoid:** `session_id.lower() in path.stem.lower()` — normalize both sides to lowercase before matching (D-01 specifies case-insensitive).
**Warning signs:** Tests pass with exact-case inputs but fail when user types a partial lowercase substring.

### Pitfall 2: Showing `probe=None` Literally Instead of Em-Dash

**What goes wrong:** `AttemptEntry.probe` is `Optional[str]`; for extraction failures it is `None`. Rendering `str(None)` produces `"None"` in the table, not `"—"`.
**Why it happens:** Forgetting to check `extraction_failed` before rendering.
**How to avoid:** Check `entry.get("extraction_failed")` first. When `True`, use the D-05 em-dash rendering unconditionally. Do not rely on `probe is None` as the sole signal — `extraction_failed` is the authoritative flag per `schema.py`.
**Warning signs:** `"None"` or `"null"` appearing in the Probe column during testing.

### Pitfall 3: Including `in_progress` / `rate_limited` Sessions

**What goes wrong:** Inspector loads and displays a session that is still in progress or was rate-limited, showing an incomplete attempt list.
**Why it happens:** The glob matches all `.json` files regardless of `outcome`.
**How to avoid:** The inspector is read-only and should display ANY session (including non-terminal ones), but the display must accurately show the `outcome` field so the user knows the session is incomplete. Do NOT silently filter out non-terminal sessions the way `scorer.py` does — the inspector's job is to show what's stored, not to apply scoring filters.
**Warning signs:** User inspects a rate-limited session and sees no error but missing attempts.

### Pitfall 4: Path Traversal via Unsanitized `--sessions-dir`

**What goes wrong:** A crafted `--sessions-dir ../../etc` argument reads files outside the intended directory.
**Why it happens:** Missing `Path(...).resolve()` before use.
**How to avoid:** Apply `Path(sessions_dir).resolve()` in `inspect_command` before passing to inspector — exactly as `score_command` does (T-04-06). This is an ASVS V5 requirement.
**Warning signs:** The `score_command` has `resolve()` on line 169; if `inspect_command` omits it, a code review diff will catch the discrepancy.

### Pitfall 5: Missing Exit Code on Error Paths

**What goes wrong:** Error messages are printed but the process exits 0, making scripting callers unable to detect failure.
**Why it happens:** Printing the error but forgetting `raise typer.Exit(code=1)` (or `raise SystemExit(1)`).
**How to avoid:** Every error branch (D-08, D-09, D-10) must exit with code 1. Test with `CliRunner` and assert `result.exit_code == 1`.
**Warning signs:** `CliRunner().invoke(app, [...]).exit_code` is 0 when it should be 1.

### Pitfall 6: Ambiguous Session ID Listing Shows Wrong Sessions

**What goes wrong:** When 2+ sessions match (D-02), the error message lists all sessions in the directory instead of only the matching ones.
**Why it happens:** Reusing the "list all" code path from the not-found branch.
**How to avoid:** Two separate lists: `matches` (filtered by substring) and `all_stems` (every `.json` stem). D-08 uses `all_stems`; D-02 uses `matches`.
**Warning signs:** Ambiguous error shows 50 sessions when only 3 matched the substring.

---

## Code Examples

### Full `inspector.py` Skeleton

```python
# Derived from scorer.py + reporter.py + human_runner.py patterns (verified from codebase)
from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()


def inspect_session(session_id: str, sessions_dir: Path, console: Console | None = None) -> None:
    """Locate and display a stored session trace (SESS-03).

    Errors: prints message and raises SystemExit(1).
    """
    if console is None:
        console = _console

    # D-09: sessions directory missing
    if not sessions_dir.exists():
        console.print(
            f"Sessions directory not found: {sessions_dir}\n"
            "Run 'cipherbench run' or 'cipherbench play' to record sessions first.",
            style="red",
        )
        raise SystemExit(1)

    all_paths = list(sessions_dir.glob("*.json"))

    # D-10: sessions directory empty
    if not all_paths:
        console.print(f"No sessions found in: {sessions_dir}", style="red")
        raise SystemExit(1)

    matches = [p for p in all_paths if session_id.lower() in p.stem.lower()]
    all_stems = sorted(p.stem for p in all_paths)

    # D-08: zero matches
    if not matches:
        console.print(f"Session not found: '{session_id}'", style="red")
        for stem in all_stems:
            console.print(f"  {stem}")
        raise SystemExit(1)

    # D-02: ambiguous (2+ matches)
    if len(matches) > 1:
        console.print(
            f"Ambiguous: matched {len(matches)} sessions for '{session_id}':", style="yellow"
        )
        for p in sorted(matches):
            console.print(f"  {p.stem}")
        raise SystemExit(1)

    # Exactly 1 match — load and display
    path = matches[0]
    try:
        with path.open() as f:
            session = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"Error reading session file: {exc}", style="red")
        raise SystemExit(1)

    display_session(session, console)


def display_session(session: dict, console: Console) -> None:
    """Render a SessionRecord dict to terminal (D-03, D-04, D-05, D-06)."""
    # D-03: Panel header
    runner = session.get("runner_type", "unknown")
    runner_label = session.get("model") or session.get("player_name") or "—"
    body = (
        f"Session ID : {session.get('session_id', '—')}\n"
        f"Runner     : {runner} ({runner_label})\n"
        f"Seed       : {session.get('seed', '—')}  |  "
        f"Difficulty : {session.get('difficulty', '—')}\n"
        f"Outcome    : {session.get('outcome', '—')}"
    )
    console.print(Panel(body, title="[bold]CipherBench Session Inspector[/bold]"))

    # D-04: Attempt table
    table = Table(title="Attempt Trace", show_header=True, header_style="bold")
    table.add_column("Attempt", justify="right", min_width=8)
    table.add_column("Probe", min_width=8)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Correct?", justify="center", min_width=9)

    for entry in session.get("attempts", []):
        if entry.get("extraction_failed"):
            # D-05: extraction failures shown, not hidden
            table.add_row(
                str(entry.get("attempt_num", "?")),
                "— (extraction failed)",
                "—",
                "✗",
                style="red",
            )
        else:
            score = entry.get("score")
            max_score = entry.get("max_score", "?")
            score_str = f"{score}/{max_score}" if score is not None else "—"
            is_correct = entry.get("is_correct", False)
            table.add_row(
                str(entry.get("attempt_num", "?")),
                entry.get("probe") or "—",
                score_str,
                "✓" if is_correct else "✗",
                style="green" if is_correct else None,
            )

    console.print(table)

    # D-06: Footer
    final_answer = session.get("final_answer")
    outcome = session.get("outcome", "unknown")
    if final_answer is None:
        footer = "Final answer: — (not reached)"
    else:
        outcome_symbol = "✓" if outcome == "success" else "✗"
        outcome_label = outcome.capitalize()
        footer = f"Final answer: {final_answer} — {outcome_symbol} {outcome_label}"
    console.print(footer)
```

### `inspect_command` in `app.py`

```python
# Derived from score_command pattern (verified from codebase)
@app.command(name="inspect")
def inspect_command(
    session_id: Annotated[str, typer.Argument(help="Session ID or substring to match")],
    sessions_dir: Annotated[str, typer.Option("--sessions-dir", help="Directory to read session files from")] = "./sessions",
) -> None:
    """Replay a stored session trace, displaying all probe attempts and final outcome (SESS-03)."""
    from cipherbench.session.inspector import inspect_session
    from rich.console import Console

    resolved = Path(sessions_dir).resolve()  # ASVS V5: path traversal prevention (T-04-06)
    inspect_session(session_id, resolved, Console())
```

### Test Pattern — CliRunner + `tmp_path` + monkeypatch

```python
# Derived from test_commands.py + test_reporter.py patterns (verified from codebase)
import json
from typer.testing import CliRunner
from cipherbench.cli.app import app

def _write_session(tmp_dir, session_id: str, session: dict):
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / f"{session_id}.json").write_text(json.dumps(session))

def test_inspect_command_help_exits_zero():
    result = CliRunner().invoke(app, ["inspect", "--help"])
    assert result.exit_code == 0
    assert "--sessions-dir" in result.output

def test_inspect_found_exits_zero(tmp_path):
    sessions = tmp_path / "sessions"
    _write_session(sessions, "20260529T000000-test", _make_session("success", 2))
    result = CliRunner().invoke(app, ["inspect", "test", "--sessions-dir", str(sessions)])
    assert result.exit_code == 0

def test_inspect_not_found_exits_one(tmp_path):
    sessions = tmp_path / "sessions"
    _write_session(sessions, "20260529T000000-test", _make_session("success", 2))
    result = CliRunner().invoke(app, ["inspect", "zzz-nomatch", "--sessions-dir", str(sessions)])
    assert result.exit_code == 1

def test_inspect_missing_dir_exits_one(tmp_path):
    result = CliRunner().invoke(app, ["inspect", "any", "--sessions-dir", str(tmp_path / "missing")])
    assert result.exit_code == 1

def test_inspect_empty_dir_exits_one(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    result = CliRunner().invoke(app, ["inspect", "any", "--sessions-dir", str(sessions)])
    assert result.exit_code == 1
```

---

## State of the Art

This phase uses no novel patterns. All techniques were established in prior phases.

| Old Approach | Current Approach | Established In | Impact |
|--------------|-----------------|----------------|--------|
| `glob()` then open all files | `glob()` then stem-match before open | Phase 4 `scorer.py` | Phase 5 adds case-insensitive substring match on stem before JSON deserialization |
| `Panel(body, title=...)` | Same — no change | Phase 3 `human_runner.py`, Phase 4 `reporter.py` | Phase 5 reuses verbatim |
| `Table(show_header=True, header_style="bold")` | Same — no change | Phase 3 `human_runner.py`, Phase 4 `reporter.py` | Phase 5 reuses verbatim |
| Lazy import inside command function | Same pattern | Phase 4 `score_command` | Inspector import placed inside `inspect_command` for consistency |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `typer.Argument` (positional) is the correct Typer construct for `<session-id>` | Code Examples | If wrong, the CLI signature would be `--session-id` flag instead of positional; harmless fix |
| A2 | `SystemExit(1)` from within `inspector.py` is the right error-signaling mechanism (vs. returning a sentinel and having `app.py` call `typer.Exit`) | Architecture Patterns, Code Examples | Either approach works; if planner prefers sentinel return, the test assertions on `exit_code` still hold |

---

## Open Questions

1. **Panel runner-type-specific display (Claude's Discretion)**
   - What we know: `runner_type` is `"model"` or `"human"`; `model` is set for model sessions and `player_name` for human sessions; the other is `None`.
   - What's unclear: Should the Panel show `Model: anthropic/claude-opus | Player: —` (always both), or `Runner: model (anthropic/claude-opus)` (unified label)?
   - Recommendation: Use a unified label `Runner: {runner_type} ({model or player_name or '—'})` — single rendering path, no branching on runner_type, satisfies success criterion 2.

2. **`inspector.py` location (Claude's Discretion)**
   - What we know: `cipherbench/session/` already contains `schema.py`, `writer.py`, `model_runner.py`, `human_runner.py` — all session-lifecycle concerns.
   - What's unclear: Inspector is read-only; does it belong in `session/` (session domain) or `cli/` (CLI-adjacent)?
   - Recommendation: `cipherbench/session/inspector.py` — consistent with all other session-domain modules; `cli/app.py` imports from it, not the reverse.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | `pyproject.toml requires-python` | ✗ (system Python 3.9.6) | 3.9.6 | Project uses venv/uv — `python3` on PATH is system Python; tests run via `uv run pytest` or the project venv |
| typer | `inspect_command` | ✓ (in venv) | 0.23.2 | — |
| rich | `Panel`, `Table`, `Console` | ✓ (in venv) | 15.0.0 | — |
| pytest | Test suite | ✓ (in venv) | 8.4.2 | — |

**Note on Python 3.9.6:** The system Python (`/usr/bin/python3`) is 3.9.6. This does not block development — all tests and production code run through the project's virtual environment managed by `uv`, which installs a Python 3.11+ runtime. The system Python is only used for `pip3` commands from outside the venv.

**Missing dependencies with no fallback:** None — all required packages are installed in the project venv.

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `addopts = "-v --tb=short"`) |
| Quick run command | `pytest tests/unit/test_session/test_inspector.py -x` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SESS-03-A | `inspect <id>` displays all probe attempts in order | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_session_shows_all_attempts -x` | ❌ Wave 0 |
| SESS-03-B | Extraction failure rows rendered as em-dash per D-05 | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_extraction_failure_row -x` | ❌ Wave 0 |
| SESS-03-C | Footer shows final answer and outcome per D-06 | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_footer_success -x` | ❌ Wave 0 |
| SESS-03-D | Footer shows `— (not reached)` when `final_answer` is None | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_footer_not_reached -x` | ❌ Wave 0 |
| SESS-03-E | Substring match (D-01): partial ID finds session | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_substring_match -x` | ❌ Wave 0 |
| SESS-03-F | Case-insensitive match (D-01) | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_case_insensitive -x` | ❌ Wave 0 |
| SESS-03-G | 0 matches → exit 1 + list all (D-08) | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_not_found -x` | ❌ Wave 0 |
| SESS-03-H | 2+ matches → exit 1 + "Ambiguous" (D-02) | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_ambiguous -x` | ❌ Wave 0 |
| SESS-03-I | Missing dir → exit 1 + D-09 message | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_missing_dir -x` | ❌ Wave 0 |
| SESS-03-J | Empty dir → exit 1 + D-10 message | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_empty_dir -x` | ❌ Wave 0 |
| SESS-03-K | `--help` exits 0 and shows `--sessions-dir` | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_command_help -x` | ❌ Wave 0 |
| SESS-03-L | Human session and model session produce same table structure (no schema divergence) | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_schema_parity -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_session/test_inspector.py -x`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_session/test_inspector.py` — covers all SESS-03 sub-requirements above
- [ ] `cipherbench/session/inspector.py` — the production module stub

*(Shared fixtures `tmp_sessions_dir`, `_make_session` are already available in `conftest.py` and `test_scorer.py` respectively — no new fixture infrastructure needed.)*

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` in `.planning/config.json`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in this CLI command |
| V3 Session Management | No | No session state in inspector (read-only) |
| V4 Access Control | No | Single-user local CLI; no multi-user ACL |
| V5 Input Validation | Yes | `Path(...).resolve()` prevents path traversal on `--sessions-dir`; substring match operates on `p.stem` (filesystem-derived, not executed) |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for Python CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--sessions-dir ../../etc` | Tampering | `Path(sessions_dir).resolve()` (already established as T-04-06 in `score_command`) |
| Malformed session JSON causing crash | Denial of Service | `try/except (json.JSONDecodeError, OSError)` with graceful error message — same pattern as `scorer.py` |
| Filename stem containing shell metacharacters | Spoofing | Stems are only displayed as strings, never passed to shell — no injection risk |

---

## Sources

### Primary (HIGH confidence)

- `cipherbench/session/schema.py` — `SessionRecord` and `AttemptEntry` field definitions, read directly from codebase
- `cipherbench/cli/app.py` — Typer `Annotated[]` command patterns, `Path(...).resolve()` discipline, lazy import pattern
- `cipherbench/scoring/reporter.py` — Rich `Panel`, `Table`, `Console` patterns and `_console` monkeypatch pattern
- `cipherbench/scoring/scorer.py` — `glob("*.json")`, `json.load()`, skip-malformed pattern
- `cipherbench/session/human_runner.py` — Rich `Table(show_header=True, header_style="bold")`, `add_column`, row styling
- `tests/unit/test_cli/test_commands.py` — `CliRunner().invoke(app, [...])` test pattern
- `tests/unit/test_scoring/test_reporter.py` — `monkeypatch.setattr(mod, "_console", mock_console)` capture pattern
- `tests/conftest.py` — `tmp_sessions_dir` fixture, `FixedResponseAdapter`

### Secondary (MEDIUM confidence)

- PyPI registry (`pip3 index versions`) — confirmed typer 0.23.2, rich 15.0.0, pytest 8.4.2 are current [VERIFIED: PyPI registry]
- `python3 -m slopcheck install` — all 7 packages returned [OK]

### Tertiary (LOW confidence)

None — all claims verified against live codebase or PyPI registry.

---

## Metadata

**Confidence breakdown:**
- SessionRecord / AttemptEntry schema: HIGH — read directly from `schema.py`
- Typer `Annotated[]` command pattern: HIGH — read directly from `app.py`
- Rich Panel / Table pattern: HIGH — read directly from `reporter.py` and `human_runner.py`
- Glob + JSON loading pattern: HIGH — read directly from `scorer.py`
- Test patterns: HIGH — read directly from `test_commands.py` and `test_reporter.py`
- Package versions: HIGH — confirmed via `pip3 index versions`

**Research date:** 2026-05-29
**Valid until:** 2026-07-01 (stable libraries; Typer and Rich release infrequently)
