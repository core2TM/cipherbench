---
phase: cipherbench-fresh-pass
reviewed: 2026-05-30T00:00:00Z
depth: standard
files_reviewed: 42
files_reviewed_list:
  - cipherbench/__init__.py
  - cipherbench/adapters/__init__.py
  - cipherbench/adapters/litellm_adapter.py
  - cipherbench/cli/__init__.py
  - cipherbench/cli/app.py
  - cipherbench/engine/__init__.py
  - cipherbench/engine/layers.py
  - cipherbench/engine/rule_engine.py
  - cipherbench/puzzle.py
  - cipherbench/scoring/__init__.py
  - cipherbench/scoring/report_writer.py
  - cipherbench/scoring/reporter.py
  - cipherbench/scoring/scorer.py
  - cipherbench/session/__init__.py
  - cipherbench/session/extractor.py
  - cipherbench/session/human_runner.py
  - cipherbench/session/inspector.py
  - cipherbench/session/model_runner.py
  - cipherbench/session/prompt.py
  - cipherbench/session/schema.py
  - cipherbench/session/writer.py
  - cipherbench/types.py
  - tests/conftest.py
  - tests/integration/test_determinism.py
  - tests/test_properties.py
  - tests/unit/test_adapters/test_litellm_adapter.py
  - tests/unit/test_cli/test_commands.py
  - tests/unit/test_engine/test_layers.py
  - tests/unit/test_engine/test_rule_engine.py
  - tests/unit/test_engine/test_seeding.py
  - tests/unit/test_engine/test_types.py
  - tests/unit/test_puzzle/test_puzzle.py
  - tests/unit/test_scoring/test_report_writer.py
  - tests/unit/test_scoring/test_reporter.py
  - tests/unit/test_scoring/test_scorer.py
  - tests/unit/test_session/test_extractor.py
  - tests/unit/test_session/test_human_runner.py
  - tests/unit/test_session/test_inspector.py
  - tests/unit/test_session/test_model_runner.py
  - tests/unit/test_session/test_prompt.py
  - tests/unit/test_session/test_writer.py
  - pyproject.toml
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# CipherBench: Code Review Report (Fresh Pass — Post Option-B Rewrite)

**Reviewed:** 2026-05-30
**Depth:** standard
**Files Reviewed:** 42
**Status:** issues_found

## Summary

This is a fresh adversarial review pass after the Option-B symmetric-encoding rewrite. The four previously reported critical issues have been resolved. The key design invariants were verified empirically:

1. `score_attempt` is the only public method on `RuleEngine` — confirmed.
2. Submitting `_ground_truth` to `score_attempt` produces `is_correct=True` on all five rounds for all tested seeds — confirmed for seeds 0, 42, 999 across EASY and MEDIUM difficulty using both the replicated RNG sequence and live engine calls.
3. 5-attempt limit enforced across session resumes — confirmed: `valid_attempts_start` is correctly passed and the loop condition `valid_attempts < MAX_ATTEMPTS` prevents over-budget continuation.
4. RNG isolation — confirmed: no `random.seed()`, `random.randint()`, `random.choice()`, or `random.random()` module-level calls exist in `rule_engine.py` or `layers.py`; all caller modules use isolated `random.Random()` instances.

Four warnings and three info items are surfaced below. The most actionable finding is the adversarial-loop cap (`total_iterations`) resetting to zero on session resume, which weakens the T-03-03-02 mitigation during resumed sessions. The second significant finding is the hardcoded `{5}` in the extractor regex, which silently breaks for any `output_length != 5`. The remaining findings are lower-severity but correctness-relevant.

---

## Warnings

### WR-01: `total_iterations` adversarial-loop cap resets to zero on session resume

**File:** `cipherbench/session/model_runner.py:105`

**Issue:** `total_iterations` is initialised to `0` unconditionally at the start of every `run()` call and is never restored from the existing session record when resuming a `rate_limited` session. The cap `MAX_TOTAL_ITERATIONS = 2 * MAX_ATTEMPTS = 10` (T-03-03-02) is designed to prevent an adversarial or broken model from spinning the loop indefinitely by never returning a valid `PROBE:` response. When resuming a session that already consumed, for example, 8 total iterations (3 valid + 5 extraction failures) before being rate-limited, a fresh `run()` call grants another full 10 iterations. Across the resume boundary the effective cap is doubled. `valid_attempts_start` is correctly restored and enforces the 5-valid-probe ceiling; only the extraction-failure iteration count is affected. In practice this means a resumed session can accept up to `2 * MAX_TOTAL_ITERATIONS - valid_attempts_start` total LLM calls instead of the intended `MAX_TOTAL_ITERATIONS - already_consumed`.

