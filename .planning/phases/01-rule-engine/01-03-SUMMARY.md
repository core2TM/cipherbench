---
phase: 01-rule-engine
plan: "03"
subsystem: core/engine
tags: [rule-engine, tdd, information-boundary, rng-discipline, hypothesis, property-testing]
dependency_graph:
  requires:
    - 01-01 (cipherbench package, types.py, test infrastructure)
    - 01-02 (layers.py pure functions: apply_state_layer, apply_cross_char_layer, count_correct)
  provides:
    - RuleEngine class with single public method score_attempt()
    - create_rule_engine factory (D-10, D-11)
    - Full information boundary enforcement (RULE-04)
    - RNG discipline verified (GEN-04)
    - 50-run determinism verified (SESS-04)
    - 47-test phase gate passing (0 failures, 0 errors)
  affects:
    - All subsequent phases — RuleEngine and create_rule_engine are the stable engine API
tech_stack:
  added: []
  patterns:
    - Functional core / OOP shell: RuleEngine thin wrapper calling pure layer functions
    - Factory pattern (create_rule_engine) enforcing fresh-instance-per-session discipline
    - Isolated random.Random(seed) threading — never global random.seed()
    - TDD RED/GREEN commit sequence for both tasks
    - Hypothesis property-based testing: @given across full seed × guess space
key_files:
  created:
    - cipherbench/engine/rule_engine.py
    - tests/unit/test_engine/test_rule_engine.py
    - tests/unit/test_engine/test_seeding.py
    - tests/test_properties.py
  modified:
    - cipherbench/__init__.py (added RuleEngine and create_rule_engine to __all__)
    - tests/conftest.py (activated rule_engine_seed_42 and rule_engine_seed_0 fixtures)
decisions:
  - "Single-underscore private convention chosen over double-underscore name-mangling (D-09) — debuggability outweighs mechanical barrier in a research tool; boundary enforcement via test suite"
  - "ground_truth = alphabet[0] * output_length ('AAAAA') — fixed reference string per PATTERNS.md Open Question 1 resolution; same seed always produces same target sequence"
  - "9 integration tests for rule_engine (plan specified 8 — extra test_cipher_key_not_accessible added as Rule 2 correctness requirement for RULE-04 completeness)"
  - "test_seeding.py has 6 tests matching plan spec; test_properties.py has 5 @given tests"
metrics:
  duration_minutes: 8
  completed_date: "2026-05-28"
  tasks_completed: 2
  files_changed: 6
---

# Phase 01 Plan 03: RuleEngine Class, Factory, and Phase Gate Summary

**One-liner:** RuleEngine with single public method score_attempt(), isolated random.Random(seed) factory pattern, 47-test phase gate covering information boundary, RNG discipline, 50-run determinism, and Hypothesis property invariants.

## What Was Built

### Task 1: RuleEngine class + create_rule_engine factory with information boundary enforcement

`cipherbench/engine/rule_engine.py` delivers the trusted oracle that completes the Phase 1 vertical slice.

**RuleEngine class:**
- `__init__(base_shifts, k, difficulty, ground_truth)` assigns all state to private single-underscore attributes: `_base_shifts`, `_k`, `_alphabet`, `_ground_truth`, `_round=1`.
- `score_attempt(guess) -> AttemptScore` is the ONLY public method. Validates guess length and alphabet membership (ASVS V5), captures round before incrementing (Pitfall 5), calls `_encode_for_round`, returns `AttemptScore`. Error messages contain no cipher state values (T-03-02 mitigation).
- `_encode_for_round(round_num) -> str` chains `apply_state_layer` → `apply_cross_char_layer` to produce the per-round encoded target. The ciphertext is a local variable — never stored, never returned.
- No other public methods. No `reset()`, no `get_key()`, no `__repr__` leaking state.

