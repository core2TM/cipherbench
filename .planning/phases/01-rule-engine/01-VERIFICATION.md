---
phase: 01-rule-engine
verified: 2026-05-28T00:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run `python3 -m pytest tests/ -v` and confirm all 47 tests are green. Then run the four spot-check commands from 01-03-PLAN.md verification block: (a) [m for m in dir(engine) if not m.startswith('_')] == ['score_attempt'], (b) score_attempt('ABCDE') returns AttemptScore with 0 <= score <= 5, (c) two engines from seed=42 return equal AttemptScore for same probe at round 1, (d) grep for random.seed( in cipherbench/ returns zero output."
    expected: "All 47 tests pass. (a) prints ['score_attempt']. (b) prints e.g. '0 5 False'. (c) prints True. (d) produces no output."
    why_human: "The 01-03-PLAN.md end-of-phase verification block contains an explicit <human-check> that requires a human to run the four spot checks and type 'approved' to close Phase 1. Automated checks have already confirmed all four programmatically; this harvested item requires the human sign-off requested in the plan."
---

# Phase 1: Rule Engine Verification Report

**Phase Goal:** The three-layer cipher rule engine exists with a locked-down information boundary — all downstream code is forced to interact through `score_attempt()` only
**Verified:** 2026-05-28
**Status:** human_needed (all automated checks pass; one harvested human-check item from 01-03-PLAN.md remains open)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Submitting the same probe string in two different rounds of the same session produces two different encoded outputs (state layer is active) | VERIFIED | `test_state_layer_changes_target_across_rounds` passes: `engine._encode_for_round(1) != engine._encode_for_round(2)` for seed=42. `apply_state_layer` applies linear multiplier `base_shift * round_num` — mathematically guaranteed to diverge for non-zero shifts. 50-run determinism test confirms sequence stability. |
| 2 | Changing one input character while holding all others fixed causes a change in a non-corresponding output position (cross-character interdependence is active) | VERIFIED | `test_cross_char_pull_model_direction` pins exact output "CAB" for `apply_cross_char_layer([0,0,0], "ABC", k=1)`. `test_cross_char_k0_vs_k1_differs` confirms k=0 != k=1 for non-uniform input. `test_cross_char_single_char_change_affects_multiple_positions` explicitly changes position 0 and observes change at position 1. Formula verified: `source_pos = (j-k) % n`. |
| 3 | `score_attempt(guess)` returns only a correctness count — cipher key and ground-truth ciphertext cannot be retrieved from any public interface | VERIFIED | `[m for m in dir(e) if not m.startswith('_')] == ['score_attempt']` confirmed by running engine. `test_no_public_key_accessor`, `test_score_attempt_returns_count_only`, `test_cipher_key_not_accessible` all pass. Hypothesis `test_score_attempt_never_reveals_private_state` runs 100 examples with no violation. Ciphertext is a local variable in `score_attempt` — never stored, never returned. |
| 4 | All generation sub-functions accept an explicit `rng` parameter; `grep -rn "random.seed(" cipherbench/` returns zero matches | VERIFIED | `grep -rn "random.seed(" cipherbench/` returns zero output. `test_no_global_random_seed_in_rule_engine_module` and `test_no_global_random_seed_in_layers_module` pass via source inspection. `test_rng_does_not_pollute_global_random` confirms `random.getstate()` unchanged after `create_rule_engine`. `random.Random(seed)` isolated instance used throughout factory. |

**Score: 4/4 truths verified**

---

### Deferred Items

None. All Phase 1 roadmap success criteria are satisfied. SESS-04 (50-run determinism) is mapped to Phase 3 in REQUIREMENTS.md traceability; Phase 1 verifies the same property as a precursor test (`test_fifty_sequential_runs_are_deterministic` passes) but the formal SESS-04 requirement is not gated here.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Package definition, build config, pytest config, dev deps; contains "hatchling" | VERIFIED | Present. `[project]`, `[project.optional-dependencies]`, `[build-system]` with `hatchling>=1.21`, `[tool.hatch.build.targets.wheel]`, `[tool.pytest.ini_options]` all present. No `[project.scripts]`. |
| `cipherbench/types.py` | AttemptScore, DifficultyConfig frozen dataclasses | VERIFIED | Both frozen dataclasses present with `__post_init__` invariant checks. No `ciphertext`, `key`, `shifts` fields. |
| `cipherbench/__init__.py` | Public API re-export surface | VERIFIED | Imports from `cipherbench.types` and `cipherbench.engine.rule_engine`. `__all__ = ["AttemptScore", "DifficultyConfig", "RuleEngine", "create_rule_engine"]`. |
| `tests/conftest.py` | Shared pytest fixtures: default_difficulty, rule_engine_seed_42, rule_engine_seed_0 | VERIFIED | All three fixtures present and active. `rule_engine_seed_42` and `rule_engine_seed_0` call `create_rule_engine` — no longer stubs. |
| `tests/unit/test_engine/test_types.py` | AttemptScore and DifficultyConfig invariant tests | VERIFIED | 11 tests present and passing. |
| `cipherbench/engine/layers.py` | Three pure cipher layer functions | VERIFIED | `apply_state_layer`, `apply_cross_char_layer`, `count_correct` all present. No `import random`. No hardcoded `"ABCDEFGHIJKLMNOPQRSTUVWXYZ"` in function bodies. |
| `tests/unit/test_engine/test_layers.py` | Unit test coverage for all three layer functions | VERIFIED | 16 tests present (plan said 15; 16 collected — expected per 01-02-SUMMARY). All pass. |
| `cipherbench/engine/rule_engine.py` | RuleEngine class + create_rule_engine factory | VERIFIED | Class present with single public method `score_attempt`. Factory `create_rule_engine` present. `grep -c "random.seed(" rule_engine.py` = 0. |
| `tests/unit/test_engine/test_rule_engine.py` | Integration tests | VERIFIED | 9 tests present (plan said 8; 9th `test_cipher_key_not_accessible` added per deviation note). All pass. |
| `tests/unit/test_engine/test_seeding.py` | GEN-04/SESS-04 RNG discipline tests | VERIFIED | 6 tests present. All pass including 50-run determinism and global state isolation. |
| `tests/test_properties.py` | Hypothesis property-based tests | VERIFIED | 5 `@given` tests present. All pass at 100 examples each. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/unit/test_engine/test_types.py` | `cipherbench/types.py` | `from cipherbench.types import AttemptScore, DifficultyConfig` | WIRED | Import present on line 8; both classes used in all 11 tests. |
| `cipherbench/__init__.py` | `cipherbench/types.py` | `from cipherbench.types import AttemptScore, DifficultyConfig` | WIRED | Import present on line 11; both in `__all__`. |
| `tests/unit/test_engine/test_layers.py` | `cipherbench/engine/layers.py` | `from cipherbench.engine.layers import apply_state_layer, apply_cross_char_layer, count_correct` | WIRED | Import present on line 14; all three functions used in 16 tests. |
| `cipherbench/engine/rule_engine.py` | `cipherbench/engine/layers.py` | `from cipherbench.engine.layers import apply_state_layer, apply_cross_char_layer, count_correct` | WIRED | Import present on line 41; all three functions called in `_encode_for_round` and `score_attempt`. |
| `cipherbench/engine/rule_engine.py` | `cipherbench/types.py` | `from cipherbench.types import AttemptScore, DifficultyConfig` | WIRED | Import present on line 40; both used in `score_attempt` and `create_rule_engine`. |
| `cipherbench/__init__.py` | `cipherbench/engine/rule_engine.py` | `from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine` | WIRED | Import present on line 12; both in `__all__`. |
| `tests/test_properties.py` | `cipherbench/engine/rule_engine.py` | `from cipherbench.engine.rule_engine import create_rule_engine` | WIRED | Import present on line 19; `create_rule_engine` called in all 5 `@given` tests. |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase contains no dynamic-data rendering components (no UI, no API endpoint returning DB data). All artifacts are pure computation or test code. The "data flow" for this phase is: `create_rule_engine(seed)` → `rng.randint(...)` → `base_shifts`, `k` → `_encode_for_round` → `count_correct` → `AttemptScore`. This was verified directly via the spot-check `e.score_attempt('ABCDE')` returning `AttemptScore(score=0, max_score=5, is_correct=False)` — real computation, not a static return.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Package importable | `python3 -c "from cipherbench import AttemptScore, DifficultyConfig, RuleEngine, create_rule_engine; print('imports ok')"` | `imports ok` | PASS |
| Exactly one public method | `python3 -c "from cipherbench import create_rule_engine; e=create_rule_engine(42); print([m for m in dir(e) if not m.startswith('_')])"` | `['score_attempt']` | PASS |
| score_attempt returns real values | `python3 -c "from cipherbench import create_rule_engine; e=create_rule_engine(42); r=e.score_attempt('ABCDE'); print(r.score, r.max_score, r.is_correct)"` | `0 5 False` | PASS |
| Determinism: two engines from same seed equal | `python3 -c "from cipherbench import create_rule_engine; e1=create_rule_engine(42); e2=create_rule_engine(42); print(e1.score_attempt('ABCDE') == e2.score_attempt('ABCDE'))"` | `True` | PASS |
| GEN-04 grep gate | `grep -rn "random.seed(" cipherbench/` | (no output) | PASS |
| Canonical regression AAA round 1 | `apply_state_layer("AAA", [1,2,3], 1, ALPHABET) == [1,2,3]` | `True` | PASS |
| Canonical regression BBB round 2 | `apply_state_layer("BBB", [1,2,3], 2, ALPHABET) == [3,5,7]` | `True` | PASS |
| Pull model direction | `apply_cross_char_layer([0,0,0], "ABC", k=1, ALPHABET) == "CAB"` | `True` | PASS |
| AttemptScore invariant enforcement | `AttemptScore(score=5, max_score=5, is_correct=False)` raises ValueError | PASS |
| DifficultyConfig validation | `DifficultyConfig(alphabet="A")` raises ValueError | PASS |
| FrozenInstanceError on mutation | `s.score = 4` on frozen AttemptScore raises FrozenInstanceError | PASS |
| Wrong-length guess rejected | `score_attempt("ABC")` raises ValueError, message does not leak cipher state | PASS |
| Invalid chars rejected | `score_attempt("12345")` raises ValueError | PASS |
| Full test suite | `python3 -m pytest tests/ -v --tb=short` | `47 passed in 0.21s` | PASS |

---

### Probe Execution

No `scripts/*/tests/probe-*.sh` files exist for this phase. No probes declared in plan frontmatter.

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RULE-01 | 01-01, 01-02, 01-03 | State layer: same probe in different rounds produces different encoded output | SATISFIED | `test_state_layer_changes_target_across_rounds` passes. `apply_state_layer` with linear multiplier verified by canonical regression tests. |
| RULE-02 | 01-01, 01-02, 01-03 | Cross-char layer: shift on one output char depends on a different input char | SATISFIED | `test_cross_char_pull_model_direction` locks formula to "CAB". `test_cross_char_single_char_change_affects_multiple_positions` passes. |
| RULE-03 | 01-01, 01-02, 01-03 | Hidden feedback: only correctness count returned, not encoded output | SATISFIED | `count_correct` returns aggregate int only. Ciphertext is local variable in `score_attempt`, never returned. `test_score_attempt_returns_count_only` passes. |
| RULE-04 | 01-01, 01-03 | Engine exposes only `score_attempt()` to rest of system | SATISFIED | `[m for m in dir(e) if not m.startswith('_')] == ['score_attempt']` confirmed programmatically. 3 boundary tests + Hypothesis property test all pass. |
| GEN-04 | 01-01, 01-03 | All generator sub-functions use explicit `rng` parameter; no global `random.seed()` | SATISFIED | `grep -rn "random.seed(" cipherbench/` returns zero matches. Source inspection tests pass. `random.getstate()` unchanged after factory call. |

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps RULE-01, RULE-02, RULE-03, RULE-04, and GEN-04 to Phase 1. All five are claimed by plans in this phase. No orphaned Phase 1 requirements.

Note: SESS-04 is referenced in 01-03-PLAN.md must_haves and tests but is formally mapped to Phase 3 in REQUIREMENTS.md traceability. The 50-run determinism test is implemented as a precursor verification here; SESS-04 formal coverage belongs to Phase 3.

---

### Anti-Patterns Found

| File | Pattern Searched | Result | Severity | Impact |
|------|-----------------|--------|----------|--------|
| `cipherbench/types.py` | TBD/FIXME/XXX | None found | — | — |
| `cipherbench/engine/layers.py` | TBD/FIXME/XXX | None found | — | — |
| `cipherbench/engine/rule_engine.py` | TBD/FIXME/XXX | None found | — | — |
| `cipherbench/__init__.py` | TBD/FIXME/XXX | None found | — | — |
| `tests/conftest.py` | TBD/FIXME/XXX | None found | — | — |
| `cipherbench/engine/layers.py` | `"ABCDEFGHIJKLMNOPQRSTUVWXYZ"` inside function bodies | None — alphabet is always a parameter | — | — |
| `cipherbench/engine/layers.py` | `import random` / `random.*` | None found (pure functions, no randomness) | — | — |
| `cipherbench/engine/rule_engine.py` | `random.seed(` | None found | — | — |
| All files | `return null` / `return {}` / `return []` (stub patterns) | None found | — | — |
| `tests/conftest.py` | `pytest.skip()` stubs | None — both engine fixtures are real (call `create_rule_engine`) | — | — |

No blockers, no warnings, no debt markers found in any file touched by Phase 1.

---

### Human Verification Required

#### 1. End-of-Phase Sign-Off (Harvested from 01-03-PLAN.md)

**Test:** Run `python3 -m pytest tests/ -v` and confirm all tests are green. Then run these four spot checks:
- `python3 -c "from cipherbench import create_rule_engine, DifficultyConfig; e = create_rule_engine(42); print([m for m in dir(e) if not m.startswith('_')])"`
- `python3 -c "from cipherbench import create_rule_engine; e = create_rule_engine(42); r = e.score_attempt('ABCDE'); print(r.score, r.max_score, r.is_correct)"`
- `python3 -c "from cipherbench import create_rule_engine; e1 = create_rule_engine(42); e2 = create_rule_engine(42); print(e1.score_attempt('ABCDE') == e2.score_attempt('ABCDE'))"`
- `grep -rn "random.seed(" cipherbench/`

**Expected:**
- 47 tests pass, 0 failures, 0 errors.
- First command prints `['score_attempt']`.
- Second command prints `0 5 False`.
- Third command prints `True`.
- Fourth command produces no output.

**Why human:** The 01-03-PLAN.md verification block explicitly contains a `<human-check>` element requiring the developer to run these checks interactively and type "approved" to close Phase 1. The automated verifier has confirmed all four results programmatically; this item requires the developer's explicit acknowledgment.

---

### Gaps Summary

No gaps. All four ROADMAP success criteria are verified. All required artifacts exist and are substantive and wired. All 47 tests pass. No anti-patterns, no debt markers, no stubs. The phase goal — "three-layer cipher rule engine with locked-down information boundary, all downstream code forced to interact through `score_attempt()` only" — is fully achieved in the codebase.

The `human_needed` status is solely due to the harvested `<human-check>` from 01-03-PLAN.md requiring explicit developer sign-off. Once the developer runs the four spot checks and confirms the expected output, Phase 1 is closed.

---

_Verified: 2026-05-28_
_Verifier: Claude (gsd-verifier)_
