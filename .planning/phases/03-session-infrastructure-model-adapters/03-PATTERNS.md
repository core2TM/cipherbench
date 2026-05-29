# Phase 3: Session Infrastructure & Model Adapters - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 11 new files
**Analogs found:** 11 / 11 (all have at least partial analog from existing codebase)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `cipherbench/adapters/litellm_adapter.py` | service | request-response | `cipherbench/engine/rule_engine.py` | role-match (factory class + single-method boundary) |
| `cipherbench/session/model_runner.py` | service | request-response | `cipherbench/engine/rule_engine.py` | role-match (stateful loop, factory pattern) |
| `cipherbench/session/human_runner.py` | service | request-response | `cipherbench/engine/rule_engine.py` | role-match (loop structure mirrors model runner) |
| `cipherbench/session/prompt.py` | utility | transform | `cipherbench/puzzle.py` (`generate_puzzle`) | role-match (pure factory function returning structured data) |
| `cipherbench/session/extractor.py` | utility | transform | `cipherbench/engine/layers.py` | exact (pure functions, explicit params, no side effects) |
| `cipherbench/session/writer.py` | utility | file-I/O | `cipherbench/puzzle.py` (`_compute_hash`) | partial (stdlib-only, pathlib, dataclass serialization) |
| `cipherbench/session/schema.py` | model | — | `cipherbench/types.py` | exact (frozen dataclass or TypedDict value object) |
| `cipherbench/cli/app.py` | controller | request-response | `cipherbench/__init__.py` (public surface) | partial (entry-point wiring; no CLI analog exists yet) |
| `tests/unit/test_adapters/test_litellm_adapter.py` | test | — | `tests/unit/test_engine/test_rule_engine.py` | exact (class-based isolation, pytest fixtures, mock injection) |
| `tests/unit/test_session/test_model_runner.py` etc. | test | — | `tests/unit/test_engine/test_seeding.py` | exact (50-run determinism pattern directly reused for SESS-04) |
| `tests/integration/test_determinism.py` | test | — | `tests/unit/test_engine/test_seeding.py` | exact (SESS-04 is the session-level analogue of the engine-level 50-run test) |

---

## Pattern Assignments

### `cipherbench/adapters/litellm_adapter.py` (service, request-response)

**Analog:** `cipherbench/engine/rule_engine.py`

**Rationale:** `RuleEngine` is the closest existing class: single-boundary public method, private state (model string and config), constructed via a factory pattern, no global state mutations.

**Imports pattern** (`rule_engine.py` lines 39–49):
```python
from __future__ import annotations

import random
from typing import Optional

from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.layers import (
    apply_state_layer,
    apply_cross_char_layer_multi,
    count_correct,
)
```
Apply to adapter: replace engine imports with `litellm` and `tenacity` imports; keep `from __future__ import annotations` and `from typing import Optional`.

**Class structure pattern** (`rule_engine.py` lines 52–84):
```python
class RuleEngine:
    """Trusted oracle. Holds cipher state privately. Exposes score_attempt() only."""

    def __init__(
        self,
        base_shifts: list,
        k_list: list,
        difficulty: DifficultyConfig,
        ground_truth: str,
    ) -> None:
        self._base_shifts = base_shifts     # private — D-09
        self._k_list = k_list               # private — D-09
        ...

    def score_attempt(self, guess: str) -> AttemptScore:
        """... This is the ONLY public method (RULE-04)."""
        ...
```
Apply to adapter: single `__init__(self, model: str, litellm_config_path: str | None = None)` storing `self._model` and `self._litellm_config_path`. Public methods: `complete(messages)` and `check_token_budget(messages)`. Match the docstring pattern (first line: one-sentence description, then blank line, then `Parameters / Returns / Raises` sections).

**Factory function pattern** (`rule_engine.py` lines 187–247):
```python
def create_rule_engine(seed: int, difficulty: Optional[DifficultyConfig] = None) -> RuleEngine:
    """Construct a fresh RuleEngine for a given seed and difficulty (D-10, D-11).

    This is the ONLY authorized way to construct a RuleEngine. ...
    """
    if difficulty is None:
        difficulty = DifficultyConfig()
    ...
    return RuleEngine(...)
```
Apply to adapter: the `LiteLLMAdapter` class can be constructed directly (no factory needed), but mirror the same `__init__` defensive guard style — e.g., validate `model` is non-empty. The session runner is the "factory" caller.

