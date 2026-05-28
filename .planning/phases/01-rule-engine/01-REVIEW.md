---
phase: 01-rule-engine
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - cipherbench/__init__.py
  - cipherbench/engine/__init__.py
  - cipherbench/engine/layers.py
  - cipherbench/engine/rule_engine.py
  - cipherbench/types.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/test_properties.py
  - tests/unit/__init__.py
  - tests/unit/test_engine/__init__.py
  - tests/unit/test_engine/test_layers.py
  - tests/unit/test_engine/test_rule_engine.py
  - tests/unit/test_engine/test_seeding.py
  - tests/unit/test_engine/test_types.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-28T00:00:00Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the core rule engine implementation: two source modules (`layers.py`, `rule_engine.py`), the shared data contract (`types.py`), the public API surface (`__init__.py`), and the full test suite. The functional cipher logic is correct and the information boundary design (private state, aggregate-only score, no ciphertext leakage) is sound. Two blockers were found: the factory crashes with an obscure standard-library error when given a valid `DifficultyConfig(output_length=1)`, and the 5-attempt-per-puzzle limit stated as a core mechanic in the spec is completely unenforced — a model can call `score_attempt` indefinitely. Four warnings cover input validation gaps, a type-annotation contract violation, and a missing alphabet uniqueness check that silently corrupts encoding. Three info items cover test fragility and annotation incompleteness.

## Critical Issues

### CR-01: `create_rule_engine` crashes with opaque `ValueError` for `output_length=1`

**File:** `cipherbench/engine/rule_engine.py:193`
**Issue:** `DifficultyConfig.__post_init__` permits `output_length=1` (the guard is `< 1`), so `DifficultyConfig(alphabet="AB", output_length=1)` is a valid object. When passed to `create_rule_engine`, line 193 executes `rng.randint(1, n - 1)` which becomes `rng.randint(1, 0)` — an empty range that raises `ValueError: empty range for randrange() (1, 1, 0)`. The error originates deep inside `random.py` with no message connecting it to the puzzle configuration, making it extremely hard to diagnose. The fix can be applied in either (or both) layers.

**Fix — option A: tighten `DifficultyConfig` validation (preferred, single point of truth):**
```python
# cipherbench/types.py  __post_init__
if self.output_length < 2:
    raise ValueError("output_length must be at least 2")
```

**Fix — option B: guard in the factory:**
```python
# cipherbench/engine/rule_engine.py  create_rule_engine, before line 193
if n < 2:
    raise ValueError(
        f"output_length must be at least 2 to support cross-character mixing "
        f"(got {n})"
    )
```

---

### CR-02: 5-attempt limit is a documented core mechanic but is not enforced

**File:** `cipherbench/engine/rule_engine.py:69-121`
**Issue:** `CLAUDE.md` states: *"Attempt limit: Fixed at 5 probe attempts per puzzle (a core mechanic, not configurable in v1)."* The `RuleEngine.score_attempt` docstring says the engine is *"ready for up to 5 score_attempt calls"*, and `create_rule_engine`'s docstring repeats *"ready for up to 5 score_attempt calls."* Despite this, `score_attempt` has no guard on `self._round`. A caller can invoke it on round 6, 7, or 100 and receive a score — the round-number multiplier continues growing (`effective_shift = base_shift * round_num`), producing results that are defined by the formula but outside the designed puzzle contract. This breaks the benchmark's fairness guarantee: a model that is given unlimited attempts has a fundamentally different — and easier — task than a model limited to 5.

**Fix:**
```python
# cipherbench/engine/rule_engine.py — add a constant and guard in score_attempt

MAX_ATTEMPTS = 5  # module-level constant

class RuleEngine:
    ...
    def score_attempt(self, guess: str) -> AttemptScore:
        if self._round > MAX_ATTEMPTS:
            raise RuntimeError(
                f"Attempt limit exceeded: this puzzle allows at most "
                f"{MAX_ATTEMPTS} attempts."
            )
        # existing validation follows ...
```

## Warnings

### WR-01: `DifficultyConfig` does not reject duplicate characters in `alphabet`

**File:** `cipherbench/types.py:32-36`
**Issue:** `__post_init__` only checks `len(alphabet) < 2`, so `DifficultyConfig(alphabet="AABCDE")` is accepted. Downstream, `alphabet.index(c)` always returns the *first* occurrence of a character, which means two distinct alphabet positions both decode to the same character. The encoding is no longer a bijection: a guess character `"A"` always maps to index `0`, even though index `1` also encodes to `"A"`. This silently corrupts per-position correctness counts and makes the cipher unsolvable for any alphabet containing repeated characters.

**Fix:**
```python
# cipherbench/types.py  __post_init__
if len(set(self.alphabet)) != len(self.alphabet):
    raise ValueError("alphabet must not contain duplicate characters")
```

---

### WR-02: `count_correct` silently truncates on length-mismatched inputs

**File:** `cipherbench/engine/layers.py:128`
**Issue:** `count_correct` uses `zip(guess, ciphertext)` with no length guard. If the two strings differ in length, `zip` silently stops at the shorter one, returning a count that is less than `len(guess)` for reasons unrelated to correctness. In the current code path this cannot be triggered through the public API (because `score_attempt` validates `len(guess) == len(ground_truth)` and `_encode_for_round` always returns `len(ground_truth)` characters). However, `count_correct` is a public-facing layer function importable by external code, and the silent truncation violates the principle of failing loudly. A callers who passes strings of unequal length receives a plausibly valid integer with no indication of the bug.

