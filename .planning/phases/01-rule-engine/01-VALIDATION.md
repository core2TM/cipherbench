---
phase: 1
slug: rule-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + hypothesis 6.x |
| **Config file** | pyproject.toml (Wave 0 installs) |
| **Quick run command** | `uv run pytest tests/unit/test_engine/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/test_engine/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | RULE-01 | — | N/A | unit stub | `uv run pytest tests/unit/test_engine/ -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | RULE-01 | — | State layer changes output between rounds | unit | `uv run pytest tests/unit/test_engine/test_layers.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | RULE-02 | — | Cross-char interdependence active | unit | `uv run pytest tests/unit/test_engine/test_layers.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | RULE-03 | C-4 | score_attempt returns count only, no key/ciphertext | unit | `uv run pytest tests/unit/test_engine/test_rule_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | RULE-04 | C-2 | RuleEngine accepts rng param, no global random.seed() | unit | `uv run pytest tests/unit/test_engine/test_seeding.py -x -q` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 1 | GEN-04 | C-3 | Hypothesis property tests for layer composition | property | `uv run pytest tests/unit/test_engine/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — test package root
- [ ] `tests/unit/__init__.py` — unit test package
- [ ] `tests/unit/test_engine/__init__.py` — engine test package
- [ ] `tests/unit/test_engine/test_layers.py` — stubs for RULE-01, RULE-02
- [ ] `tests/unit/test_engine/test_rule_engine.py` — stubs for RULE-03
- [ ] `tests/unit/test_engine/test_seeding.py` — stubs for RULE-04
- [ ] `pyproject.toml` — with pytest + hypothesis + hatchling config
- [ ] `uv` lockfile — dev dependencies pinned

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| grep confirms no `random.seed(` calls | RULE-04 | Source scan, not runtime | `grep -r "random\.seed(" src/cipherbench/engine/` returns zero matches |
| Private attrs not accessible without name mangling | RULE-03 | Convention enforcement | Review `engine/rule_engine.py` — all sensitive attrs use single `_` prefix minimum |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
