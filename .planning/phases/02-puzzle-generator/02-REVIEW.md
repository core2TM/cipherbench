---
phase: 02-puzzle-generator
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - cipherbench/types.py
  - cipherbench/engine/layers.py
  - cipherbench/engine/rule_engine.py
  - cipherbench/puzzle.py
  - cipherbench/__init__.py
  - tests/unit/test_engine/test_types.py
  - tests/unit/test_engine/test_layers.py
  - tests/unit/test_puzzle/__init__.py
  - tests/unit/test_puzzle/test_puzzle.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-29T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the puzzle-generator phase: frozen dataclasses (`types.py`), three pure cipher-layer functions (`layers.py`), the stateful `RuleEngine` and its factory (`rule_engine.py`), the `Puzzle` dataclass and tier presets (`puzzle.py`), the public API surface (`__init__.py`), and the accompanying test suite.

The core cipher mechanics are arithmetically correct and the round-counter isolation is sound. However, one correctness bug exists in `DifficultyConfig` validation that makes `output_length=1` appear valid while silently rejecting every attempt to use it. Beyond that, the most structurally significant issue is that `generate_puzzle` and `verify_puzzle` reach directly into private attributes of `RuleEngine` (`_base_shifts`, `_k_list`, `_ground_truth`), breaking the encapsulation that the codebase explicitly prizes and creating a cross-module coupling that will silently break if the attribute names ever change. Additional findings cover an unused import, silent truncation in two pure functions, and missing type annotations.

---

## Critical Issues

### CR-01: `DifficultyConfig(output_length=1)` validates as "valid" but no derived object can ever be constructed — misleading invariant

**File:** `cipherbench/types.py:46-54`

**Issue:** `__post_init__` accepts `output_length >= 1`, yet the `cross_char_depth` constraint enforces `1 <= cross_char_depth <= output_length - 1`. When `output_length == 1`, `output_length - 1 == 0`, so the constraint becomes `1 <= cross_char_depth <= 0` — impossible for any integer. Every attempt to build a `DifficultyConfig` with `output_length=1` raises `ValueError` with the confusing message "cross_char_depth must be in [1, output_length-1=0]", regardless of what `cross_char_depth` value is supplied. The caller gets no signal from the `output_length` validator itself. The effective minimum is `output_length >= 2`, but the code documents and enforces `>= 1`.

```python
# Current (misleading):
if self.output_length < 1:
    raise ValueError("output_length must be positive")

# Fix: enforce the true minimum
if self.output_length < 2:
    raise ValueError(
        "output_length must be at least 2 "
        "(output_length=1 leaves no valid cross_char_depth)"
    )
```

The docstring on the field ("Default: 5 … Fixed at 5 across all puzzles in v1") further hints this was never intended to be 1, but the validator allows it and then detonates on the next check with a confusing error.

---

## Warnings

### WR-01: `generate_puzzle` and `verify_puzzle` access private `RuleEngine` attributes, violating the encapsulation boundary the design explicitly enforces

**File:** `cipherbench/puzzle.py:106` and `cipherbench/puzzle.py:120`

**Issue:** Both functions call `engine._base_shifts`, `engine._k_list`, and `engine._ground_truth` directly. The codebase's design documentation devotes significant text to the information boundary and private-attribute convention (D-09, RULE-04). Yet `puzzle.py` is the only external consumer that systematically reads all three private attributes. This is a coupling that will break silently if `RuleEngine`'s internal attribute names are ever refactored. The design goal would be better served by a controlled extraction pathway.

```python
# Fix option A: add a dedicated factory method on RuleEngine for hash payload extraction
# In rule_engine.py RuleEngine class:
def _hash_payload(self) -> dict:
    """Return the minimal derived-state dict for puzzle integrity hashing.
    Intentionally private; only generate_puzzle / verify_puzzle may call this."""
    return {
        "base_shifts": self._base_shifts,
        "k_list": self._k_list,
        "ground_truth": self._ground_truth,
    }

# In puzzle.py:
payload = engine._hash_payload()
puzzle_hash = _compute_hash(payload["base_shifts"], payload["k_list"], payload["ground_truth"])
```

This localises the private-attribute coupling inside `RuleEngine` itself and means `puzzle.py` never needs to name `_base_shifts` directly.

### WR-02: `apply_state_layer` and `count_correct` silently truncate on length-mismatched inputs

**File:** `cipherbench/engine/layers.py:57-59` (`apply_state_layer`) and `cipherbench/engine/layers.py:192` (`count_correct`)

**Issue:** Both functions use `zip()` without asserting that the paired sequences have equal length. A caller that passes a `plaintext` longer than `base_shifts` (or vice versa) gets a shorter result list with no error. Similarly, `count_correct("ABCDE", "A")` returns `1` instead of raising. In production flow, lengths are always consistent because `create_rule_engine` derives `base_shifts` and `ground_truth` from the same `n`, so the bug is latent — but these are documented public functions, and the contract says nothing about silent truncation. A future caller (e.g. in the CLI or a custom scorer) can misuse them and receive a wrong-but-plausible answer.

