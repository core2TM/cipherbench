---
phase: 4
slug: scoring-reporting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 + hypothesis 6.141.1 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-v --tb=short"` |
| **Quick run command** | `python3 -m pytest tests/unit/test_scoring/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/unit/test_scoring/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-W0-01 | Wave 0 | 0 | SCORE-01–04 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/ -x -q` | ❌ W0 | ⬜ pending |
| 04-01-01 | scorer.py | 1 | SCORE-01 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_success_rate -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | scorer.py | 1 | SCORE-01 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_success_rate_empty -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | scorer.py | 1 | SCORE-02 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_score_success -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | scorer.py | 1 | SCORE-02 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_score_failure -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | scorer.py | 1 | SCORE-02 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_extraction_failures_excluded -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | scorer.py | 1 | SCORE-03 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_agi_proximity_with_baseline -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | scorer.py | 1 | SCORE-03 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_agi_proximity_no_baseline -x` | ❌ W0 | ⬜ pending |
| 04-01-08 | scorer.py | 1 | SCORE-04 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_group_by_difficulty -x` | ❌ W0 | ⬜ pending |
| 04-01-09 | scorer.py | 1 | SCORE-01/04 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_compute_report_totals_consistent -x` | ❌ W0 | ⬜ pending |
| 04-01-10 | scorer.py | 1 | SCORE-02 | — | N/A | property | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_efficiency_score_in_range -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | report_writer.py | 2 | SCORE-01–04 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_report_writer.py -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | cli score cmd | 3 | SCORE-01–04 | — | N/A | unit (CLI) | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_score_command_help -x` | ❌ W0 | ⬜ pending |
| 04-03-02 | cli score cmd | 3 | SCORE-01–04 | — | N/A | unit | `python3 -m pytest tests/unit/test_scoring/test_scorer.py::test_load_sessions_skips_non_terminal -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_scoring/__init__.py` — test package init
- [ ] `tests/unit/test_scoring/test_scorer.py` — stubs for all SCORE-01–04 unit tests
- [ ] `tests/unit/test_scoring/test_report_writer.py` — stubs for JSON writer tests
- [ ] All stubs use `pytest.mark.skip` or `pass` bodies — must be importable and collectible by pytest

*Existing pytest infrastructure (`conftest.py`, `pyproject.toml`) covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live summary line printed at end of `cipherbench run` | D-03 | Requires live model call or mock adapter; CliRunner integration covers flags but not end-to-end output | Run `cipherbench run --model <model> --runs-per-puzzle 1 --seeds 1` and verify the last line matches pattern `N/M success (P%) \| avg efficiency: X.XX \| AGI proximity: Y.YYx` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