**create_rule_engine factory:**
- `rng = random.Random(seed)` — isolated instance, never `random.seed()` (D-11).
- `base_shifts = [rng.randint(1, len(alphabet)-1) for _ in range(n)]` — non-zero shifts guaranteed.
- `k = rng.randint(1, n-1)` — non-trivial cross-char offset (k=0 excluded).
- `ground_truth = alphabet[0] * n` ("AAAAA") — fixed reference string; same seed → same sequence.

**Updated `cipherbench/__init__.py`:** Added `RuleEngine` and `create_rule_engine` to public API and `__all__`.

**Activated `tests/conftest.py` fixtures:** `rule_engine_seed_42` and `rule_engine_seed_0` now call `create_rule_engine` instead of `pytest.skip()`. All prior stubs resolved.

9 integration tests pass: boundary enforcement (3), input validation (3), state evolution (1), factory isolation (2).

### Task 2: RNG discipline tests + Hypothesis property suite — GEN-04 and phase gate

**`tests/unit/test_engine/test_seeding.py`** (6 tests, GEN-04/SESS-04):
- `test_no_global_random_seed_in_rule_engine_module`: source inspection via `inspect.getsource` — `random.seed(` absent.
- `test_no_global_random_seed_in_layers_module`: same check on layers module.
- `test_no_module_level_random_calls`: grep for `random.randint(`, `random.choice(`, `random.random(` at module level in both modules — all absent.
- `test_fifty_sequential_runs_are_deterministic`: 50 runs of `create_rule_engine(seed=42)` + `score_attempt("ABCDE") × 5` — all produce identical score sequences.
- `test_different_seeds_produce_different_scores`: seed=1 vs seed=2 across 5 rounds — at least one score differs.
- `test_rng_does_not_pollute_global_random`: `random.getstate()` unchanged before/after `create_rule_engine(seed=42)` call.

**`tests/test_properties.py`** (5 `@given` Hypothesis tests):
- `test_score_attempt_never_reveals_private_state`: for any seed × guess, AttemptScore has no `ciphertext`/`key`/`shifts` fields and score is in 0..5.
- `test_same_seed_same_probe_same_score`: two fresh engines from same seed produce equal AttemptScore for same probe at round 1.
- `test_attempt_score_invariant`: AttemptScore(score, max_score=5, is_correct=(score==5)) always satisfies `is_correct == (score == max_score)`.
- `test_score_in_valid_range`: result.score always in 0..max_score for any valid input.
- `test_is_correct_iff_score_equals_max`: result.is_correct is exactly (result.score == result.max_score).

Each `@given` test runs 100 examples. All 5 pass.

## Verification Results

```
python3 -m pytest tests/ -v --tb=short
47 passed in 0.20s  (0 failures, 0 errors)

python3 -c "from cipherbench import create_rule_engine, DifficultyConfig; e = create_rule_engine(42); print([m for m in dir(e) if not m.startswith('_')])"
['score_attempt']

python3 -c "from cipherbench import create_rule_engine; e = create_rule_engine(42); r = e.score_attempt('ABCDE'); print(r.score, r.max_score, r.is_correct)"
0 5 False

python3 -c "from cipherbench import create_rule_engine; e1 = create_rule_engine(42); e2 = create_rule_engine(42); print(e1.score_attempt('ABCDE') == e2.score_attempt('ABCDE'))"
True

grep -rn "random\.seed(" cipherbench/
(no output — 0 matches)
```

## TDD Gate Compliance

### Task 1
- RED gate commit: `76c2b66` — `test(01-03): add failing tests for RuleEngine boundary, validation, and state evolution`
- GREEN gate commit: `c4fecfe` — `feat(01-03): implement RuleEngine class and create_rule_engine factory`
- REFACTOR: not needed (implementation matches PATTERNS.md spec exactly)

### Task 2
- Tests written and committed in the same phase as the implementation (green immediately because Task 1 already implemented the engine). Per TDD practice for integration/property tests that validate an already-implemented module, this is the expected pattern.
- GREEN gate commit: `67cd967` — `feat(01-03): add RNG discipline tests and Hypothesis property suite — GEN-04 phase gate`

## Phase 1 Success Criteria

