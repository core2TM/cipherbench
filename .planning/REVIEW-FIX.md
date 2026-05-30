---
phase: cipherbench-fresh-pass
fixed_at: 2026-05-30T00:00:00Z
review_path: /Users/atipat/Desktop/superfinal/.planning/REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# CipherBench: Code Review Fix Report (Fresh Pass)

**Fixed at:** 2026-05-30
**Source review:** /Users/atipat/Desktop/superfinal/.planning/REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01 through WR-04; 3 Info items out of scope per fix_scope=critical_warning)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: `total_iterations` adversarial-loop cap resets to zero on session resume

**Files modified:** `cipherbench/session/model_runner.py`
**Applied fix:**
Added `total_iterations_start: int = 0` parameter to `ModelSessionRunner.__init__`, stored as `self._total_iterations_start`. In `run()`, changed `total_iterations: int = 0` to `total_iterations: int = self._total_iterations_start`. In the resume branch of `create_model_session`, computed `already_total = len(existing["attempts"])` (count of all attempt entries, valid + extraction-failed) and passed it as `total_iterations_start=already_total` alongside the existing `valid_attempts_start=already_used`. This ensures the `MAX_TOTAL_ITERATIONS` adversarial-loop cap (T-03-03-02) is correctly applied across session resume boundaries.

### WR-02: `extract_probe` and `extract_answer` hardcode `{5}` — silently break for any `output_length != 5`

**Files modified:** `cipherbench/session/extractor.py`, `cipherbench/session/model_runner.py`
**Applied fix:**
Added `output_length: int = 5` parameter (defaulting to 5 for backward compatibility) to both `extract_probe` and `extract_answer`. Updated all three regex patterns to use `{{{output_length}}}` instead of `{{5}}`. Updated docstrings to document the new parameter and updated return-type descriptions from "5-character" to "`output_length`-character". Updated call sites in `model_runner.py`: `extract_probe(raw, alphabet, output_length)` and `extract_answer(raw_ans, alphabet, output_length)`. Human runner (`human_runner.py`) does not call these functions — it uses `_validate_probe` directly — so no update was needed there.

### WR-03: System prompt uses `X` as the placeholder — collides with valid MEDIUM/HARD alphabet characters

**Files modified:** `cipherbench/session/prompt.py`, `cipherbench/session/model_runner.py`
**Applied fix:**
Changed `'X' * output_length` to `'#' * output_length` as the format placeholder in `build_system_prompt`. The `#` character is not in any supported alphabet (`ABCDEFGHIJ` for EASY, `A-Z` for MEDIUM, `A-Z0-9` for HARD), so the extractor regex can never match it — a model echoing the format example will not trigger a false extraction hit. Also updated the inline final-answer prompt in `model_runner.py` (the "You have used all your probe attempts" message) from `'X' * output_length` to `'#' * output_length` for consistency. Updated surrounding description text from "where each X is a character from the alphabet" to "where each # is replaced by a character from the alphabet".

### WR-04: `RuleEngine` does not enforce the 5-attempt limit — contract is documentation-only

**Files modified:** `cipherbench/engine/rule_engine.py`
**Applied fix:**
Added module-level constant `MAX_SCORE_ATTEMPTS: int = 5` with docstring explaining its purpose. Added `self._attempts_remaining: int = MAX_SCORE_ATTEMPTS` to `RuleEngine.__init__` (private attribute, single-underscore convention, consistent with existing `_round` pattern). Added a guard at the top of `score_attempt` that raises `RuntimeError("Attempt budget exhausted: ...")` when `_attempts_remaining <= 0`, then decrements `_attempts_remaining` before proceeding with validation and scoring. The `_attempts_remaining` attribute starts with `_` so it does not appear in the `dir(engine)` public-method check in `test_no_public_key_accessor`. The session resume path in `create_model_session` benefits correctly: the replay loop calls `engine.score_attempt` for each already-consumed valid attempt, which naturally decrements `_attempts_remaining` so that `MAX_SCORE_ATTEMPTS - already_used` attempts remain for the resumed session — no special handling required.

**Full test suite result:** 148 passed in 11.37s. All tests pass after applying all four fixes.

---

_Fixed: 2026-05-30_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