**Input validation pattern** (`rule_engine.py` lines 118–125):
```python
# --- Input validation (ASVS V5; T-03-02 mitigation) ---
if len(guess) != len(self._ground_truth):
    raise ValueError(
        f"guess length {len(guess)} does not match output_length "
        f"{len(self._ground_truth)}"
    )
if not all(c in self._alphabet for c in guess):
    raise ValueError("guess contains characters outside the configured alphabet")
```
Apply to adapter: validate `messages` is a non-empty list of dicts before calling `litellm.completion`. Raise `ValueError` with generic message — do not include API keys in error text (ASVS V2 / security boundary mirrors RULE-04).

**Module docstring pattern** (`rule_engine.py` lines 1–38):
```python
"""CipherBench rule engine — stateful oracle with hard information boundary.

This module contains two public names:
  RuleEngine       — ...
  create_rule_engine — ...

Design decisions implemented here:
  D-09  ...
  D-10  ...
  D-11  ...
  ...
"""
```
Apply to adapter: open with `"""CipherBench LiteLLM adapter — ..."""`, then list public names, then list design decisions by ID (ADAPT-01, ADAPT-02, ADAPT-03).

---

### `cipherbench/session/model_runner.py` (service, request-response)

**Analog:** `cipherbench/engine/rule_engine.py` (stateful class) + `cipherbench/puzzle.py` (factory function)

**Core loop pattern** (`rule_engine.py` lines 86–138 — `score_attempt` method):
```python
def score_attempt(self, guess: str) -> AttemptScore:
    # --- Input validation ---
    ...
    # --- Capture round before incrementing ---
    round_num = self._round
    self._round += 1
    # --- Encode and score ---
    current_target = self._encode_for_round(round_num)
    score = count_correct(guess, current_target)
    return AttemptScore(
        score=score,
        max_score=len(guess),
        is_correct=(score == len(guess)),
    )
```
Apply to runner: the attempt loop mirrors this capture-then-mutate structure. Capture `attempt_num` before incrementing the counter. Call `engine.score_attempt(probe)` to get `AttemptScore`. Map `AttemptScore` fields directly to the D-08 attempt entry dict using the same field names (`score`, `max_score`, `is_correct`).

**Factory pattern for session runner** (`puzzle.py` lines 85–109 — `generate_puzzle`):
```python
def generate_puzzle(seed: int, difficulty: Optional[DifficultyConfig] = None) -> Puzzle:
    """... This is the ONLY authorized way to construct a Puzzle (D-06)."""
    if difficulty is None:
        difficulty = DifficultyConfig()
    engine = create_rule_engine(seed, difficulty)
    ...
    return Puzzle(seed=seed, difficulty=difficulty, puzzle_hash=puzzle_hash)
```
Apply to runner: provide a `create_model_session(seed, difficulty, model, adapter, output_dir)` factory function that validates args, calls `generate_puzzle` and `puzzle.create_engine()`, then constructs and returns `ModelSessionRunner`. The runner is never constructed directly by CLI code.

**Imports pattern** (`puzzle.py` lines 21–29):
```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional

from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
```
Apply to runner: replace `hashlib` with `datetime`, `os`, `tempfile`, `re`, `pathlib.Path`. Import from `cipherbench.puzzle` (`generate_puzzle`, `get_tier`, `EASY`, `MEDIUM`, `HARD`) and `cipherbench.adapters.litellm_adapter` (`LiteLLMAdapter`).

**RNG isolation pattern** (`rule_engine.py` lines 218–219):
```python
rng = random.Random(seed)  # D-11: isolated instance; global random state never touched
```
Apply to runner: when generating a default seed (when `--seed` is not provided), use `random.Random().randint(0, 2**32 - 1)` — never `random.randint()` (module-level). Follow the same comment style referencing the decision ID.

---

### `cipherbench/session/human_runner.py` (service, request-response)

**Analog:** `cipherbench/engine/rule_engine.py` (loop structure) + `cipherbench/session/model_runner.py` (mirror structure)

