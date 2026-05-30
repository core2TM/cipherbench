---
phase: 04-scoring-reporting
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - cipherbench/__init__.py
  - cipherbench/cli/app.py
  - cipherbench/scoring/__init__.py
  - cipherbench/scoring/reporter.py
  - cipherbench/scoring/report_writer.py
  - cipherbench/scoring/scorer.py
  - tests/unit/test_scoring/__init__.py
  - tests/unit/test_scoring/test_reporter.py
  - tests/unit/test_scoring/test_report_writer.py
  - tests/unit/test_scoring/test_scorer.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-05-29T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the Phase 4 scoring and reporting subsystem: `scorer.py` (pure computation), `reporter.py` (Rich terminal output), `report_writer.py` (JSON file write), the `score` subcommand in `cli/app.py`, updated `__init__.py` exports, and three test modules.

The SCORE-02 efficiency formula is correctly clamped, the divide-by-zero guard for SCORE-03 is present, malformed JSON is skipped, and JSON `null` (not string "N/A") is correctly used for absent AGI proximity. Two blockers were found: `output_file` in `score_command` is written without path resolution, creating an asymmetric path-traversal gap that the adjacent ASVS V5 comment implies was fully addressed; and `run_command`'s post-run live summary reloads all historical sessions for the model rather than only those generated in the current invocation, producing inflated results. Four warnings cover a misleading model label when `--model` is omitted, an undocumented seed-reuse behaviour with `--num-puzzles > 1`, bare `dict["outcome"]` accesses in the public API surface, and unhandled I/O exceptions in `write_json_report`. Three info items address test helper duplication, a missing test for malformed-JSON skipping, and a cross-difficulty mixing issue in the totals AGI proximity calculation.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `output_file` not path-resolved — asymmetric write-path traversal gap

**File:** `cipherbench/cli/app.py:175`

**Issue:** `score_command` correctly calls `Path(sessions_dir).resolve()` on line 161 (with an explicit ASVS V5 T-04-06 comment) before passing the path to `load_sessions`. The write path on line 175 has no corresponding guard:

```python
if output_file:
    write_json_report(report, Path(output_file))   # no .resolve()
```

`write_json_report` immediately calls `output_file.parent.mkdir(parents=True, exist_ok=True)` on a raw, unresolved `Path`. A caller supplying `--output-file ../../../etc/cron.d/evil` will have those directories created and the file written without any traversal check. The inconsistency is especially visible because the code demonstrates awareness of this class of vulnerability one line earlier.

**Fix:**
```python
if output_file:
    resolved_output = Path(output_file).resolve()
    write_json_report(report, resolved_output)
```

---

### CR-02: `run_command` live summary loads all historical sessions — inflated results

**File:** `cipherbench/cli/app.py:111`

**Issue:** After the run loop completes, the live summary is populated by:

```python
completed_sessions = _load_sessions(out_path, runner_type="model", model=model)
```

`load_sessions` globs every `*.json` file in `out_path` matching `runner_type="model"` and `model=model` — including sessions from all prior invocations of `cipherbench run` written to the same output directory. Running 5 sessions against a model that already has 100 historical sessions in `./sessions` will display a live summary reporting 105 sessions, not 5. The comment on line 108 (`# D-01, D-03: live summary after all sessions complete`) and the D-03 docstring in `reporter.py` both describe this as showing the current run's results.

**Fix:** Collect `session_record` objects returned by `runner.run()` inside the loop rather than re-reading from disk:

```python
current_run_sessions: list[dict] = []

for puzzle_idx in range(num_puzzles):
    puzzle_seed = seed if seed is not None else random.Random().randint(0, 2**32 - 1)
    for run_idx in range(runs_per_puzzle):
        adapter = LiteLLMAdapter(model, litellm_config_path=litellm_config)
        runner = create_model_session(puzzle_seed, config, adapter, out_path)
        session_record = runner.run()
        current_run_sessions.append(session_record)
        typer.echo(
            f"Puzzle {puzzle_idx + 1}/{num_puzzles} Run {run_idx + 1}/{runs_per_puzzle}: "
            f"seed={puzzle_seed} outcome={session_record['outcome']}"
        )

from cipherbench.scoring.reporter import render_live_summary as _render_live_summary
from cipherbench.scoring.scorer import load_sessions as _load_sessions
human_baseline = _load_sessions(out_path, runner_type="human")
_render_live_summary(current_run_sessions, human_baseline)
```

---

## Warnings

### WR-01: Model label in score panel is "human" when `--model` not provided and `--human` not set

**File:** `cipherbench/cli/app.py:172`

**Issue:**

```python
render_score_report(report, model=model or "human")
```

When the user runs `cipherbench score` without `--model` and without `--human`, `model` is `None`. `None or "human"` evaluates to `"human"`, so the Rich panel header prints `Model: human` while the report is actually scoring all model sessions (`runner_type="model"`). A user running an aggregate report across all models sees a heading that says "human" in a model-session context, which is directly misleading.

**Fix:**
```python
label = model if model is not None else ("human" if human else "(all models)")
render_score_report(report, model=label)
```

---

### WR-02: `--seed` with `--num-puzzles > 1` silently repeats the same puzzle

**File:** `cipherbench/cli/app.py:95-97`

**Issue:** Inside the outer `for puzzle_idx` loop:

