---
phase: 03-session-infrastructure-model-adapters
plan: 03
status: complete
completed: "2026-05-29"
requirements_covered:
  - SESS-01
  - SESS-04
key-files:
  created:
    - cipherbench/session/writer.py
    - cipherbench/session/model_runner.py
---

## Summary

Delivered the model session runner and atomic writer — the complete SESS-01 vertical slice. A `cipherbench run` session can now run end-to-end with a mock adapter: puzzle generated, engine created, 5 probes attempted, extraction failures tracked without consuming budget, inline checkpoint written after each attempt, final session JSON written atomically. 11 tests pass.

## What Was Built

**SessionWriter** (`cipherbench/session/writer.py`):
- `_atomic_write_json(path, data)` — tempfile.mkstemp + os.replace, no partial writes (T-03-03-01)
- `slugify_model(model)` — sanitises LiteLLM model strings for filenames (D-06)
- `make_session_id(slug, output_dir)` — timestamp + slug with same-second collision avoidance
- `SessionWriter.init_session()` — writes `outcome='in_progress'` at session start (D-17)
- `SessionWriter.write_checkpoint()` — overwrites file after every attempt (D-17)
- `SessionWriter.finalize(outcome, final_answer)` — writes terminal state + `completed_at`

**ModelSessionRunner** (`cipherbench/session/model_runner.py`):
- `run() -> dict` — probe-attempt loop: builds conversation, calls adapter, extracts probe, scores, checkpoints
- D-05 discipline: `extraction_failed=True` attempts recorded but do NOT consume the 5-attempt budget
- `MAX_TOTAL_ITERATIONS = 10` hard cap prevents adversarial infinite loops (T-03-03-02)
- `litellm.RateLimitError` caught after tenacity exhaustion → `outcome='rate_limited'` written and returned
- Final-answer 6th call only when no correct probe was found; `extract_answer()` parses response
- `create_model_session()` factory: generates puzzle, creates engine, builds full D-11 session record, writes `in_progress`, returns runner
- D-18 resume detection: scans `output_dir` for `rate_limited` sessions matching model+seed
- RNG isolation: uses `random.Random()` instance, never touches global `random` state

## Test Results

| Test | Status |
|------|--------|
| test_atomic_write_creates_file | ✓ PASS |
| test_atomic_write_is_idempotent_on_overwrite | ✓ PASS |
| test_in_progress_written_at_init | ✓ PASS |
| test_outcome_overwritten_on_finalize | ✓ PASS |
| test_session_json_written | ✓ PASS |
| test_checkpoint_written_after_each_attempt | ✓ PASS |
| test_outcome_transitions_to_success | ✓ PASS |
| test_outcome_transitions_to_failure | ✓ PASS |
| test_rate_limited_outcome_on_exhaustion | ✓ PASS |
| test_rng_does_not_pollute_global_random | ✓ PASS |
| test_extraction_failure_does_not_consume_attempt | ✓ PASS |
| **Total** | **11/11** |

Prior 76 tests (engine + puzzle + adapters) still green.

## Deviations

None. All must-haves delivered as specified.

## Self-Check: PASSED

- [x] Session JSON written to output_dir with `outcome='success'` or `'failure'` after 5 valid probes
- [x] `outcome='in_progress'` file exists immediately after session start
- [x] `extraction_failed=True` attempts recorded but valid-attempt budget unaffected (D-05)
- [x] `MAX_TOTAL_ITERATIONS = 2 * MAX_ATTEMPTS` cap present in code
- [x] `run()` returns dict with all D-11 SessionRecord fields
- [x] RNG isolation confirmed: global `random.getstate()` unchanged before/after run