**Key difference from model runner:** Replace `adapter.complete(messages)` with `typer.prompt()` for input. Replace checkpoint write after API call with checkpoint write after `engine.score_attempt()`. The session JSON schema (D-11) and attempt entry schema (D-08) are identical — `raw_response` is `null`, `extraction_failed` is always `False`.

**Input validation pattern** to mirror (`rule_engine.py` lines 118–125 — score_attempt validation):
```python
if len(guess) != len(self._ground_truth):
    raise ValueError(...)
if not all(c in self._alphabet for c in guess):
    raise ValueError(...)
```
Apply to human runner: validate `typer.prompt()` result against `puzzle.difficulty.output_length` and `puzzle.difficulty.alphabet`. Re-prompt on failure (loop, not raise) — per D-05 human input handling.

---

### `cipherbench/session/prompt.py` (utility, transform)

**Analog:** `cipherbench/engine/layers.py` (pure functions, explicit params, no side effects)

**Pure function pattern** (`layers.py` lines 20–63 — `apply_state_layer`):
```python
def apply_state_layer(
    plaintext: str,
    base_shifts: list,
    round_num: int,
    alphabet: str,
    state_change_rate: float = 1.0,
) -> list:
    """Apply round-number multiplier to base shifts and shift each plaintext character.

    ...

    Parameters
    ----------
    plaintext : str
        ...
    ...

    Returns
    -------
    list[int]
        ...
    """
    if len(plaintext) != len(base_shifts):
        raise ValueError(...)
    ...
    return [...]
```
Apply to prompt.py: define `build_system_prompt(alphabet: str, output_length: int) -> str` and `build_user_turn(attempt_num: int, attempts: list[dict], max_score: int) -> str` as pure module-level functions. No class needed. Use the same NumPy-style docstring format (Parameters / Returns sections). No side effects, no I/O. All state passed explicitly.

**Module docstring pattern** (`layers.py` lines 1–15):
```python
"""Pure cipher layer functions — the functional core of CipherBench.

Three module-level pure functions implement each cipher layer independently.
No state, no side effects, no randomness — all inputs are explicit parameters.
...

Design decisions implemented here:
  D-04  Pull model...
  D-05  ...
"""
```
Apply to prompt.py: open with `"""Pure prompt builder functions — ...` and list which D-xx decisions the module implements.

---

### `cipherbench/session/extractor.py` (utility, transform)

**Analog:** `cipherbench/engine/layers.py` (pure functions, explicit params, no state)

This is the closest analog in role and data flow: both modules export pure functions that transform a string input into a derived output using only stdlib operations and explicit parameters.

**Pure function pattern** (`layers.py` lines 175–200 — `count_correct`):
```python
def count_correct(guess: str, ciphertext: str) -> int:
    """Count characters in the correct position — aggregate only (D-01, RULE-03).

    Returns the number of positions where ``guess[i] == ciphertext[i]``.
    ...

    Parameters
    ----------
    guess : str
        ...
    ciphertext : str
        ...

    Returns
    -------
    int
        ...
    """
    if len(guess) != len(ciphertext):
        raise ValueError(...)
    return sum(g == c for g, c in zip(guess, ciphertext))
```
Apply to extractor: define `extract_probe(text: str, alphabet: str) -> str | None` and `extract_answer(text: str, alphabet: str) -> str | None` as pure functions. Same NumPy docstring style. Raise `ValueError` on bad inputs (e.g., empty alphabet), return `None` on failed extraction (not raise). The `None` return signals the caller to set `extraction_failed=True`.

**No-state enforcement** (`layers.py` header comment lines 6–8):
```python
# No state, no side effects, no randomness — all inputs are explicit parameters.
# These functions are called internally by RuleEngine (Plan 03) and are never
# exposed in the top-level cipherbench namespace
```
Apply to extractor: `extractor.py` is `cipherbench/session/`-internal. Do not re-export from `cipherbench/__init__.py`.

---

### `cipherbench/session/writer.py` (utility, file-I/O)

**Analog:** `cipherbench/puzzle.py` (`_compute_hash`, `generate_puzzle` — stdlib-only, `json`, `hashlib`, `pathlib`-style)

