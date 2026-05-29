---
phase: 2
slug: puzzle-generator
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-29
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python3 -m pytest tests/ -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -q --tb=short`
- **After every plan wave:** Run `python3 -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | GEN-01, GEN-03 | T-2-01 | `DifficultyConfig` rejects `cross_char_depth <= 0`, `> output_length-1`, `state_change_rate <= 0` | unit | `python3 -m pytest tests/unit/test_engine/test_types.py -x -q` | ✅ (extended) | ⬜ pending |
| 2-01-02 | 01 | 1 | GEN-01 | — | `apply_state_layer` with rate=1.0 produces bit-identical results to Phase 1; rate=1.5 produces different shifts | unit | `python3 -m pytest tests/unit/test_engine/test_layers.py -x -q` | ✅ (extended) | ⬜ pending |
| 2-02-01 | 02 | 1 | GEN-01 | T-2-02 | `create_rule_engine` with depth=1 is RNG-call-count-equivalent to Phase 1; `engine._k_list` is a list | unit | `python3 -m pytest tests/unit/test_engine/test_rule_engine.py -x -q` | ✅ (spot-check via python3 -c commands) | ⬜ pending |
| 2-02-02 | 02 | 1 | GEN-01 | — | All 47 Phase 1 tests pass after engine changes | regression | `python3 -m pytest tests/ -q --tb=short` | ✅ | ⬜ pending |
| 2-03-01 | 03 | 2 | GEN-01, GEN-02, GEN-03 | — | `generate_puzzle(42)` twice → identical `puzzle_hash`; `verify_puzzle` passes; `get_tier(EASY)` returns `'easy'` | unit | `python3 -m pytest tests/unit/test_puzzle/ -x -q` | ✅ (created in Plan 03 Task 1) | ⬜ pending |
| 2-03-02 | 03 | 2 | GEN-02 | T-2-03 | `verify_puzzle` raises `ValueError('hash mismatch: ...')` when seed is mutated | unit | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_verify_puzzle_detects_mutation -x` | ✅ (created in Plan 03 Task 2) | ⬜ pending |
| 2-03-03 | 03 | 2 | GEN-03 | — | EASY/MEDIUM/HARD produce measurably distinct score distributions over 100 seeds | integration | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_difficulty_tiers_distinct_complexity -x` | ✅ (created in Plan 03 Task 2) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/test_puzzle/__init__.py` — test sub-package init for puzzle.py tests (Plan 03 Task 1)
- [x] `tests/unit/test_puzzle/test_puzzle.py` — full GEN-01, GEN-02, GEN-03 coverage (Plan 03 Task 2)

*Existing infrastructure covers engine-layer tests — only puzzle sub-package is new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-platform hash stability | GEN-02 | Requires running on a second OS/Python version | Run `python3 -c "from cipherbench.puzzle import generate_puzzle; p = generate_puzzle(42); print(p.puzzle_hash)"` on a second machine and confirm output matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
