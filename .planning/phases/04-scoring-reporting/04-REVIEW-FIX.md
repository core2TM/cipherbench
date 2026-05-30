---
phase: 04-scoring-reporting
iteration: 1
fix_scope: critical_warning
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-05-29T00:00:00Z
**Source review:** .planning/phases/04-scoring-reporting/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: output_file not path-resolved — asymmetric write-path traversal gap

**Files modified:** `cipherbench/cli/app.py`
**Commit:** f430937
**Applied fix:** Added `resolved_output = Path(output_file).resolve()` before passing to `write_json_report`, matching the existing ASVS V5 T-04-06 guard applied to `sessions_dir`. The raw `Path(output_file)` call is replaced by `resolved_output` so directory traversal via `--output-file ../../../etc/cron.d/evil` is now blocked.

---

### CR-02: run_command live summary loads all historical sessions — inflated results

**Files modified:** `cipherbench/cli/app.py`
**Commit:** 09937f6
**Applied fix:** Introduced `current_run_sessions: list[dict] = []` before the loop and appended each `session_record` returned by `runner.run()` inside the inner loop. The live summary now calls `_render_live_summary(current_run_sessions, human_baseline)` using only the sessions from the current invocation, eliminating the disk re-read that globbed all historical sessions for the model.

---

### WR-01: Model label in score panel is "human" when --model not provided and --human not set

**Files modified:** `cipherbench/cli/app.py`
**Commit:** bebc50b
**Applied fix:** Replaced `model=model or "human"` with an explicit ternary:
`label = model if model is not None else ("human" if human else "(all models)")`
The panel now correctly shows the model name when `--model` is set, "human" when `--human` is set, or "(all models)" when neither flag is provided.

---

### WR-02: --seed with --num-puzzles > 1 silently repeats the same puzzle

**Files modified:** `cipherbench/cli/app.py`
**Commit:** d1a34b6
**Applied fix:** Replaced the inline `puzzle_seed = seed if seed is not None else random.Random().randint(...)` inside the loop with `puzzle_rng = random.Random(seed)` before the loop, then `puzzle_seed = puzzle_rng.randint(0, 2**32 - 1)` per iteration. When `--seed` is provided every puzzle gets a distinct deterministically derived seed; when no seed is provided `random.Random(None)` samples OS entropy as before. This matches the documented behaviour ("distinct puzzles") without requiring an external warning.

---

### WR-03: Bare session["outcome"] accesses in public API functions

**Files modified:** `cipherbench/scoring/scorer.py`, `cipherbench/scoring/reporter.py`
**Commit:** f619425
**Applied fix:** Changed all three bare dict key accesses to `.get("outcome")`:
- `scorer.py` `efficiency_score` line 118: `session["outcome"]` → `session.get("outcome")`
- `scorer.py` `success_rate` line 134: `s["outcome"]` → `s.get("outcome")`
- `reporter.py` `render_live_summary` line 107: `s["outcome"]` → `s.get("outcome")`

SDK callers passing dicts without an `"outcome"` key now receive a graceful `False` comparison rather than an unhelpful `KeyError`.

---

### WR-04: write_json_report has no error handling — raw traceback on I/O failure

**Files modified:** `cipherbench/scoring/report_writer.py`, `cipherbench/cli/app.py`
**Commit:** ea33ba3
**Applied fix:**
- `report_writer.py`: Wrapped `mkdir` and `open` in `try/except OSError`; on failure, logs the error via the existing `logger.error` and re-raises.
- `cli/app.py` `score_command`: Wrapped the `write_json_report` call in `try/except OSError`; on failure, prints `"Error: could not write report: {exc}"` to stderr and exits with code 1 via `typer.Exit(code=1)`.

---

_Fixed: 2026-05-29T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