**Fix:** Record the already-consumed iteration count from the session record and pass it as a start value analogous to `valid_attempts_start`:

```python
# In create_model_session, resume branch (model_runner.py ~line 236)
already_used = 0
for attempt in existing["attempts"]:
    if not attempt.get("extraction_failed") and attempt.get("probe"):
        engine.score_attempt(attempt["probe"])
        already_used += 1
already_total = len(existing["attempts"])  # all entries, valid + failed

return ModelSessionRunner(
    puzzle, engine, adapter, writer, existing,
    valid_attempts_start=already_used,
    total_iterations_start=already_total,  # NEW
)
```

```python
# In ModelSessionRunner.__init__
def __init__(self, ..., valid_attempts_start: int = 0,
             total_iterations_start: int = 0) -> None:
    ...
    self._valid_attempts_start = valid_attempts_start
    self._total_iterations_start = total_iterations_start

# In ModelSessionRunner.run()
total_iterations: int = self._total_iterations_start  # was: 0
```

---

### WR-02: `extract_probe` and `extract_answer` hardcode `{5}` — silently break for any `output_length != 5`

**File:** `cipherbench/session/extractor.py:60,66,106`

**Issue:** Both extraction functions embed the literal `{5}` in their regex patterns:

```python
primary = re.search(rf"PROBE:\s*([{pattern_chars}]{{5}})", text)
fallback = re.search(rf"([{pattern_chars}]{{5}})", text)
```

The `alphabet` parameter is dynamic but the expected string length is not. The session runner passes `output_length` to `build_system_prompt` (which correctly uses it) but passes only `alphabet` to `extract_probe` and `extract_answer`. If a caller creates `DifficultyConfig(output_length=7)`, the system prompt tells the model to submit 7-char probes, but the extractor searches for exactly 5-char strings — all valid probes fail extraction and are recorded as `extraction_failed=True`. The session produces no valid attempts without any error or warning.

In v1 all presets (`EASY`, `MEDIUM`, `HARD`) use `output_length=5`, so this is latent rather than active. However, `DifficultyConfig` does not constrain `output_length` to 5, and the SDK is importable as a library. The module-level `MAX_ATTEMPTS: int = 5` constant in `extractor.py` is also misleadingly named — it documents the attempt limit, not the probe length.

**Fix:** Add `output_length` as a parameter (default `5` for backward compatibility) and use it in both regex patterns:

```python
def extract_probe(text: str, alphabet: str, output_length: int = 5) -> str | None:
    ...
    primary = re.search(rf"PROBE:\s*([{pattern_chars}]{{{output_length}}})", text)
    ...
    fallback = re.search(rf"([{pattern_chars}]{{{output_length}}})", text)

def extract_answer(text: str, alphabet: str, output_length: int = 5) -> str | None:
    ...
    primary = re.search(rf"ANSWER:\s*([{pattern_chars}]{{{output_length}}})", text)
```

Thread `output_length` through from the session runner:

```python
# model_runner.py
probe = extract_probe(raw, alphabet, output_length)
final_answer = extract_answer(raw_ans, alphabet, output_length)
```

---

### WR-03: System prompt uses `X` as the placeholder — collides with valid MEDIUM/HARD alphabet characters

**File:** `cipherbench/session/prompt.py:56-58`

**Issue:** `build_system_prompt` constructs the format example as:

```python
f"- Each probe must be submitted exactly as: PROBE: {'X' * output_length}\n"
f"- Your final answer must be submitted exactly as: ANSWER: {'X' * output_length}\n"
```

`X` is a member of the MEDIUM alphabet (`A-Z`) and the HARD alphabet (`A-Z0-9`). When a model echoes the format instruction (e.g., `"I will follow the format: PROBE: XXXXX. My actual probe is PROBE: ABCDE"`), the primary extractor pattern `PROBE:\s*([A-Z]{5})` matches the first occurrence `PROBE: XXXXX` and returns `XXXXX` — the model's intended probe `ABCDE` is ignored. Since `XXXXX` consists of valid MEDIUM/HARD alphabet characters, it passes `score_attempt` validation and wastes a probe attempt. This is a concrete behavioral regression that is more likely with reasoning models that explain their reasoning step-by-step before emitting the final formatted answer.

For EASY difficulty (alphabet `ABCDEFGHIJ`), `X` is not in the alphabet, so the primary pattern does not match `XXXXX` — EASY is unaffected.