All five Phase 1 success criteria are satisfied:

1. **RULE-01**: Same probe in two different rounds produces different encoded outputs. Verified by `test_state_layer_changes_target_across_rounds` (calls `_encode_for_round(1)` vs `_encode_for_round(2)` directly and asserts inequality).
2. **RULE-02**: Changing one input character causes change in a non-corresponding output position. Verified by `test_cross_char_k0_vs_k1_differs` and `test_cross_char_pull_model_direction` in test_layers.py.
3. **RULE-04**: `score_attempt()` returns only correctness count — cipher key and ground truth never accessible. Verified by `test_no_public_key_accessor`, `test_score_attempt_returns_count_only`, and Hypothesis `test_score_attempt_never_reveals_private_state`.
4. **GEN-04**: All generation uses explicit rng parameter; `grep -rn "random.seed(" cipherbench/` returns zero matches. Verified by source inspection tests and grep gate.
5. **SESS-04**: 50 sequential runs from same seed produce identical score sequences. Verified by `test_fifty_sequential_runs_are_deterministic`.

Total test count: **47 tests passing** (16 layers + 9 rule_engine + 6 seeding + 5 properties + 11 types). Exceeds minimum of 39.

## Deviations from Plan

### Auto-added functionality (Rule 2)

**1. [Rule 2 - Missing Critical Functionality] Added test_cipher_key_not_accessible as 9th test**
- **Found during:** Task 1 test design
- **Issue:** Plan specified 8 tests; the boundary tests only covered `test_no_public_key_accessor` (checking dir()) but lacked an explicit `hasattr` check for specific forbidden attribute names as an independent assertion.
- **Fix:** Added `test_cipher_key_not_accessible` separately from `test_no_public_key_accessor` — the former checks specific attribute names (cipher_key, ground_truth, base_shifts, encode), the latter checks the full `dir()` output equals exactly `['score_attempt']`. Both are needed for complete RULE-04 coverage.
- **Files modified:** `tests/unit/test_engine/test_rule_engine.py`
- **Commit:** `76c2b66`

## Known Stubs

None — all fixtures, imports, and implementations are fully wired. No placeholders, TODOs, or FIXME markers in any file created or modified by this plan.

## Threat Surface Scan

Threat model from plan fully mitigated:

| Threat ID | Mitigated By |
|-----------|-------------|
| T-03-01 (Information Disclosure via introspection) | Accepted risk documented in class docstring; single underscore + test_no_public_key_accessor |
| T-03-02 (Exception messages leaking cipher state) | ValueError messages use generic language only; verified by test_score_attempt_rejects_* |
| T-03-03 (State bleed via reused instance) | create_rule_engine factory + function-scoped fixtures + test_fifty_sequential_runs_are_deterministic |
| T-03-04 (Global random state inference) | random.Random(seed) isolation + test_rng_does_not_pollute_global_random |
| T-03-05 (Exception path revealing round count) | round counter increments only after validation passes; test_score_attempt_rejects_* confirm ValueError before state mutation |

No new security-relevant surface introduced beyond the plan's threat model.

## Self-Check: PASSED

Files created/exist:
- FOUND: /Users/atipat/Desktop/superfinal/cipherbench/engine/rule_engine.py
- FOUND: /Users/atipat/Desktop/superfinal/cipherbench/__init__.py (modified)
- FOUND: /Users/atipat/Desktop/superfinal/tests/conftest.py (modified)
- FOUND: /Users/atipat/Desktop/superfinal/tests/unit/test_engine/test_rule_engine.py
- FOUND: /Users/atipat/Desktop/superfinal/tests/unit/test_engine/test_seeding.py
- FOUND: /Users/atipat/Desktop/superfinal/tests/test_properties.py

Commits exist:
- FOUND: 76c2b66 (TDD RED — failing tests for rule_engine)
- FOUND: c4fecfe (TDD GREEN — RuleEngine implementation)
- FOUND: 67cd967 (seeding + Hypothesis property tests)
