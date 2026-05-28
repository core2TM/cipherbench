---
phase: 02-puzzle-generator
plan: "01"
subsystem: types-and-layers
tags: [difficulty-config, state-change-rate, cross-char-depth, layers, tdd, backward-compat]
dependency_graph:
  requires: []
  provides: [DifficultyConfig.state_change_rate, DifficultyConfig.cross_char_depth, apply_cross_char_layer_multi]
  affects: [cipherbench/engine/rule_engine.py, cipherbench/puzzle.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, additive-accumulation, int-truncation-determinism]
key_files:
  created: []
  modified:
    - cipherbench/types.py
    - cipherbench/engine/layers.py
    - tests/unit/test_engine/test_types.py
    - tests/unit/test_engine/test_layers.py
decisions:
  - "int() truncation (not round()) for state_change_rate formula: deterministic floor-toward-zero, matches research Pattern 4"
  - "apply_cross_char_layer unchanged: new multi variant appended as separate function preserving backward compat for all Phase 1 callers"
  - "Import apply_cross_char_layer_multi at top of test_layers.py: ImportError itself serves as RED confirmation before implementation"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-29"
  tasks_completed: 2
  files_modified: 4
---

# Phase 02 Plan 01: Extend DifficultyConfig and Add apply_cross_char_layer_multi Summary

**One-liner:** Added `state_change_rate` and `cross_char_depth` fields to `DifficultyConfig` with validated constraints, and implemented `apply_cross_char_layer_multi` for configurable multi-depth cross-character mixing — all 47 Phase 1 tests still pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for DifficultyConfig new fields | 693f219 | tests/unit/test_engine/test_types.py |
| 1 (GREEN) | Extend DifficultyConfig with new fields and validation | ced2aad | cipherbench/types.py |
| 2 (RED) | Failing tests for apply_state_layer rate param and multi function | c38d5c3 | tests/unit/test_engine/test_layers.py |
| 2 (GREEN) | Extend apply_state_layer and add apply_cross_char_layer_multi | 64ab821 | cipherbench/engine/layers.py |

## What Was Built

### DifficultyConfig Extensions (cipherbench/types.py)

Two new fields added immediately after `output_length`:

- `state_change_rate: float = 1.0` — multiplier for the state layer shift formula; controls how aggressively effective shifts grow per round. Validated: must be > 0.0.
- `cross_char_depth: int = 1` — number of cross-character offset distances applied in sequence. Validated: must be in `[1, output_length - 1]`.

Both fields default to values preserving Phase 1 behavior exactly. `DifficultyConfig()` with no args is indistinguishable from Phase 1's version.

### apply_state_layer Extension (cipherbench/engine/layers.py)

Added `state_change_rate: float = 1.0` as the 5th parameter. Formula changed from:

```python
effective_shifts = [s * round_num for s in base_shifts]
```

to:

```python
effective_shifts = [int(s * round_num * state_change_rate) for s in base_shifts]
```

`int()` truncation (not `round()`) is used for deterministic floor-toward-zero behavior.

### apply_cross_char_layer_multi (cipherbench/engine/layers.py)

New pure function appended after `apply_cross_char_layer` (original is unchanged). Takes `k_list: list` instead of single `k: int` and accumulates cross-character offsets additively for each k value. Depth-1 guarantee: `k_list=[k]` produces identical output to `apply_cross_char_layer(k=k)`.

## Test Results

```
62 passed in 0.20s (47 original Phase 1 + 15 new Phase 2-01)

tests/test_properties.py               5 passed
tests/unit/test_engine/test_layers.py  22 passed  (16 original + 6 new)
tests/unit/test_engine/test_rule_engine.py  9 passed
tests/unit/test_engine/test_seeding.py  6 passed
tests/unit/test_engine/test_types.py   20 passed  (11 original + 9 new)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. No placeholder data or TODO markers in the implemented code.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. All changes are to pure in-memory data types and pure functions. Threat model items T-02-01-A and T-02-01-B (mitigate disposition) are fully resolved: `__post_init__` validates both `state_change_rate > 0.0` and `1 <= cross_char_depth <= output_length - 1`.

## TDD Gate Compliance

- RED gate (test commits): 693f219 (types), c38d5c3 (layers)
- GREEN gate (feat commits): ced2aad (types), 64ab821 (layers)
- Both RED and GREEN gates satisfied for both tasks.

## Self-Check: PASSED

- cipherbench/types.py: FOUND
- cipherbench/engine/layers.py: FOUND
- tests/unit/test_engine/test_types.py: FOUND
- tests/unit/test_engine/test_layers.py: FOUND
- Commit 693f219: FOUND
- Commit ced2aad: FOUND
- Commit c38d5c3: FOUND
- Commit 64ab821: FOUND
