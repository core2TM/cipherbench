---
phase: 02-puzzle-generator
plan: "03"
subsystem: puzzle-generator
tags: [puzzle, frozen-dataclass, sha256, reproducibility, difficulty-tiers, hypothesis]
dependency_graph:
  requires: [02-02]
  provides: [cipherbench/puzzle.py, Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD]
  affects: [cipherbench/__init__.py, Phase 3 Session Infrastructure]
tech_stack:
  added: []
  patterns: [frozen-dataclass, sha256-hash, factory-function, hypothesis-property-test]
key_files:
  created:
    - cipherbench/puzzle.py
    - tests/unit/test_puzzle/__init__.py
    - tests/unit/test_puzzle/test_puzzle.py
  modified:
    - cipherbench/__init__.py
decisions:
  - "json.dumps(sort_keys=True) for hash serialization guarantees cross-platform stability on int/str values (T-02-03-E)"
  - "k_list always serialized as JSON array even at depth=1, preventing scalar-vs-array hash divergence (Pitfall 4)"
  - "All four DifficultyConfig fields explicit in EASY/MEDIUM/HARD constants to avoid get_tier fragility when new fields are added (Pitfall 6)"
  - "Puzzle.create_engine() delegates entirely to create_rule_engine — no RNG state stored in Puzzle (D-05)"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 4
---

# Phase 02 Plan 03: Puzzle Frozen Dataclass, Factory, and Test Suite Summary

**One-liner:** Puzzle frozen dataclass with SHA-256 hash of derived engine state (`base_shifts + k_list + ground_truth`), `generate_puzzle` / `verify_puzzle` / `get_tier` functions, and `EASY/MEDIUM/HARD` tier constants — completing the Phase 2 deliverable with 75 tests passing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create Puzzle frozen dataclass, generate_puzzle, verify_puzzle, get_tier, EASY/MEDIUM/HARD | 75a5ae7 | cipherbench/puzzle.py, cipherbench/__init__.py, tests/unit/test_puzzle/__init__.py |
| 2 | Write comprehensive test_puzzle.py covering GEN-01, GEN-02, GEN-03 with Hypothesis | faf67da | tests/unit/test_puzzle/test_puzzle.py |

## What Was Built

### cipherbench/puzzle.py

**`Puzzle` frozen dataclass (D-04, D-05):**
- Three fields: `seed: int`, `difficulty: DifficultyConfig`, `puzzle_hash: str`
- `__post_init__` validates seed is int and puzzle_hash is non-empty
- `create_engine()` method returns a fresh `RuleEngine` via `create_rule_engine(self.seed, self.difficulty)` — each call is independent

**`_compute_hash` private helper (D-07, D-08):**
- Serializes `{"base_shifts": ..., "ground_truth": ..., "k_list": ...}` with `json.dumps(sort_keys=True)` for determinism
- Returns `hashlib.sha256(payload).hexdigest()` — 64-char hex string
- k_list always serialized as JSON array (Pitfall 4 prevention)

**`generate_puzzle` factory (GEN-01, GEN-02, D-06):**
- Only authorized Puzzle constructor
- Calls `create_rule_engine(seed, difficulty)` and hashes derived state
- Delegates all RNG to `create_rule_engine` — no `random.*` calls in puzzle.py

**`verify_puzzle` integrity function (GEN-02, D-09):**
- Re-derives hash from `puzzle.seed + puzzle.difficulty`
- Raises `ValueError("hash mismatch: expected {X}, got {Y}")` on mismatch

**Tier constants (D-10, D-11):**
- `EASY = DifficultyConfig(alphabet="ABCDEFGHIJ", output_length=5, state_change_rate=1.0, cross_char_depth=1)`
- `MEDIUM = DifficultyConfig(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", output_length=5, state_change_rate=1.5, cross_char_depth=2)`
- `HARD = DifficultyConfig(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", output_length=5, state_change_rate=2.0, cross_char_depth=3)`

**`get_tier` classifier (D-12):**
- Uses frozen dataclass `==` for field-by-field comparison
- Returns `"easy"`, `"medium"`, `"hard"`, or `"custom"`

### cipherbench/__init__.py updates

Added seven puzzle public names to imports and `__all__`:
- `Puzzle`, `generate_puzzle`, `verify_puzzle`, `get_tier`, `EASY`, `MEDIUM`, `HARD`

### tests/unit/test_puzzle/test_puzzle.py

13 tests covering all requirements:

| Test | Requirement |
|------|-------------|
| `test_generate_puzzle_reproducible` | GEN-01 |
| `test_same_seed_same_puzzle` | GEN-01 |
| `test_verify_puzzle_passes` | GEN-02 |
| `test_verify_puzzle_detects_mutation` | GEN-02 |
| `test_tier_constants_distinct` | GEN-03 |
| `test_get_tier` | GEN-03 / D-12 |
| `test_get_tier_custom` | D-12 |
| `test_difficulty_tiers_distinct_complexity` | GEN-03 |
| `test_create_engine_returns_rule_engine` | D-05 |
| `test_create_engine_fresh_each_call` | D-04 / D-05 |
| `test_puzzle_is_frozen` | D-09 |
| `test_public_import_path` | D-06 |
| `test_verify_puzzle_always_passes_for_fresh_puzzle` | GEN-02 (Hypothesis) |

## Test Results

```
75 passed in 0.21s

tests/test_properties.py               5 passed
tests/unit/test_engine/test_layers.py  22 passed
tests/unit/test_engine/test_rule_engine.py  9 passed
tests/unit/test_engine/test_seeding.py  6 passed
tests/unit/test_engine/test_types.py   20 passed
tests/unit/test_puzzle/test_puzzle.py  13 passed
```

## Phase 2 Success Criteria Verification

**SC-1 (GEN-01): Same seed → same puzzle across process restarts:**
```
generate_puzzle(42).puzzle_hash == '1a7a949f36bd988777842516d97d9896f33fe76f28e749730802017e7ec20837'
Same result on second call: True
```

**SC-2 (GEN-02): Mutated seed produces hash mismatch:**
```
PASS: hash mismatch: expected b042da001288fb5f8e42805ccf2ec226aa70bda455e9fe042de317e9dfc826e5,
      got 1a7a949f36bd988777842516d97d9896f33fe76f28e749730802017e7ec20837
```

**SC-3 (GEN-03): EASY/MEDIUM/HARD produce distinct complexity:**
```
disjoint: True (hash sets from 20 seeds are pairwise disjoint)
```

**GEN-04 regression (no global random.seed in puzzle.py):**
```
Only occurrence is in a docstring comment — no actual random.seed() call in code
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. No placeholder data or TODO markers in the implemented code.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. All changes are pure Python in-memory operations. Threat model items verified:
- T-02-03-B (Tampering — crafted Puzzle bypassing verify_puzzle): mitigated — `test_verify_puzzle_detects_mutation` passes; verify_puzzle re-derives hash from seed+difficulty every call
- T-02-03-C (Information Disclosure — error message exposing hash): accepted — only 64-char hex strings in error, no cipher key or base_shifts values
- T-02-SC (Tampering — package installs): accepted — stdlib only (hashlib, json, dataclasses)

## Self-Check: PASSED

- cipherbench/puzzle.py: FOUND
- cipherbench/__init__.py updated with puzzle imports: FOUND
- tests/unit/test_puzzle/__init__.py: FOUND
- tests/unit/test_puzzle/test_puzzle.py: FOUND
- Commit 75a5ae7: FOUND
- Commit faf67da: FOUND
- 75 tests passing: CONFIRMED
