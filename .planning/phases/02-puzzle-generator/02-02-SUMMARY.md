---
phase: 02-puzzle-generator
plan: "02"
subsystem: rule-engine
tags: [k-list, state-change-rate, cross-char-depth, rule-engine, rng-equivalence, backward-compat]
dependency_graph:
  requires: [02-01]
  provides: [RuleEngine._k_list, RuleEngine._state_change_rate, create_rule_engine.k_list]
  affects: [cipherbench/puzzle.py]
tech_stack:
  added: []
  patterns: [rng-sample-equivalence, k-list-multi-depth, factory-update]
key_files:
  created: []
  modified:
    - cipherbench/engine/rule_engine.py
decisions:
  - "rng.sample(range(1, n), depth) replaces rng.randint(1, n-1): call-count-equivalent for depth=1 (RESEARCH.md Pattern 3 / Assumption A1), generalizes cleanly for depth > 1"
  - "apply_cross_char_layer kept in imports alongside apply_cross_char_layer_multi: existing tests indirectly depend on importability of both"
  - "_state_change_rate stored as engine attribute (not recomputed each call): consistent with single-underscore private convention, enables verify in test_rule_engine.py"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-29"
  tasks_completed: 1
  files_modified: 1
---

# Phase 02 Plan 02: Update RuleEngine to use k_list and state_change_rate Summary

**One-liner:** Updated `RuleEngine.__init__` to accept `k_list: list` and store `_state_change_rate`, and updated `create_rule_engine` to use `rng.sample` for k_list generation — RNG call-count-equivalent for depth=1, enabling all 62 tests to pass with zero regressions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update RuleEngine and create_rule_engine to use k_list and state_change_rate | fe51cbc | cipherbench/engine/rule_engine.py |

## What Was Built

### Changes to cipherbench/engine/rule_engine.py

Four targeted changes made to the file:

**CHANGE 1 — Import block updated:**
`apply_cross_char_layer_multi` added to the `from cipherbench.engine.layers import (...)` block alongside the existing `apply_cross_char_layer` (kept for backward compat).

**CHANGE 2 — RuleEngine.__init__ signature and body:**
- Signature changed from `k: int` to `k_list: list` (D-03)
- Removed `self._k = k`
- Added `self._k_list = k_list`
- Added `self._state_change_rate = difficulty.state_change_rate` (D-02)
- Class docstring updated to reference `_k_list` and `_state_change_rate` instead of `_k`

**CHANGE 3 — RuleEngine._encode_for_round updated:**
- `apply_state_layer` call now passes `self._state_change_rate` as the 5th argument
- `apply_cross_char_layer` call replaced with `apply_cross_char_layer_multi` using `self._k_list`

**CHANGE 4 — create_rule_engine updated:**
- `k = rng.randint(1, n - 1)` replaced with `k_list = rng.sample(range(1, n), difficulty.cross_char_depth)`
- `return RuleEngine(k=k, ...)` updated to `return RuleEngine(k_list=k_list, ...)`
- Factory docstring updated to reference `k_list` and `cross_char_depth`

## Test Results

```
62 passed in 0.21s (all 62 tests, zero regressions)

tests/test_properties.py               5 passed
tests/unit/test_engine/test_layers.py  22 passed
tests/unit/test_engine/test_rule_engine.py  9 passed
tests/unit/test_engine/test_seeding.py  6 passed
tests/unit/test_engine/test_types.py   20 passed
```

## Spot Check Results

```
python3 -c "from cipherbench import create_rule_engine; e = create_rule_engine(42); print(type(e._k_list), e._k_list)"
→ <class 'list'> [2]  ✓

python3 -c "from cipherbench import create_rule_engine, DifficultyConfig; e = create_rule_engine(42, DifficultyConfig(state_change_rate=1.5)); print(e._state_change_rate)"
→ 1.5  ✓

python3 -c "... s1 = e1.score_attempt('ABCDE'); s2 = e2.score_attempt('ABCDE'); print(s1 == s2)"
→ True  ✓ (determinism at depth=1 preserved)

python3 -c "from cipherbench import create_rule_engine; e = create_rule_engine(42); print([m for m in dir(e) if not m.startswith('_')])"
→ ['score_attempt']  ✓ (information boundary unchanged)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. No placeholder data or TODO markers in the implemented code.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. All changes are targeted modifications to an existing in-memory stateful class. Threat model items:
- T-02-02-A (Information Disclosure — _k → _k_list rename): accepted — renaming does not reduce information boundary; `test_no_public_key_accessor` still passes.
- T-02-02-B (Tampering — rng.sample with cross_char_depth): mitigated — `DifficultyConfig.__post_init__` (Phase 02-01) enforces `1 <= cross_char_depth <= output_length - 1`, preventing `Sample larger than population` ValueError.
- T-02-02-C (Information Disclosure — local ciphertext): accepted — local variable pattern unchanged from Phase 1.

## Self-Check: PASSED

- cipherbench/engine/rule_engine.py: FOUND
- Commit fe51cbc: FOUND
- `self._k_list = k_list` in rule_engine.py: FOUND
- `self._state_change_rate = difficulty.state_change_rate` in rule_engine.py: FOUND
- `k_list = rng.sample(range(1, n), difficulty.cross_char_depth)` in rule_engine.py: FOUND
- `self._k = k` absent from rule_engine.py: CONFIRMED (removed)
- `k = rng.randint(1, n - 1)` absent from rule_engine.py: CONFIRMED (removed)
- `apply_cross_char_layer_multi` in rule_engine.py: FOUND
