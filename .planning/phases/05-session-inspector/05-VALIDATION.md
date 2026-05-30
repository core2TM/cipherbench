---
phase: 5
slug: session-inspector
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-30
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/unit/test_session/test_inspector.py -x` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/test_session/test_inspector.py -x`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-W0-01 | 01 | 0 | SESS-03 | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py -x` | ❌ W0 | ⬜ pending |
| 05-01-01 | 01 | 1 | SESS-03-A | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_session_shows_all_attempts -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | SESS-03-B | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_extraction_failure_row -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | SESS-03-C | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_footer_success -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | SESS-03-D | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py::test_display_footer_not_reached -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | SESS-03-E | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_substring_match -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 1 | SESS-03-F | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_case_insensitive -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 1 | SESS-03-G | T-05-01 | exit 1 + list on not-found (D-08) | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_not_found -x` | ❌ W0 | ⬜ pending |
| 05-01-08 | 01 | 1 | SESS-03-H | — | exit 1 + Ambiguous message (D-02) | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_ambiguous -x` | ❌ W0 | ⬜ pending |
| 05-01-09 | 01 | 1 | SESS-03-I | T-05-01 | exit 1 + D-09 message for missing dir | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_missing_dir -x` | ❌ W0 | ⬜ pending |
| 05-01-10 | 01 | 1 | SESS-03-J | — | exit 1 + D-10 message for empty dir | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_empty_dir -x` | ❌ W0 | ⬜ pending |
| 05-01-11 | 01 | 1 | SESS-03-K | — | N/A | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_command_help -x` | ❌ W0 | ⬜ pending |
| 05-01-12 | 01 | 1 | SESS-03-L | — | schema parity: human=model table structure | unit | `pytest tests/unit/test_session/test_inspector.py::test_inspect_schema_parity -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_session/test_inspector.py` — stubs for all SESS-03 sub-requirements (A–L)
- [ ] `cipherbench/session/inspector.py` — production module stub

*Shared fixtures `tmp_sessions_dir` and `_make_session` are available in existing conftest.py and test_scorer.py — no new fixture infrastructure needed.*

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
