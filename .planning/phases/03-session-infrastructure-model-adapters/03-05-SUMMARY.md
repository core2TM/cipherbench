---
phase: 03-session-infrastructure-model-adapters
plan: 05
status: complete
completed: "2026-05-29"
duration: "<2 minutes"
requirements_covered:
  - SESS-04
tags:
  - determinism
  - integration-tests
  - rng-isolation
  - session-runner
subsystem: session
dependency_graph:
  requires:
    - 03-04 (ModelSessionRunner, create_model_session, FixedResponseAdapter)
  provides:
    - SESS-04 phase gate cleared
    - 50-run determinism proof
    - global-random non-pollution proof
    - seed-isolation proof
  affects:
    - Phase 3 completion gate
tech_stack:
  added: []
  patterns:
    - 50-run loop determinism test (session-level analogue of engine test_seeding.py)
    - tmp_path subdirectory isolation per run (prevents resume detection false-positives)
    - random.getstate() / getstate() RNG pollution check
key_files:
  created: []
  modified:
    - tests/integration/test_determinism.py
decisions:
  - "Used `tmp_path / f'run_{run}'` per-run subdirectory in 50-run loop to prevent D-18 resume detection treating run N+1 as continuation of run N — session isolation is a correctness requirement (T-03-05-01)"
  - "Imported FixedResponseAdapter directly from tests.conftest (non-fixture class) instead of defining locally — DRY; conftest exposes it as a plain class"
  - "Used EASY difficulty (10-char alphabet) — faster 50 runs, valid ABCDE probe in alphabet, deterministic failure outcome for seed=42"
metrics:
  duration: "<2 minutes"
  completed_date: "2026-05-29"
  tasks_completed: 1
  files_modified: 1
---

# Phase 03 Plan 05: SESS-04 Determinism Integration Tests Summary

SESS-04 phase gate implemented: 50 sequential sessions from seed=42 with FixedResponseAdapter produce identical outcomes; global random state unaffected; different seeds produce different score sequences.

## What Was Built

**`tests/integration/test_determinism.py`** — replaced pytest.fail stubs from Plan 01 with 3 fully-implemented integration tests:

1. **`test_fifty_sequential_sessions_are_deterministic`** — runs 50 sequential `create_model_session(seed=42, difficulty=EASY, adapter=FixedResponseAdapter("PROBE: ABCDE"), output_dir=tmp_path/run_{run})` calls, asserts all 50 `session["outcome"]` values are identical. Each run writes to its own subdirectory (`run_0` through `run_49`) to prevent D-18 resume detection from treating iteration N+1 as a continuation of iteration N (T-03-05-01 mitigation).

2. **`test_different_seeds_produce_different_session_outcomes`** — runs 1 session each for seed=42 and seed=99 with identical `PROBE: ABCDE` response. Extracts score sequences from `session["attempts"]` for each seed. Asserts `scores_a != scores_b` — different cipher keys from different seeds cause the same probe to score differently.

3. **`test_session_runner_does_not_pollute_global_random`** — saves `random.getstate()` before and after a full `ModelSessionRunner.run()` call and asserts they are identical, verifying D-11 RNG isolation discipline is maintained throughout the session pipeline.

## Test Results

| Test | Status |
|------|--------|
| test_fifty_sequential_sessions_are_deterministic | PASS |
| test_different_seeds_produce_different_session_outcomes | PASS |
| test_session_runner_does_not_pollute_global_random | PASS |
| **Targeted total** | **3/3** |

Full suite (excluding litellm adapter stubs): **108 passed**

## Deviations from Plan

None — plan executed exactly as written. The 3 tests match the behavior spec in the plan. Import of `FixedResponseAdapter` directly from `tests.conftest` worked as the class is a plain (non-fixture) class available for import.

## Known Stubs

None. All test implementations are complete. No placeholder or TODO bodies remain in `test_determinism.py`.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Tests write to pytest's `tmp_path` (managed by pytest, auto-cleaned). No threat flags.

## Self-Check: PASSED

- [x] `tests/integration/test_determinism.py` exists with 3 fully-implemented tests (no pytest.fail bodies)
- [x] `grep -c "range(50)" tests/integration/test_determinism.py` returns 1
- [x] `pytest tests/integration/test_determinism.py -v` exits 0 — 3/3 tests passed
- [x] `pytest tests/ --ignore=tests/unit/test_adapters -x -q` exits 0 — 108 passed
- [x] Commit cc6013c verified: `feat(03-05): implement SESS-04 determinism integration tests`
- [x] T-03-05-01 mitigated: each of 50 runs writes to `tmp_path / f"run_{run}"` subdirectory
- [x] "State bleed detected" assertion message present in 50-run loop (mirrors test_seeding.py style)
- [x] global random.getstate() comparison test present
