---
phase: 04-scoring-reporting
plan: 04
subsystem: cli
tags: [cli, scoring, tdd, wave-3, score-command, live-summary, init-exports]
dependency_graph:
  requires: [04-03]
  provides: [cipherbench.cli.score_command, cipherbench.__init__.scoring-exports]
  affects: [cipherbench.cli.app, cipherbench.__init__]
tech_stack:
  added: []
  patterns: [TDD-RED-GREEN, Typer-Annotated-flags, lazy-import-wiring, ASVS-V5-path-resolve]
key_files:
  created: []
  modified:
    - cipherbench/cli/app.py
    - cipherbench/__init__.py
    - tests/unit/test_scoring/test_scorer.py
decisions:
  - "score_command uses lazy imports for scorer/reporter/report_writer — consistent with no-business-logic-in-app.py constraint"
  - "Path(sessions_dir).resolve() applied before passing to load_sessions — ASVS V5 path traversal guard (T-04-06)"
  - "render_live_summary uses aliased lazy import (_load_sessions, _render_live_summary) in run_command to avoid shadowing the local model variable"
  - "load_sessions, compute_report, ScoreReport added to cipherbench.__all__ — public SDK surface now complete"
metrics:
  duration: 8m
  completed_date: "2026-05-29"
  tasks_completed: 1
  files_created: 0
  files_modified: 3
---

# Phase 04 Plan 04: CLI Wiring — Score Subcommand and Live Summary

**One-liner:** TDD wiring of score subcommand (D-02 flags, path traversal guard) and run_command live summary (D-03) into the CLI; scoring exports added to cipherbench.__init__ — all 22 Phase 4 tests green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Unskip test_score_command_help | 2c0c763 | tests/unit/test_scoring/test_scorer.py |
| 1 (GREEN) | Wire score_command + live summary + __init__ exports | d91e935 | cipherbench/cli/app.py, cipherbench/__init__.py |

## Checkpoint Pending

Task 2 (checkpoint:human-verify) reached — awaiting human verification of end-to-end CLI behavior.

## Verification Results

- `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_score_command_help -x -q` — 1 passed
- `python3 -m pytest tests/unit/test_scoring/ -v` — 22 passed, 0 skipped
- `python3 -m pytest tests/ -q` — 136 passed, 0 skipped, 0 failed
- `grep -c "@app.command(name=\"score\")" cipherbench/cli/app.py` — 1
- `grep -c "render_live_summary" cipherbench/cli/app.py` — 2 (import alias + call)
- `python3 -c "from cipherbench import load_sessions, compute_report, ScoreReport"` — exits 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. CLI wiring is complete. All scoring modules fully implemented.

## TDD Gate Compliance

- RED gate commit `2c0c763` (unskip test_score_command_help) — FOUND
- GREEN gate commit `d91e935` (wire score_command + live summary) — FOUND

## Threat Flags

None beyond plan scope:
- T-04-06 (path traversal — sessions_dir): mitigated via Path(sessions_dir).resolve()
- T-04-07 (output_file write path): accepted
- T-04-08 (model string filter): accepted
- T-04-09 (model name echoed): accepted

## Self-Check: PASSED

- cipherbench/cli/app.py: FOUND — score_command wired, render_live_summary injected
- cipherbench/__init__.py: FOUND — load_sessions, compute_report, ScoreReport exported
- tests/unit/test_scoring/test_scorer.py: FOUND — test_score_command_help unskipped and passing
- Commit 2c0c763: FOUND (RED gate)
- Commit d91e935: FOUND (GREEN gate)
- Full suite: 136 passed, 0 failed
