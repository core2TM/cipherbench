---
phase: 02-puzzle-generator
fixed_at: 2026-05-28T19:48:02Z
review_path: .planning/phases/02-puzzle-generator/02-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-05-28T19:48:02Z
**Source review:** .planning/phases/02-puzzle-generator/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: DifficultyConfig(output_length=1) validates as "valid" but no derived object can ever be constructed

**Files modified:** `cipherbench/types.py`
**Commit:** c898c3c
**Applied fix:** Changed the `output_length` validator floor from `< 1` to `< 2` with an updated error message: `"output_length must be at least 2 (output_length=1 leaves no valid cross_char_depth)"`. This surfaces the true effective minimum at validation time rather than detonating with a confusing `cross_char_depth` error on the next check.

### WR-01: generate_puzzle and verify_puzzle access private RuleEngine attributes, violating encapsulation

**Files modified:** `cipherbench/engine/rule_engine.py`, `cipherbench/puzzle.py`
**Commit:** d338eb2
**Applied fix:** Added `_hash_payload()` method to `RuleEngine` that returns `{"base_shifts": ..., "k_list": ..., "ground_truth": ...}`. Updated `generate_puzzle` and `verify_puzzle` in `puzzle.py` to call `engine._hash_payload()` and unpack the dict, so neither function names `_base_shifts`, `_k_list`, or `_ground_truth` directly. The private-attribute coupling is now localised inside `RuleEngine` itself.

### WR-02: apply_state_layer and count_correct silently truncate on length-mismatched inputs

**Files modified:** `cipherbench/engine/layers.py`
**Commit:** 71c9516
**Applied fix:** Added explicit `ValueError` guards at the top of both function bodies. `apply_state_layer` raises when `len(plaintext) != len(base_shifts)`; `count_correct` raises when `len(guess) != len(ciphertext)`. Both messages include the observed lengths for easy diagnosis.

### WR-03: difficulty: DifficultyConfig = None is an incorrect type annotation on two factory functions

**Files modified:** `cipherbench/engine/rule_engine.py`, `cipherbench/puzzle.py`
**Commit:** 9b0f51a
**Applied fix:** Added `from typing import Optional` to both files. Updated `create_rule_engine` signature to `difficulty: Optional[DifficultyConfig] = None` and `generate_puzzle` signature to `difficulty: Optional[DifficultyConfig] = None`. Both files already had `from __future__ import annotations` so no other changes were needed.

### WR-04: apply_cross_char_layer is imported but never called in rule_engine.py

**Files modified:** `cipherbench/engine/rule_engine.py`
**Commit:** d41042f
**Applied fix:** Removed `apply_cross_char_layer` from the import block in `rule_engine.py`. Only `apply_state_layer`, `apply_cross_char_layer_multi`, and `count_correct` are actually called in the module.

---

_Fixed: 2026-05-28T19:48:02Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
