---
phase: 05-session-inspector
fixed_at: 2026-05-30T00:00:00Z
review_path: .planning/phases/05-session-inspector/05-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-05-30T00:00:00Z
**Source review:** .planning/phases/05-session-inspector/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, CR-02, WR-01, WR-02)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: `inspect_session` raises `SystemExit` from a public SDK function

**Files modified:** `cipherbench/session/inspector.py`, `cipherbench/cli/app.py`
**Commit:** 333f2b8
**Applied fix:** Defined `InspectorError(RuntimeError)` at module level in `inspector.py` and replaced all five `raise SystemExit(1)` calls in `inspect_session` with `raise InspectorError(...)`. Updated `inspect_command` in `app.py` to import `InspectorError`, wrap the `inspect_session` call in a `try/except InspectorError` block, and convert it to `typer.Exit(code=1)`. CLI behaviour is identical; library callers can now recover via `except InspectorError`.

### CR-02: Empty `session_id` string matches every session

**Files modified:** `cipherbench/session/inspector.py`
**Commit:** 333f2b8
**Applied fix:** Added an early guard at the top of `inspect_session` (after the `console is None` check) that raises `InspectorError("session_id must be a non-empty string.")` when `session_id` is falsy or whitespace-only, preventing `""` from silently matching every JSON file in the directory.

### WR-01: Rich markup injection from unescaped session fields in `display_session`

**Files modified:** `cipherbench/session/inspector.py`
**Commit:** 333f2b8
**Applied fix:** Added `from rich.markup import escape` import. Wrapped all user-controlled values passed to Rich `Panel` body and `table.add_row` with `escape()`: `session_id`, `runner_type`, `model`/`player_name` (runner_label), `seed`, `difficulty`, `outcome`, and `probe`. The `title` argument to `Panel` retains intentional markup (`[bold]CipherBench Session Inspector[/bold]`) as it is a hardcoded constant, not user-controlled.

### WR-02: Dead `monkeypatch.setattr(inspector_mod, "_console", ...)` in test helper

**Files modified:** `tests/unit/test_session/test_inspector.py`
**Commit:** fd37766
**Applied fix:** Removed the `monkeypatch.setattr(inspector_mod, "_console", mock_console)` line from `_capture_display_session`. Updated the docstring to clarify that `display_session` uses only its injected `console` parameter. The monkeypatch parameter remains in the function signature for backward compatibility with call sites that pass `monkeypatch`, but the setattr has no effect and was misleading.

## Skipped Issues

None — all in-scope findings were fixed.

---

**Test results after fixes:**
- `tests/unit/test_session/test_inspector.py`: 12/12 passed
- Full suite (`tests/`): 148/148 passed

---

_Fixed: 2026-05-30T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