```python
# apply_state_layer fix — add at start of function body:
if len(plaintext) != len(base_shifts):
    raise ValueError(
        f"plaintext length {len(plaintext)} != base_shifts length {len(base_shifts)}"
    )

# count_correct fix — add at start of function body:
if len(guess) != len(ciphertext):
    raise ValueError(
        f"guess length {len(guess)} != ciphertext length {len(ciphertext)}"
    )
```

### WR-03: `difficulty: DifficultyConfig = None` is an incorrect type annotation on two factory functions

**File:** `cipherbench/engine/rule_engine.py:174` and `cipherbench/puzzle.py:84`

**Issue:** Both `create_rule_engine` and `generate_puzzle` declare `difficulty: DifficultyConfig = None`. The type annotation says `DifficultyConfig` (never `None`), but the default value is `None`. This is a type error: `None` is not a `DifficultyConfig`. Any type-checker (mypy, pyright) will flag every call site that relies on the default. The correct annotation is `Optional[DifficultyConfig]` (or `DifficultyConfig | None` in Python 3.10+ style).

```python
# Fix in both rule_engine.py and puzzle.py:
from __future__ import annotations
from typing import Optional

def create_rule_engine(seed: int, difficulty: Optional[DifficultyConfig] = None) -> RuleEngine:
    ...

def generate_puzzle(seed: int, difficulty: Optional[DifficultyConfig] = None) -> Puzzle:
    ...
```

Note: both files already have `from __future__ import annotations`, so `from typing import Optional` is the only addition needed (or use `DifficultyConfig | None` syntax).

### WR-04: `apply_cross_char_layer` is imported but never called in `rule_engine.py`

**File:** `cipherbench/engine/rule_engine.py:46`

**Issue:** The import statement on line 46 imports `apply_cross_char_layer` (single-k version). The only function actually called inside the module is `apply_cross_char_layer_multi`. The dead import adds noise, misleads readers into thinking single-k encoding has a role in the engine, and will produce a lint/flake8 warning.

```python
# Current:
from cipherbench.engine.layers import (
    apply_state_layer,
    apply_cross_char_layer,        # unused
    apply_cross_char_layer_multi,
    count_correct,
)

# Fix: remove the unused import
from cipherbench.engine.layers import (
    apply_state_layer,
    apply_cross_char_layer_multi,
    count_correct,
)
```

---

## Info

### IN-01: `Puzzle.__post_init__` does not validate `puzzle_hash` format

**File:** `cipherbench/puzzle.py:55-59`

**Issue:** The only `puzzle_hash` check is `if not self.puzzle_hash` (truthy test for non-empty string). A caller can supply any non-empty string — `"not-a-hex-digest"`, `"x" * 64` — and the `Puzzle` is accepted without complaint. `verify_puzzle` would later catch the inconsistency, but only if called. Since the docstring specifies this must be "SHA-256 hex digest", a format check would make the data contract self-enforcing.

```python
import re
_HEX64 = re.compile(r'^[0-9a-f]{64}$')

def __post_init__(self) -> None:
    if not isinstance(self.seed, int):
        raise ValueError("seed must be an integer")
    if not _HEX64.match(self.puzzle_hash or ""):
        raise ValueError("puzzle_hash must be a 64-character lowercase hex string")
```

### IN-02: `test_difficulty_config_zero_length_rejected` docstring claims the minimum is 1 but the true enforced minimum is 2

**File:** `tests/unit/test_engine/test_types.py:57-59`

**Issue:** The test docstring says "output_length must be >= 1", which matches the current validator message. But as CR-01 establishes, the functional minimum is 2. Once CR-01 is fixed the validator will reject `output_length=1` directly, but this test only asserts that `output_length=0` raises — it does not catch the off-by-one in the validator floor. A companion test for `output_length=1` is missing.

```python
def test_difficulty_config_one_length_rejected():
    """output_length=1 must raise ValueError (minimum usable length is 2)."""
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="AB", output_length=1)
```

### IN-03: `test_puzzle.py` comment references "D-09: no leaking of engine private state through Puzzle" but contains no test for that property

**File:** `tests/unit/test_puzzle/test_puzzle.py:10`

**Issue:** The module docstring lists "D-09: Puzzle is frozen; no leaking of engine private state through Puzzle" as a covered requirement. The test suite has a frozen-field mutation test (`test_puzzle_is_frozen`) but has no assertion that `Puzzle` does not expose `base_shifts`, `k_list`, or `ground_truth` as fields or properties. Since `Puzzle.puzzle_hash` is a SHA-256 digest (non-invertible) this is not a correctness risk today, but the stated coverage claim is inaccurate.

```python
def test_puzzle_does_not_expose_engine_private_state():
    """D-09: Puzzle must not have base_shifts, k_list, or ground_truth attributes."""
    puzzle = generate_puzzle(seed=42)
    assert not hasattr(puzzle, "base_shifts")
    assert not hasattr(puzzle, "k_list")
    assert not hasattr(puzzle, "ground_truth")
```

---

_Reviewed: 2026-05-29T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
