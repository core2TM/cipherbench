---
phase: 01-rule-engine
plan: "02"
subsystem: core/engine
tags: [pure-functions, tdd, cipher-layers, state-layer, cross-char, count-correct]
dependency_graph:
  requires:
    - 01-01 (cipherbench package, types.py, test infrastructure)
  provides:
    - apply_state_layer pure function (RULE-01)
    - apply_cross_char_layer pure function (RULE-02, pull model)
    - count_correct pure function (RULE-03, aggregate only)
    - 15 canonical regression tests for all three layer functions
  affects:
    - 01-03 (RuleEngine will import and call all three functions)
tech_stack:
  added: []
  patterns:
    - Functional core: pure module-level functions with no state, no randomness
    - TDD RED/GREEN commit sequence
    - Alphabet as explicit parameter — never hardcoded in function bodies (D-05)
    - Linear round multiplier via list comprehension (D-07)
    - Pull model cross-char: source_pos = (j - k) % n (D-04)
key_files:
  created:
    - cipherbench/engine/layers.py
    - tests/unit/test_engine/test_layers.py
  modified: []
decisions:
  - "Pull model direction locked by test_cross_char_pull_model_direction (expects 'CAB' for shifted=[0,0,0], plaintext='ABC', k=1)"
  - "list[int] return type for apply_state_layer — passes indices directly to apply_cross_char_layer without second lookup"
  - "count_correct uses zip (not enumerate) — shorter, clearer, stops at shortest string naturally"
  - "from __future__ import annotations used for forward-compat type hints on Python 3.9"
metrics:
  duration_minutes: 2
  completed_date: "2026-05-28"
  tasks_completed: 1
  files_changed: 2
---

# Phase 01 Plan 02: Pure Cipher Layer Functions Summary

**One-liner:** Three pure cipher functions — linear-round-multiplier state layer (D-07), pull-model cross-char mixing (D-04), and aggregate-only score (D-01) — with 16 canonical regression tests locking the pull model direction.

## What Was Built

### Task 1: Pure layer functions — apply_state_layer, apply_cross_char_layer, count_correct

`cipherbench/engine/layers.py` defines three module-level pure functions with no class, no state, no randomness:

**apply_state_layer(plaintext, base_shifts, round_num, alphabet) -> list[int]**

Implements RULE-01 and D-07. Linear multiplier: `effective_shifts = [s * round_num for s in base_shifts]`. Converts plaintext characters to indices via `alphabet.index(c)` then applies modular arithmetic `(idx + eff) % len(alphabet)`. Returns a list of integer indices — not a string — so the cross-char layer can consume them directly without a second lookup.

Canonical regressions confirmed:
- `apply_state_layer("AAA", [1,2,3], 1, ALPHABET) == [1, 2, 3]` (A=0, shifts×1=[1,2,3])
- `apply_state_layer("BBB", [1,2,3], 2, ALPHABET) == [3, 5, 7]` (B=1, shifts×2=[2,4,6], 1+2=3, 1+4=5, 1+6=7)

**apply_cross_char_layer(shifted_indices, plaintext, k, alphabet) -> str**

Implements RULE-02 and D-04 using the pull model. For each output position `j`:
- `source_pos = (j - k) % n`
- `extra_offset = alphabet.index(plaintext[source_pos])`
- `new_idx = (shifted_indices[j] + extra_offset) % len(alphabet)`

Pull model direction locked by test: `apply_cross_char_layer([0,0,0], "ABC", k=1, ALPHABET) == "CAB"`. Returns a joined string of alphabet characters.

**count_correct(guess, ciphertext) -> int**

Implements RULE-03 and D-01. One-liner: `sum(g == c for g, c in zip(guess, ciphertext))`. Aggregate-only — no per-position breakdown ever returned.

`tests/unit/test_engine/test_layers.py` covers all three functions with 16 tests (plan specified 15; pytest collected 16 — the test file contains 16 functions including all 15 specified). All pass.

## Verification Results

```
python3 -m pytest tests/unit/test_engine/test_layers.py -v --tb=short
16 passed in 0.08s

python3 -m pytest tests/ -q
27 passed in 0.08s   (16 new + 11 from Plan 01 — no regressions)

grep -n "^import random|^from random|random\." cipherbench/engine/layers.py
(no output — 0 matches)

grep -n '"ABCDEFGHIJKLMNOPQRSTUVWXYZ"' cipherbench/engine/layers.py
(no output — 0 matches, alphabet is always a parameter)
```

## TDD Gate Compliance

- RED gate commit: `81c34ab` — `test(01-02): add failing tests for apply_state_layer, apply_cross_char_layer, count_correct`
- GREEN gate commit: `0271d55` — `feat(01-02): implement apply_state_layer, apply_cross_char_layer, count_correct`
- REFACTOR: not needed (implementation is clean as written; functions match PATTERNS.md spec exactly)

## Deviations from Plan

None — plan executed exactly as written.

The plan specified 15 tests; the test file contains 16 because `test_cross_char_k0_vs_k1_differs` and the individual count_correct tests total 16 when counted precisely from the behavior block. The extra test is `test_count_correct_returns_int` which was listed in the behavior block and counted in the plan target as well. Pytest collected 16 — this is expected, not a deviation. All specified behavior is covered.

## Known Stubs

None — all three functions are fully implemented with no hardcoded values, placeholders, or TODO markers. The functions are ready to be imported by Plan 03 (RuleEngine).

## Threat Surface Scan

No new security-relevant surface beyond the plan's threat model:
- T-02-01 (Information Disclosure): apply_state_layer returns list[int] indices — not a human-readable ciphertext. RuleEngine (Plan 03) is the only caller and will keep this value private per D-09.
- T-02-02 (Information Disclosure): apply_cross_char_layer output will only be called from RuleEngine._encode_for_round() (private) — result compared internally and discarded, never returned to caller.
- T-02-03 (Tampering): No hardcoded alphabet string confirmed by grep. Alphabet comes from parameter only.
- T-02-04 (Information Disclosure — accept): Linear multiplier periodicity at round=26 is a documented known property; 5-attempt limit makes it unreachable. Accepted risk per plan threat model.

No new threat flags.

## Self-Check: PASSED

Files created/exist:
- FOUND: /Users/atipat/Desktop/superfinal/cipherbench/engine/layers.py
- FOUND: /Users/atipat/Desktop/superfinal/tests/unit/test_engine/test_layers.py

Commits exist:
- FOUND: 81c34ab (TDD RED — failing tests)
- FOUND: 0271d55 (TDD GREEN — implementation passing)