No exact file-I/O analog exists in the current codebase. The closest structural analog is `puzzle.py`'s use of stdlib-only operations (`json.dumps`, `hashlib.sha256`) and `pathlib`-style patterns. The atomic write pattern comes from RESEARCH.md Pattern 2 (no existing analog).

**Stdlib-only pattern** (`puzzle.py` lines 71–82):
```python
def _compute_hash(base_shifts: list, k_list: list, ground_truth: str) -> str:
    """Compute SHA-256 hex digest of derived puzzle state (D-07, D-08).

    Serialization: json.dumps with sort_keys=True — deterministic across
    all Python versions and platforms for int/str values.
    """
    payload = json.dumps(
        {"base_shifts": base_shifts, "ground_truth": ground_truth, "k_list": k_list},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()
```
Apply to writer: use `json.dump(data, f, indent=2, ensure_ascii=False)` for session serialization. Use `sort_keys=False` (insertion order is meaningful for human readability of session files). Use `pathlib.Path` for all path operations. The atomic write pattern (from RESEARCH.md Pattern 2) has no existing analog; implement directly from the research pattern.

**Private helper pattern** (`puzzle.py` lines 71–72 — leading underscore):
```python
def _compute_hash(base_shifts: list, k_list: list, ground_truth: str) -> str:
```
Apply to writer: name the atomic write helper `_atomic_write_json(path: Path, data: dict) -> None`. Use leading underscore to signal it is a module-private implementation detail not part of the public writer API.

**Imports pattern** (`puzzle.py` lines 21–29):
```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional

from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
```
Apply to writer: replace `hashlib` / `dataclass` with `os`, `tempfile`, `datetime`; no external `cipherbench` imports (writer is a leaf module — depends only on stdlib).

---

### `cipherbench/session/schema.py` (model, —)

**Analog:** `cipherbench/types.py` (frozen dataclasses as value objects)

**Frozen dataclass pattern** (`types.py` lines 12–57):
```python
@dataclass(frozen=True)
class DifficultyConfig:
    """Configuration for a cipher puzzle difficulty tier.

    Frozen after construction — mutation raises FrozenInstanceError (D-09).
    All puzzle instances with the same DifficultyConfig are comparable.

    Fields
    ------
    alphabet : str
        The character set used for input and output. Default: A-Z (D-05).
        ...
    """

    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    output_length: int = 5
    state_change_rate: float = 1.0
    cross_char_depth: int = 1

    def __post_init__(self) -> None:
        if len(self.alphabet) < 2:
            raise ValueError("alphabet must have at least 2 characters")
        ...
```
Apply to schema.py: `SessionRecord` may be a `TypedDict` rather than frozen dataclass — because session data evolves (attempts list grows), and `TypedDict` is better for JSON round-trip. However, `AttemptEntry` (the per-attempt dict structure from D-08) can be a `TypedDict` with required fields. Follow the same docstring style: class-level docstring with `Fields` section listing each key.

**No-import-from-engine rule** (`types.py` lines 1–8):
```python
"""CipherBench data contracts.

...
NO imports from cipherbench.engine — this is the pure data layer.
"""
from dataclasses import dataclass
```
Apply to schema.py: no imports from `cipherbench.engine` or `cipherbench.session` other than stdlib typing. `schema.py` is the pure data contract module for Phase 3.

---

### `cipherbench/cli/app.py` (controller, request-response)

**Analog:** `cipherbench/__init__.py` (public API surface / entry-point wiring)

No CLI analog exists in the codebase. The closest structural analog is `__init__.py` as the "public surface" coordinator that imports and re-exports internal modules without containing logic. The Typer subcommand pattern comes entirely from RESEARCH.md Pattern 3.

**Public surface / wiring-only pattern** (`__init__.py` lines 1–34):
```python
"""CipherBench — AGI Proximity Benchmark.

Public API surface. Import from here; internal module paths are implementation detail.

Available:
    AttemptScore      — frozen dataclass: ...
    ...
"""
from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
from cipherbench.puzzle import Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD

__all__ = [
    "AttemptScore",
    ...
]
```
Apply to cli/app.py: the CLI app module is the "wiring" layer — it imports `ModelSessionRunner`, `HumanSessionRunner`, and `LiteLLMAdapter` but contains no business logic. The `run_command` and `play_command` functions only: parse flags, construct runner, call `runner.run()`, print outcome. Mirror the `__init__.py` philosophy: this file is a coordinator, not an implementor.

