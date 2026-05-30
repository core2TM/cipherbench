---
phase: 01-rule-engine
plan: "01"
subsystem: core/types
tags: [scaffold, data-contracts, tdd, frozen-dataclasses, pyproject]
dependency_graph:
  requires: []
  provides:
    - cipherbench package installable
    - AttemptScore frozen dataclass (score, max_score, is_correct)
    - DifficultyConfig frozen dataclass (alphabet, output_length)
    - pytest test infrastructure
  affects:
    - All subsequent plans — these types are the stable import surface
tech_stack:
  added:
    - pyproject.toml with hatchling build backend
    - pytest 8.4.2 (dev dep)
    - hypothesis 6.114.1 (dev dep)
    - pytest-asyncio 0.23.8 (dev dep)
  patterns:
    - frozen dataclass with __post_init__ validation
    - TDD RED/GREEN commit sequence
key_files:
  created:
    - pyproject.toml
    - cipherbench/__init__.py
    - cipherbench/types.py
    - cipherbench/engine/__init__.py
    - tests/__init__.py
    - tests/unit/__init__.py
    - tests/unit/test_engine/__init__.py
    - tests/unit/test_engine/test_types.py
    - tests/conftest.py
  modified: []
decisions:
  - "Used pip fallback (uv not available on system PATH); documented in SUMMARY"
  - "Downgraded pytest-asyncio to 0.23.8 (1.4.0 requires Python 3.10+)"
  - "Downgraded hypothesis to 6.114.1 (6.154.1 uses Python 3.10+ union syntax)"
  - "Used single-underscore private convention for types.py (double-underscore in Plan 03)"
  - "conftest.py engine fixtures use pytest.skip (not NotImplementedError) for clean skips"
metrics:
  duration_minutes: 3
  completed_date: "2026-05-28"
  tasks_completed: 2
  files_changed: 9
---

# Phase 01 Plan 01: Project Scaffold and Data Contracts Summary

**One-liner:** Stdlib-only frozen dataclasses AttemptScore/DifficultyConfig with __post_init__ invariant enforcement, installed as editable package under pytest 8.4.2 test infrastructure.

## What Was Built

### Task 1: Project scaffold
Created the installable package skeleton: `pyproject.toml` with hatchling build backend, pytest configuration, and dev dependency declarations. Created `cipherbench/` package directory with `engine/` sub-package. Created `tests/` hierarchy with empty `__init__.py` files throughout.

The package is installable via `pip install -e ".[dev]"` and `python3 -c "import cipherbench"` exits 0. pytest discovers and runs with no collection errors.

### Task 2: Data contracts — AttemptScore and DifficultyConfig

`cipherbench/types.py` defines both frozen dataclasses with validated invariants:
- `AttemptScore`: enforces `0 <= score <= max_score` and `is_correct == (score == max_score)`. Fields: `score: int`, `max_score: int`, `is_correct: bool`. No `ciphertext`, `key`, or `shifts` fields (RULE-04 boundary enforced at type level).
- `DifficultyConfig`: enforces `len(alphabet) >= 2` and `output_length >= 1`. Defaults: `alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"`, `output_length=5`.

`cipherbench/__init__.py` re-exports both types with `__all__`. `tests/conftest.py` provides `default_difficulty` fixture and stubbed `rule_engine_seed_42` / `rule_engine_seed_0` fixtures that call `pytest.skip()` until Plan 03 implements `RuleEngine`.

All 11 TDD tests pass (0 failures).

## Verification Results

```
python -m pytest tests/unit/test_engine/test_types.py -v --tb=short
11 passed in 0.05s

python -c "from cipherbench import AttemptScore, DifficultyConfig; print('ok')"
ok

grep -r "random\.seed(" cipherbench/
(no output — 0 matches)
```

## TDD Gate Compliance

- RED gate commit: `fc45695` — `test(01-01): add failing tests for AttemptScore and DifficultyConfig invariants`
- GREEN gate commit: `9059a90` — `feat(01-01): implement AttemptScore and DifficultyConfig frozen dataclasses`
- REFACTOR: not needed (code is clean as written)

## Deviations from Plan

### Environment Deviations (not bugs — system compatibility)

**1. [Rule 3 - Blocking] Python 3.9.6 system Python requires compatible dependency versions**

- **Found during:** Task 1 dependency install
- **Issue:** System Python is 3.9.6; pyproject.toml targets >=3.11. Several dev dependencies installed at latest versions use Python 3.10+ syntax (union type `X | Y`, `TypeAlias`, `ParamSpec`).
- **Fix:** Pinned pytest to `<9.0` (8.4.2), iniconfig to `<2.0` (1.1.1), hypothesis to `<6.115` (6.114.1), pytest-asyncio to `<0.24` (0.23.8) — all within the >=constraints specified in pyproject.toml.
- **Files modified:** none (runtime pip install; pyproject.toml constraints remain correct)
- **Commits:** Task 1 commit `45633c1`

**Note:** pyproject.toml correctly declares `requires-python = ">=3.11"`. The system Python 3.9.6 is a developer environment limitation, not a package requirement issue. The install used `--ignore-requires-python` flag to proceed. Future developers should install Python 3.11+ via pyuenv or uv before installing.

**2. uv not available on PATH** — pip fallback used as documented in RESEARCH.md. No functional impact.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `rule_engine_seed_42` / `rule_engine_seed_0` fixtures call `pytest.skip()` | tests/conftest.py | 22, 31 | RuleEngine not implemented until Plan 03; fixtures will be updated then |
| Forward-reference comment for RuleEngine/create_rule_engine | cipherbench/__init__.py | 12-13 | Imports added in Plan 03 when engine/rule_engine.py exists |

These stubs are intentional and expected per plan. They do not prevent Plan 01's goal (data contracts) from being achieved.

## Threat Surface Scan

No new security-relevant surface introduced beyond what the plan's threat model covers:
- T-01-01 (Information Disclosure): AttemptScore locked to score/max_score/is_correct — verified by test_attempt_score_no_ciphertext_field
- T-01-02 (Tampering): frozen=True on both dataclasses — verified by test_dataclasses_are_frozen_*
- T-01-03 (Information Disclosure): `__all__` explicitly declared in `__init__.py`
- T-01-04 (DoS): __post_init__ validates both types — prevents degenerate configs

No new threat flags.

## Self-Check: PASSED

Files created/exist:
- FOUND: pyproject.toml
- FOUND: cipherbench/__init__.py
- FOUND: cipherbench/types.py
- FOUND: cipherbench/engine/__init__.py
- FOUND: tests/__init__.py
- FOUND: tests/unit/__init__.py
- FOUND: tests/unit/test_engine/__init__.py
- FOUND: tests/unit/test_engine/test_types.py
- FOUND: tests/conftest.py

Commits exist:
- FOUND: 45633c1 (scaffold)
- FOUND: fc45695 (TDD RED)
- FOUND: 9059a90 (TDD GREEN)
