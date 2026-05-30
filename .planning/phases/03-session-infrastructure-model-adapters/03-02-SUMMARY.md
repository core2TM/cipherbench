---
phase: 03-session-infrastructure-model-adapters
plan: 02
status: complete
completed: "2026-05-29"
requirements_covered:
  - ADAPT-01
  - ADAPT-02
  - ADAPT-03
  - ADAPT-04
key-files:
  created:
    - cipherbench/adapters/__init__.py
    - cipherbench/adapters/litellm_adapter.py
    - cipherbench/session/__init__.py
    - cipherbench/session/schema.py
    - cipherbench/session/extractor.py
    - cipherbench/session/prompt.py
---

## Summary

Delivered the adapter and extraction foundation — the four pure-contract modules that all downstream plans depend on. All 16 adapter and extractor tests pass (TDD RED→GREEN cycle complete).

## What Was Built

**LiteLLMAdapter** (`cipherbench/adapters/litellm_adapter.py`):
- `complete(messages: list[dict]) -> str` — calls `litellm.completion()` and returns the response string
- `check_token_budget(messages: list[dict]) -> tuple[int, int]` — returns `(estimated_tokens, model_max)` with graceful fallback for unknown models
- Tenacity retry on `RateLimitError` with exponential backoff (ADAPT-03)
- Bounded to raise `RateLimitError` after exhaustion so callers can track outcome

**Session Schema** (`cipherbench/session/schema.py`):
- `AttemptEntry` TypedDict — all D-08 fields: `attempt_num`, `probe`, `score`, `max_score`, `is_correct`, `raw_response`, `extraction_failed`
- `SessionRecord` TypedDict — all D-11 fields: `session_id`, `runner_type`, `model`, `player_name`, `seed`, `difficulty`, `puzzle_hash`, `outcome`, `final_answer`, `attempts`, `created_at`, `completed_at`

**Extractor** (`cipherbench/session/extractor.py`):
- `extract_probe(text, alphabet) -> str | None` — primary `PROBE:` tag regex, fallback 5-char alphabet run, `None` on both failing (ADAPT-04, D-01)
- `extract_answer(text, alphabet) -> str | None` — primary `ANSWER:` tag only, no fallback (D-02)
- Bounded quantifiers `{5}` in all patterns (T-03-02-03 ReDoS mitigation)
- Empty alphabet raises `ValueError` before regex construction

**Prompt Builder** (`cipherbench/session/prompt.py`):
- `build_system_prompt(alphabet, output_length) -> str` — contains `PROBE:` format instruction, no strategy hints or worked examples (D-03, D-04)
- `build_user_turn(attempt_num, attempts, max_score) -> str` — formats attempt history without per-position score breakdown (D-04)

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| test_adapters/test_litellm_adapter.py | 6 | ✓ PASSED |
| test_session/test_extractor.py | 6 | ✓ PASSED |
| test_session/test_prompt.py | 4 | ✓ PASSED |
| **Total** | **16** | **✓ ALL PASS** |

## Commits

- `97af2f0` — `test(03-02): add failing tests for LiteLLMAdapter (TDD RED)`
- `9ced7bb` — `feat(03-02): implement LiteLLMAdapter with complete(), check_token_budget(), tenacity retry`
- `61ac69a` — `test(03-02): add failing tests for session schema, extractor, and prompt builder (TDD RED)`
- `1e5cdb8` — `feat(03-02): implement session schema, extractor, and prompt builder (TDD GREEN)`

## Deviations

None. Plan executed as specified.

## Self-Check: PASSED

All must-haves verified:
- [x] LiteLLMAdapter.complete() returns str for valid messages list
- [x] check_token_budget handles unknown models gracefully
- [x] extract_probe returns 5-char string on primary PROBE: match, falls back, returns None on failure
- [x] extract_answer returns 5-char string on ANSWER: tag, None when absent
- [x] build_system_prompt contains literal 'PROBE:' and has no strategy hints
- [x] SessionRecord and AttemptEntry define all D-08 and D-11 fields