**`pyproject.toml` entry point** — must add after creating `cli/app.py`:
```toml
[project.scripts]
cipherbench = "cipherbench.cli.app:app"
```
This is the analog of the existing `[tool.hatch.build.targets.wheel] packages = ["cipherbench"]` entry in `pyproject.toml` — both are wiring declarations, not logic.

---

### `tests/unit/test_adapters/test_litellm_adapter.py` (test, —)

**Analog:** `tests/unit/test_engine/test_rule_engine.py`

**Test module docstring pattern** (`test_rule_engine.py` lines 1–8):
```python
"""Integration tests for RuleEngine class and create_rule_engine factory.

Covers: information boundary enforcement (RULE-04, D-09), input validation (ASVS V5),
state evolution (RULE-01), and factory isolation (D-10).
"""
from __future__ import annotations

import inspect

import pytest

from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine
```
Apply to test_litellm_adapter.py: docstring lists ADAPT-01, ADAPT-02, ADAPT-03 coverage. Import `pytest`, `unittest.mock.patch`, `litellm`, and `LiteLLMAdapter`. Use `from __future__ import annotations`.

**Section separator + comment pattern** (`test_rule_engine.py` lines 19–21):
```python
# ---------------------------------------------------------------------------
# Boundary tests — RULE-04, D-09
# ---------------------------------------------------------------------------
```
Apply to test_litellm_adapter.py: use identical separator style. Sections: `# ADAPT-01: complete() routing`, `# ADAPT-02: token budget check`, `# ADAPT-03: rate-limit retry`.

**Source inspection test pattern** (`test_seeding.py` lines 32–38):
```python
def test_no_global_random_seed_in_rule_engine_module():
    """GEN-04: random.seed() must not appear anywhere in rule_engine.py source."""
    src = inspect.getsource(rule_engine_mod)
    assert "random.seed(" not in src, (
        "Found forbidden 'random.seed(' in ..."
    )
```
Apply to test_litellm_adapter.py: add `test_no_api_key_in_source()` using `inspect.getsource` to assert no hardcoded API key patterns appear in `litellm_adapter.py`.

**Fixture pattern** (`conftest.py` lines 12–24):
```python
@pytest.fixture
def default_difficulty() -> DifficultyConfig:
    """Standard A-Z alphabet with output_length=5. Used as the default config."""
    return DifficultyConfig()


@pytest.fixture
def rule_engine_seed_42(default_difficulty: DifficultyConfig):
    """Fresh RuleEngine for seed 42 — the canonical test seed."""
    return create_rule_engine(seed=42, difficulty=default_difficulty)
```
Apply to conftest.py additions: add `@pytest.fixture def mock_adapter()` returning a `FixedResponseAdapter("PROBE: AAAAA")`, and `@pytest.fixture def tmp_sessions_dir(tmp_path)` returning `tmp_path / "sessions"`. Follow the same docstring style: one-sentence description of what is returned.

---

### `tests/unit/test_session/test_model_runner.py` etc. (test, —)

**Analog:** `tests/unit/test_engine/test_seeding.py` (50-run determinism, RNG isolation)

**50-run determinism pattern** (`test_seeding.py` lines 72–91):
```python
def test_fifty_sequential_runs_are_deterministic():
    """SESS-04: 50 sequential calls with seed=42 must produce identical score sequences."""
    SEED = 42
    PROBE = "ABCDE"
    ROUNDS = 5
    reference_scores = None

    for run in range(50):
        engine = create_rule_engine(seed=SEED, difficulty=DifficultyConfig())
        scores = [engine.score_attempt(PROBE).score for _ in range(ROUNDS)]
        if reference_scores is None:
            reference_scores = scores
        assert scores == reference_scores, (
            f"Run {run}: got {scores}, expected {reference_scores}. State bleed detected."
        )
```
Apply to `tests/integration/test_determinism.py`: replicate this exact loop structure at the session level. Replace `create_rule_engine` + `score_attempt` calls with `ModelSessionRunner(seed=SEED, ..., adapter=mock_adapter).run()`. Replace `reference_scores` with `reference_outcome`. Assert `session["outcome"] == reference_outcome` for all 50 runs. Keep the same assertion message format: `f"Run {run}: got {actual}, expected {expected}. State bleed detected."`.

