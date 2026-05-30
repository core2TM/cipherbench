---
phase: 3
slug: session-infrastructure-model-adapters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10–15 seconds (no real API calls; mock adapter) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | ADAPT-01 | — | adapter returns str, never exposes raw API creds | unit | `uv run pytest tests/test_adapter.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | ADAPT-02 | — | token budget warning does not abort session | unit | `uv run pytest tests/test_adapter.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | ADAPT-03 | — | RateLimitError triggers backoff, not silent failure | unit | `uv run pytest tests/test_adapter.py::test_rate_limit_backoff -x -q` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | ADAPT-04 | — | regex extracts PROBE: from freeform text; fallback fires on no-match | unit | `uv run pytest tests/test_extraction.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | SESS-01 | — | session JSON written with correct schema; outcome transitions correct | unit | `uv run pytest tests/test_session_runner.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | SESS-01 | — | in_progress checkpoint present after each attempt | unit | `uv run pytest tests/test_session_runner.py::test_checkpoint -x -q` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 1 | SESS-02 | — | human play session writes same JSON schema as model session | unit | `uv run pytest tests/test_human_runner.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | SESS-04 | — | 50 sequential sessions from seed=42 produce identical outcomes | determinism | `uv run pytest tests/test_determinism.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_adapter.py` — stubs for ADAPT-01, ADAPT-02, ADAPT-03
- [ ] `tests/test_extraction.py` — stubs for ADAPT-04 probe/answer regex
- [ ] `tests/test_session_runner.py` — stubs for SESS-01 session runner
- [ ] `tests/test_human_runner.py` — stubs for SESS-02 human runner
- [ ] `tests/test_determinism.py` — stubs for SESS-04 determinism test
- [ ] `tests/conftest.py` — shared fixtures: mock adapter, sample puzzle, fixed seed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `cipherbench play` Rich terminal display (panel, colored scores, attempt table) | SESS-02 | Terminal UI rendering cannot be asserted programmatically | Run `uv run cipherbench play --seed 42 --difficulty easy`, verify Rich panel shows prompt, attempt table updates after each submission, score line is colored |
| `cipherbench run` with real Anthropic API key | SESS-01/ADAPT-01 | Requires live API key; cannot run in CI | Run `ANTHROPIC_API_KEY=xxx uv run cipherbench run --model anthropic/claude-haiku-4-5-20251001 --seed 42`, verify session JSON written to `sessions/` |
| Rate-limit checkpoint recovery | ADAPT-03 | Requires real rate-limit response or manual injection | Interrupt a run mid-session, verify `outcome='rate_limited'` in JSON, re-run same command, verify resume from last attempt |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