**Fix:**
```python
def count_correct(guess: str, ciphertext: str) -> int:
    if len(guess) != len(ciphertext):
        raise ValueError(
            f"guess and ciphertext must have equal length "
            f"(got {len(guess)} and {len(ciphertext)})"
        )
    return sum(g == c for g, c in zip(guess, ciphertext))
```

---

### WR-03: Incorrect type annotation for `difficulty` parameter in `create_rule_engine`

**File:** `cipherbench/engine/rule_engine.py:153`
**Issue:** The signature is:
```python
def create_rule_engine(seed: int, difficulty: DifficultyConfig = None) -> RuleEngine:
```
The annotation `difficulty: DifficultyConfig` is incorrect when the default value is `None`. A static type checker (mypy, pyright) will flag this as a type error because `None` is not assignable to `DifficultyConfig`. The correct annotation is `Optional[DifficultyConfig]` or, using the PEP 604 union syntax available with `from __future__ import annotations`, `DifficultyConfig | None`.

**Fix:**
```python
# Option 1 — explicit Optional (works without __future__)
from typing import Optional

def create_rule_engine(seed: int, difficulty: Optional[DifficultyConfig] = None) -> RuleEngine:

# Option 2 — union syntax (already safe here because __future__ annotations is imported)
def create_rule_engine(seed: int, difficulty: DifficultyConfig | None = None) -> RuleEngine:
```

---

### WR-04: `apply_state_layer` silently truncates when `base_shifts` and `plaintext` differ in length

**File:** `cipherbench/engine/layers.py:50-52`
**Issue:** `apply_state_layer` computes `zip(indices, effective_shifts)` where `indices` has length `len(plaintext)` and `effective_shifts` has length `len(base_shifts)`. If these differ, `zip` silently truncates to the shorter length, returning fewer indices than expected. The returned list is then passed to `apply_cross_char_layer` which uses `n = len(shifted_indices)` as the loop bound — so the final encoded string is also silently shorter than expected. This mismatch is not caught by `count_correct` (which also uses `zip`), meaning a mismatched-length construction returns a fabricated score rather than an error. The factory always constructs consistent lengths, but `RuleEngine.__init__` accepts any `base_shifts` list without validating that `len(base_shifts) == len(ground_truth)`, leaving this latent path open to anyone who constructs `RuleEngine` directly.

**Fix — add a guard to `apply_state_layer`:**
```python
def apply_state_layer(
    plaintext: str,
    base_shifts: list[int],
    round_num: int,
    alphabet: str,
) -> list[int]:
    if len(plaintext) != len(base_shifts):
        raise ValueError(
            f"plaintext length ({len(plaintext)}) must equal "
            f"base_shifts length ({len(base_shifts)})"
        )
    ...
```

## Info

### IN-01: Magic number `5` hardcoded in property-based tests instead of `result.max_score`

**File:** `tests/test_properties.py:40-42`
**Issue:** `test_score_attempt_never_reveals_private_state` asserts:
```python
assert 0 <= result.score <= 5
assert result.is_correct == (result.score == 5)
```
Both lines hardcode `5` rather than `result.max_score`. The assertions happen to be correct because `DifficultyConfig()` defaults to `output_length=5`, but they would silently pass or give misleading failures if the test were ever run against a non-default difficulty. Using `result.max_score` makes the assertions self-contained and robust to configuration changes.

**Fix:**
```python
assert 0 <= result.score <= result.max_score
assert result.is_correct == (result.score == result.max_score)
```

---

### IN-02: Unparameterized `list` type annotations in `layers.py`

**File:** `cipherbench/engine/layers.py:25, 55`
**Issue:** Both `apply_state_layer` and `apply_cross_char_layer` use bare `list` in their parameter and return type annotations rather than the more informative `list[int]`. Since `from __future__ import annotations` is imported at the top of the file, `list[int]` is a zero-cost string annotation at runtime and carries no compatibility cost. The docstrings already describe the types accurately (e.g., `list[int]`), so updating the signatures closes the gap between documentation and code.

**Fix:**
```python
def apply_state_layer(
    plaintext: str,
    base_shifts: list[int],
    round_num: int,
    alphabet: str,
) -> list[int]:

def apply_cross_char_layer(
    shifted_indices: list[int],
    plaintext: str,
    k: int,
    alphabet: str,
) -> str:
```

---

### IN-03: Misleading docstring claim that `score_attempt` error messages are "generic"

**File:** `cipherbench/engine/rule_engine.py:75`
**Issue:** The docstring says *"ValueError is raised with a generic message — no cipher state is included in the error (T-03-02 mitigation)"*, but the actual error message for a wrong-length guess is:
```
guess length 3 does not match output_length 5
```
This includes `output_length` (the value `5`), which is not secret cipher state, but the message is not "generic". The docstring overstates the security property. The second error message (`"guess contains characters outside the configured alphabet"`) is genuinely generic. The docstring should be corrected to accurately describe what is and is not revealed, so developers do not mistake this for a stronger guarantee than it provides.

**Fix:** Update the docstring to read something like: *"ValueError is raised without revealing cipher keys, ciphertext, or shift values — output_length is included in the length-mismatch message since it is not secret."*

---

_Reviewed: 2026-05-28T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