**RNG non-pollution test pattern** (`test_seeding.py` lines 126–139):
```python
def test_rng_does_not_pollute_global_random():
    """D-11: create_rule_engine must not touch the global random state."""
    state_before = random.getstate()
    create_rule_engine(seed=42, difficulty=DifficultyConfig())
    state_after = random.getstate()
    assert state_after == state_before, (
        "Global random.getstate() changed after create_rule_engine(). ..."
    )
```
Apply to test_model_runner.py: add equivalent test that calls `ModelSessionRunner(...).run()` with a mock adapter and asserts `random.getstate()` is unchanged before and after. This extends D-11 enforcement to the session layer.

**Input validation test pattern** (`test_rule_engine.py` lines 58–73):
```python
def test_score_attempt_rejects_wrong_length(rule_engine_seed_42):
    """score_attempt must raise ValueError for a guess that is too short."""
    with pytest.raises(ValueError):
        rule_engine_seed_42.score_attempt("ABC")
```
Apply to test_extractor.py: `test_extract_probe_returns_none_on_no_match()`, `test_extract_probe_primary_pattern()`, `test_extract_probe_fallback_pattern()`, `test_extract_answer_returns_none_on_missing_tag()`. Use `pytest.raises(ValueError)` for invalid `alphabet` inputs to `extract_probe`.

---

### `tests/integration/test_determinism.py` (test, —)

**Analog:** `tests/unit/test_engine/test_seeding.py` (direct structural template)

The entire `test_fifty_sequential_runs_are_deterministic` function in `test_seeding.py` is the template. The integration version lifts that same test to the session level using a mock adapter. See SESS-04 pattern in the previous section.

**Additional pattern — differentiation test** (`test_seeding.py` lines 99–118):
```python
def test_different_seeds_produce_different_scores():
    """Different seeds must produce different score sequences with high probability."""
    ...
    assert scores_1 != scores_2, (
        f"Seed 1 and seed 2 produced identical score sequences {scores_1}. ..."
    )
```
Apply to test_determinism.py: add `test_different_seeds_produce_different_outcomes()` verifying that two sessions from different seeds do NOT necessarily produce the same outcome with a deterministic mock adapter — confirming the puzzle generator's seed effect propagates end-to-end.

---

## Shared Patterns

### Frozen Dataclass / TypedDict Value Objects
**Source:** `cipherbench/types.py` lines 12–91
**Apply to:** `cipherbench/session/schema.py`

```python
@dataclass(frozen=True)
class AttemptScore:
    score: int
    max_score: int
    is_correct: bool

    def __post_init__(self) -> None:
        if not (0 <= self.score <= self.max_score):
            raise ValueError(f"score {self.score} out of range 0..{self.max_score}")
        if self.is_correct != (self.score == self.max_score):
            raise ValueError("is_correct must match score == max_score")
```

Rule: every value object gets a `__post_init__` that validates field consistency. `schema.py` session types follow this rule — `AttemptEntry` validates that if `extraction_failed=True` then `probe` is `None`.

### Pure Functions with Explicit Parameters and NumPy Docstrings
**Source:** `cipherbench/engine/layers.py` lines 20–200
**Apply to:** `cipherbench/session/prompt.py`, `cipherbench/session/extractor.py`

```python
def apply_state_layer(
    plaintext: str,
    base_shifts: list,
    round_num: int,
    alphabet: str,
    state_change_rate: float = 1.0,
) -> list:
    """One-line description.

    Parameters
    ----------
    plaintext : str
        ...
    ...

    Returns
    -------
    list[int]
        ...
    """
    if len(plaintext) != len(base_shifts):
        raise ValueError(...)
    ...
```

All utility functions in Phase 3 use:
1. NumPy-style docstrings (Parameters / Returns / Raises sections)
2. Explicit parameters — no global state reads
3. Guard clauses at the top of the function body
4. Module-level functions (not methods) where no state is needed