```python
puzzle_seed = seed if seed is not None else random.Random().randint(0, 2**32 - 1)
```

When `--seed` is provided, `puzzle_seed` is always the same value for every `puzzle_idx` iteration. Running `cipherbench run --seed 42 --num-puzzles 5` generates the same puzzle five times. No warning is issued. The `--num-puzzles` help text says "Number of **distinct** puzzles to run", making this a silent contradiction between the documented behaviour and the implementation.

**Fix:** Either emit a warning when the combination is detected, or derive distinct per-puzzle seeds deterministically from the root seed:

```python
# Option A: warn
if seed is not None and num_puzzles > 1:
    typer.echo(
        "Warning: --seed with --num-puzzles > 1 generates the same puzzle repeatedly.",
        err=True,
    )

# Option B: derive distinct seeds preserving reproducibility
rng = random.Random(seed)
for puzzle_idx in range(num_puzzles):
    puzzle_seed = rng.randint(0, 2**32 - 1)
    for run_idx in range(runs_per_puzzle):
        ...
```

---

### WR-03: Bare `session["outcome"]` accesses in public API functions

**Files:** `cipherbench/scoring/scorer.py:118`, `cipherbench/scoring/scorer.py:134`, `cipherbench/scoring/reporter.py:107`

**Issue:** `efficiency_score` (line 118), `success_rate` (line 134), and `render_live_summary` (line 107) use bare `session["outcome"]` / `s["outcome"]` dict access. These functions are part of the public SDK surface exported from `cipherbench.__init__`. An SDK caller passing a session dict without an `"outcome"` key — for example a partially constructed dict, a dict from an older schema version, or a test fixture that omits the field — receives an unhelpful `KeyError` with no indication of which field is missing or which function expected it.

`load_sessions` guarantees the key is present for all sessions it returns, so the production CLI pipeline is safe. The public API contract is the concern.

**Fix:**
```python
# scorer.py efficiency_score line 118:
success = 1 if session.get("outcome") == "success" else 0

# scorer.py success_rate line 134:
return sum(1 for s in sessions if s.get("outcome") == "success") / len(sessions)

# reporter.py render_live_summary line 107:
successes = sum(1 for s in sessions if s.get("outcome") == "success")
```

---

### WR-04: `write_json_report` has no error handling — raw traceback on I/O failure

**File:** `cipherbench/scoring/report_writer.py:32-34`

**Issue:** Both `mkdir` and `open` can raise `PermissionError`, `OSError`, or `FileExistsError`. Neither call is wrapped. When `write_json_report` is called from `score_command`, any I/O failure propagates as an unhandled exception and prints a full Python traceback to the user rather than a clean CLI error message. The `logger` is defined at line 16 but never called in the error path.

**Fix:**
```python
def write_json_report(report: dict, output_file: Path) -> None:
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("Score report written to %s", output_file)
    except OSError as exc:
        logger.error("Failed to write score report to %s: %s", output_file, exc)
        raise
```

The `score_command` caller should then catch and render a clean error:
```python
try:
    write_json_report(report, resolved_output)
except OSError as exc:
    typer.echo(f"Error: could not write report: {exc}", err=True)
    raise typer.Exit(code=1)
```

---

## Info

### IN-01: `totals` AGI proximity mixes difficulty tiers — cross-tier comparison may be unfair

**File:** `cipherbench/scoring/scorer.py:220`

**Issue:** Per-tier AGI proximity correctly tier-matches human sessions (line 197: `human_by_tier.get(tier, [])`), satisfying D-08. However, the `totals` row calls:

```python
agi_proximity=agi_proximity(model_sessions, human_sessions),
```

This computes the ratio using all model sessions (possibly a mix of easy/medium/hard) against all human sessions (also mixed). If the model was benchmarked only on `hard` puzzles but the human baseline is predominantly `easy` sessions, the aggregate proximity ratio is not a fair comparison. Design decision D-09 does not specify whether totals should be tier-matched or aggregated, so this may be intentional — but it should be documented.

---

### IN-02: `_make_session` helper is duplicated verbatim in two test files

**Files:** `tests/unit/test_scoring/test_scorer.py:18-59`, `tests/unit/test_scoring/test_reporter.py:15-51`

**Issue:** The `_make_session` function is copy-pasted identically (same body, same docstring) into both test files. Any change to the `SessionRecord` schema requires updating both copies, creating a maintenance hazard and risk of silent divergence.

**Fix:** Move `_make_session` to `tests/unit/test_scoring/conftest.py` as a pytest fixture or a shared module-level helper, and import it in both test files.

---

### IN-03: No test covers the malformed-JSON-skipping path in `load_sessions`

**File:** `tests/unit/test_scoring/test_scorer.py`

**Issue:** The code comment at `scorer.py:88` references "Pitfall 2 / T-04-01: skip malformed or unreadable files silently," but there is no test that writes an invalid JSON file to `tmp_sessions_dir` and verifies `load_sessions` returns `[]` rather than raising. The silent-skip behavior — which could mask data loss — goes untested.

**Fix:**
```python
def test_load_sessions_skips_malformed_json(tmp_sessions_dir):
    tmp_sessions_dir.mkdir(parents=True)
    (tmp_sessions_dir / "bad.json").write_text("not valid json{{{")
    result = load_sessions(tmp_sessions_dir, runner_type="model")
    assert result == []
```

---

_Reviewed: 2026-05-29T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