**Fix:** Use a placeholder guaranteed to be outside all configured alphabets. Since all configured alphabets are uppercase, use lowercase characters:

```python
placeholder = "abcde"[:output_length]
f"- Each probe must be submitted exactly as: PROBE: {placeholder.upper()}\n"
```

Alternatively, use a bracketed template that cannot be matched by the regex:

```python
placeholder = "".join(f"[{i+1}]" for i in range(output_length))
f"- Each probe must be submitted exactly as: PROBE: {placeholder}\n"
# Produces: "PROBE: [1][2][3][4][5]"
```

---

### WR-04: `RuleEngine` does not enforce the 5-attempt limit — contract is documentation-only

**File:** `cipherbench/engine/rule_engine.py:87`

**Issue:** The `score_attempt` docstring and the `create_rule_engine` docstring both describe the engine as "ready for up to 5 `score_attempt` calls", but no runtime check enforces this. Calling `score_attempt` a 6th (or 10th) time succeeds silently; `_round` increments past 6, effective shifts grow linearly beyond their intended range, and the engine returns scores for arbitrarily many rounds. The session runner correctly stops at 5 via `valid_attempts < MAX_ATTEMPTS`, but `RuleEngine` is exported in the public API (`cipherbench/__init__.py`) and is callable as a library object without the runner. Any direct caller can violate the 5-attempt core mechanic without receiving any error signal.

**Fix:** Add an attempt budget counter to the engine and raise a domain-specific error when exhausted:

```python
# rule_engine.py
MAX_SCORE_ATTEMPTS: int = 5

class RuleEngine:
    def __init__(self, ...) -> None:
        ...
        self._attempts_remaining: int = MAX_SCORE_ATTEMPTS

    def score_attempt(self, guess: str) -> AttemptScore:
        if self._attempts_remaining <= 0:
            raise RuntimeError(
                "Attempt budget exhausted: this RuleEngine instance allows "
                f"at most {MAX_SCORE_ATTEMPTS} score_attempt calls."
            )
        self._attempts_remaining -= 1
        # ... rest unchanged
```

---

## Info

### IN-01: Mock `check_token_budget` in `conftest.py` returns a tuple — violates adapter interface

**File:** `tests/conftest.py:54-56`

**Issue:** The real `LiteLLMAdapter.check_token_budget` returns `None` (it is a void advisory method). The `FixedResponseAdapter` mock returns `(100, 4096)`:

```python
def check_token_budget(self, messages: list[dict]) -> tuple[int, int]:
    return (100, 4096)
```

Because the session runner wraps the call in a bare `except Exception` and ignores the return value, no test failure results. However, the mock's return-type annotation (`tuple[int, int]`) misrepresents the interface. If `check_token_budget` is ever refactored to return a meaningful value (e.g., a structured result), this mock would mask the regression.

**Fix:**
```python
def check_token_budget(self, messages: list[dict]) -> None:
    """No-op — mock does not perform real token counting."""
```

---

### IN-02: `test_difficulty_config_zero_length_rejected` has a misleading docstring and misses `output_length=1`

**File:** `tests/unit/test_engine/test_types.py:56-59`

**Issue:** The test docstring reads: `"output_length=0 must raise ValueError (output_length must be >= 1)"`. The actual minimum enforced by `DifficultyConfig.__post_init__` is `>= 2` (line 46 in `types.py`), not `>= 1`. There is no test for `output_length=1`, which is also invalid per the current constraint.

**Fix:** Correct the docstring and add the missing test:

```python
def test_difficulty_config_zero_length_rejected():
    """output_length=0 must raise ValueError (minimum is 2)."""
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="AB", output_length=0)

def test_difficulty_config_one_length_rejected():
    """output_length=1 must raise ValueError (minimum is 2)."""
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="AB", output_length=1)
```

---

### IN-03: `pyproject.toml` does not declare `asyncio_mode` for `pytest-asyncio`

**File:** `pyproject.toml:29-31`

**Issue:** `pytest-asyncio>=0.23` is listed as a dev dependency. Since pytest-asyncio 0.21, the default mode changed from `"auto"` to `"strict"`. In strict mode, async test functions must be explicitly decorated with `@pytest.mark.asyncio`, or they are silently collected as synchronous functions and never `await`-ed (they pass trivially without executing the async body). No `asyncio_mode` entry appears in `[tool.pytest.ini_options]`. There are no async tests currently, but the dependency is declared, suggesting async tests are anticipated.

**Fix:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
asyncio_mode = "auto"
```

---

_Reviewed: 2026-05-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