### Factory Function Pattern
**Source:** `cipherbench/puzzle.py` lines 85–109 (`generate_puzzle`) and `cipherbench/engine/rule_engine.py` lines 187–247 (`create_rule_engine`)
**Apply to:** Session runner constructors, `cipherbench/cli/app.py` (creates runner objects)

```python
def generate_puzzle(seed: int, difficulty: Optional[DifficultyConfig] = None) -> Puzzle:
    """... This is the ONLY authorized way to construct a Puzzle (D-06)."""
    if difficulty is None:
        difficulty = DifficultyConfig()
    ...
    return Puzzle(...)
```

Rule: complex objects that require validated construction get a factory function, not raw `__init__` calls in CLI code. CLI code calls `create_model_session(...)`, not `ModelSessionRunner(...)` directly.

### RNG Isolation (D-11)
**Source:** `cipherbench/engine/rule_engine.py` line 218
**Apply to:** `cipherbench/session/model_runner.py` (seed default generation), `cipherbench/cli/app.py` (seed default for `--num-puzzles`)

```python
rng = random.Random(seed)  # D-11: isolated instance; global random state never touched
```

Never call `random.randint()`, `random.choice()`, or `random.seed()` at module level. Always `random.Random(seed_value).method(...)`. For one-shot default seeds, `random.Random().randint(0, 2**32 - 1)` creates a throwaway isolated instance.

### Private Module Helpers (Leading Underscore)
**Source:** `cipherbench/puzzle.py` line 71 (`_compute_hash`)
**Apply to:** `cipherbench/session/writer.py` (`_atomic_write_json`)

```python
def _compute_hash(base_shifts: list, k_list: list, ground_truth: str) -> str:
```

Leading underscore convention for module-private helpers. These are implementation details not re-exported through `__init__.py` or accessible as part of the public API.

### `from __future__ import annotations`
**Source:** Every existing module in the project (`rule_engine.py` line 39, `puzzle.py` line 21, `layers.py` line 18)
**Apply to:** All Phase 3 modules

```python
from __future__ import annotations
```

All `.py` files begin with `from __future__ import annotations`. This is a universal project convention — do not omit it.

### Test Section Separators
**Source:** `tests/unit/test_engine/test_rule_engine.py` lines 19–21
**Apply to:** All test files in Phase 3

```python
# ---------------------------------------------------------------------------
# Boundary tests — RULE-04, D-09
# ---------------------------------------------------------------------------
```

Every test module uses this exact 75-character separator style to delimit test groups. Group names reference requirement IDs (RULE-04, ADAPT-01, SESS-04, etc.).

### Pytest Fixtures — Function-Scoped, Fresh per Test
**Source:** `tests/conftest.py` lines 12–33
**Apply to:** `tests/conftest.py` additions, all new test files

```python
@pytest.fixture
def rule_engine_seed_42(default_difficulty: DifficultyConfig):
    """Fresh RuleEngine for seed 42 — the canonical test seed.

    Function-scoped (default): each test gets an isolated instance with _round=1.
    """
    return create_rule_engine(seed=42, difficulty=default_difficulty)
```

All fixtures are function-scoped (default). The docstring explains why: prevents state bleed. New fixtures follow the same pattern: `mock_adapter()` returns `FixedResponseAdapter("PROBE: AAAAA")`, `tmp_sessions_dir(tmp_path)` returns a fresh temp directory per test.

---

## No Analog Found

All Phase 3 files have at least a partial analog. The files below have no direct analog but map to patterns from RESEARCH.md (all patterns documented above):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `cipherbench/cli/app.py` | controller | request-response | No Typer CLI exists in codebase yet; use RESEARCH.md Pattern 3 (Typer subcommand) and mirror `__init__.py` wiring philosophy |
| `cipherbench/session/writer.py` | utility | file-I/O | No file I/O exists in codebase; use RESEARCH.md Pattern 2 (`_atomic_write_json`) + `puzzle.py` stdlib-only style |
| `tests/unit/test_cli/test_commands.py` | test | — | No Typer CLI tests exist; use RESEARCH.md Pattern (CliRunner) + `test_rule_engine.py` section structure |

---

## Metadata

**Analog search scope:** `cipherbench/` (all modules), `tests/` (all test modules)
**Files scanned:** 10 source files, 6 test files
**Pattern extraction date:** 2026-05-29
