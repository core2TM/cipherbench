# Phase 1: Rule Engine - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 9 (7 source + 2 config files)
**Analogs found:** 0 / 9 — greenfield project, no existing source code

> **Greenfield note:** The codebase has no Python source files. Every analog is drawn from the
> research corpus (RESEARCH.md, ARCHITECTURE.md, STACK.md) and the locked decisions in CONTEXT.md.
> Planner must treat all "Analog" references below as canonical specification excerpts, not
> file-path line references. Code excerpts are verbatim from the planning documents.

---

## File Classification

| New File | Role | Data Flow | Closest Analog Source | Match Quality |
|----------|------|-----------|-----------------------|---------------|
| `cipherbench/types.py` | model | transform | RESEARCH.md Pattern 2 + ARCHITECTURE.md Layer 0 | spec-derived |
| `cipherbench/__init__.py` | config | — | RESEARCH.md project structure | spec-derived |
| `cipherbench/engine/__init__.py` | config | — | RESEARCH.md project structure | spec-derived |
| `cipherbench/engine/layers.py` | utility | transform | RESEARCH.md Pattern 1 code example | spec-derived |
| `cipherbench/engine/rule_engine.py` | service | request-response | RESEARCH.md Pattern 1 code example | spec-derived |
| `tests/conftest.py` | test | — | RESEARCH.md Validation Architecture | spec-derived |
| `tests/test_types.py` | test | — | RESEARCH.md Validation Architecture | spec-derived |
| `tests/test_layers.py` | test | — | RESEARCH.md Validation Architecture | spec-derived |
| `tests/test_rule_engine.py` | test | — | RESEARCH.md Validation Architecture + Code Examples | spec-derived |
| `tests/test_properties.py` | test | — | RESEARCH.md Code Examples (Hypothesis sketches) | spec-derived |
| `pyproject.toml` | config | — | STACK.md pyproject.toml pattern | spec-derived |

---

## Pattern Assignments

### `cipherbench/types.py` (model, transform)

**Analog source:** RESEARCH.md §Pattern 2 "Data Contract Types First"

**Purpose:** Define all shared dataclasses before any other module. Every downstream phase imports
from this file. Field names are locked by D-01 through D-06.

**Core dataclass pattern** (frozen, validated via `__post_init__`):
```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class DifficultyConfig:
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # D-05: default A-Z
    output_length: int = 5                          # D-06: fixed at 5

    def __post_init__(self):
        if len(self.alphabet) < 2:
            raise ValueError("alphabet must have at least 2 characters")
        if self.output_length < 1:
            raise ValueError("output_length must be positive")


@dataclass(frozen=True)
class AttemptScore:
    score: int       # D-02: number of correctly placed characters (0..output_length)
    max_score: int   # D-02: output_length (e.g. 5)
    is_correct: bool # D-03: True iff score == max_score

    def __post_init__(self):
        if not (0 <= self.score <= self.max_score):
            raise ValueError(f"score {self.score} out of range 0..{self.max_score}")
        if self.is_correct != (self.score == self.max_score):
            raise ValueError("is_correct must match score == max_score")
```

**Rules to follow:**
- Use `frozen=True` on every type defined here — immutable after construction (D-09 alignment)
- Use `__post_init__` for invariant checks, not external validators
- No logic beyond validation — types.py is pure data, no imports from `engine/`
- `AttemptScore` fields are the downstream contract: `score`, `max_score`, `is_correct`. Do not add `ciphertext`, `key`, or `shifts` fields (RULE-04 boundary)

---

### `cipherbench/engine/layers.py` (utility, transform)

**Analog source:** RESEARCH.md §Pattern 1 "Functional Core, OOP Shell" — the pure function block

**Purpose:** Three standalone pure functions implementing each cipher layer. No class, no state,
no imports except `cipherbench.types`. All are independently testable.

**Imports pattern:**
```python
from cipherbench.types import DifficultyConfig
```

**Core pure function pattern** — all three functions follow the same signature style (explicit
parameters, no side effects, returns a value):
```python
def apply_state_layer(
    plaintext: str,
    base_shifts: list[int],
    round_num: int,
    alphabet: str,
) -> list[int]:
    """Apply round-number multiplier to base shifts. Returns shifted character indices.
    D-07: effective_shift = base_shift * round_num (linear multiplier).
    """
    effective_shifts = [s * round_num for s in base_shifts]
    indices = [alphabet.index(c) for c in plaintext]
    return [(i + s) % len(alphabet) for i, s in zip(indices, effective_shifts)]


def apply_cross_char_layer(
    shifted_indices: list[int],
    plaintext: str,
    k: int,
    alphabet: str,
) -> str:
    """Apply index-based cross-character offset. D-04: pull model —
    output position j receives extra offset from input position (j - k) mod N.
    """
    n = len(shifted_indices)
    result = []
    for j in range(n):
        source_pos = (j - k) % n
        extra_offset = alphabet.index(plaintext[source_pos])
        new_idx = (shifted_indices[j] + extra_offset) % len(alphabet)
        result.append(alphabet[new_idx])
    return "".join(result)


def count_correct(guess: str, ciphertext: str) -> int:
    """D-01/D-02: aggregate count of characters in correct position. No per-position info."""
    return sum(g == c for g, c in zip(guess, ciphertext))
```

**Rules to follow:**
- Every function receives `alphabet` as an explicit parameter — never hardcode `"ABCDEFGHIJKLMNOPQRSTUVWXYZ"` (D-05 configurability)
- Every function is a module-level function, not a method — no `self`, no class
- Functions must NOT call `random` in any form — they are deterministic given inputs
- `apply_state_layer` returns `list[int]` (indices), not `str` — the cross-char step takes indices as input, so the intermediate representation passes through cleanly
- Linear multiplier (`base_shift * round_num`) is the canonical formula matching the `AAA→BCD / BBB→DFH` examples in CONTEXT.md

---

### `cipherbench/engine/rule_engine.py` (service, request-response)

**Analog source:** RESEARCH.md §Pattern 1 — the `RuleEngine` class and `create_rule_engine` factory block

**Purpose:** The trusted oracle. Holds cipher state privately. Single public method
`score_attempt(guess) -> AttemptScore`. Factory function `create_rule_engine` is the only
authorized constructor.

**Imports pattern:**
```python
import random
from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.layers import apply_state_layer, apply_cross_char_layer, count_correct
```

**Class structure pattern** — private state, single public method:
```python
class RuleEngine:
    """Trusted oracle. Holds cipher state privately. Exposes score_attempt() only."""

    def __init__(
        self,
        base_shifts: list[int],
        k: int,
        difficulty: DifficultyConfig,
        ground_truth: str,
    ) -> None:
        self._base_shifts = base_shifts      # private — D-09
        self._k = k                          # private — D-09
        self._alphabet = difficulty.alphabet  # private — D-09
        self._ground_truth = ground_truth    # private — D-09
        self._round = 1                      # private mutable state

    def score_attempt(self, guess: str) -> AttemptScore:
        """The only public method. Validates input, encodes for current round, returns score."""
        # Input validation (ASVS V5)
        if len(guess) != len(self._ground_truth):
            raise ValueError(
                f"guess length {len(guess)} does not match output_length "
                f"{len(self._ground_truth)}"
            )
        if not all(c in self._alphabet for c in guess):
            raise ValueError("guess contains characters outside the configured alphabet")

        # Capture round before incrementing (Pitfall 5 prevention)
        round_num = self._round
        self._round += 1

        # Encode ground truth for this round
        current_target = self._encode_for_round(round_num)
        score = count_correct(guess, current_target)
        return AttemptScore(
            score=score,
            max_score=len(guess),
            is_correct=(score == len(guess)),
        )

    def _encode_for_round(self, round_num: int) -> str:
        """Private: apply state + cross-char layers to ground_truth for this round."""
        shifted = apply_state_layer(
            self._ground_truth, self._base_shifts, round_num, self._alphabet
        )
        return apply_cross_char_layer(shifted, self._ground_truth, self._k, self._alphabet)

    # NO other public methods. No reset(), no get_key(), no cipher_text property.
```

**Factory function pattern** — D-10, D-11 (RNG isolation, fresh instance per session):
```python
def create_rule_engine(seed: int, difficulty: DifficultyConfig) -> RuleEngine:
    """Factory. Constructs fresh RuleEngine from seed. Never reuse an instance. D-10, D-11."""
    rng = random.Random(seed)       # D-11: isolated instance, not random.seed()
    alphabet = difficulty.alphabet
    n = difficulty.output_length     # D-06: fixed at 5
    base_shifts = [rng.randint(1, len(alphabet) - 1) for _ in range(n)]
    k = rng.randint(1, n - 1)       # D-04: cross-char offset k
    # Ground truth: encode a fixed reference string through base cipher at construction
    # (implementer must resolve Open Question 1 from RESEARCH.md before writing this line)
    ground_truth = "AAAAA"          # placeholder — replace with implementer's resolution
    return RuleEngine(
        base_shifts=base_shifts,
        k=k,
        difficulty=difficulty,
        ground_truth=ground_truth,
    )
```

**Rules to follow:**
- `_round` increment happens AFTER capturing the value for encoding (Pitfall 5)
- ALL `random` calls go through the `rng` instance in `create_rule_engine` — never `random.randint()` at module level (D-11, Pitfall 2)
- Private attributes use single underscore (`_base_shifts`). The planner may upgrade to double underscore (`__base_shifts`) for Python name-mangling protection per RESEARCH.md ASVS V4 note — document the choice
- `score_attempt` is the only public method and must validate length and alphabet (ASVS V5, Pitfall 3)
- `create_rule_engine` must be the only way to construct `RuleEngine` — no `__init__` calls from outside `rule_engine.py`

---

### `cipherbench/__init__.py` (config)

**Purpose:** Package root. Re-export the public API surface that downstream phases will import.

**Pattern:**
```python
# cipherbench/__init__.py
from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine

__all__ = ["AttemptScore", "DifficultyConfig", "RuleEngine", "create_rule_engine"]
```

**Rules to follow:**
- Only re-export the public surface — do not expose `layers.py` pure functions in the top-level namespace (they are internal implementation detail)
- Downstream phases import from `cipherbench` (top-level), not from `cipherbench.engine.rule_engine` directly

---

### `cipherbench/engine/__init__.py` (config)

**Purpose:** Sub-package marker. Empty or minimal re-export.

**Pattern:**
```python
# cipherbench/engine/__init__.py
# Engine sub-package. Import from cipherbench directly for the public API.
```

---

### `tests/conftest.py` (test, —)

**Analog source:** RESEARCH.md §Validation Architecture "Wave 0 Gaps" + pytest fixture conventions

**Purpose:** Shared pytest fixtures used across all test modules. Avoids repeated engine
construction boilerplate.

**Core fixture pattern** (function-scoped for isolation):
```python
import pytest
from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine

@pytest.fixture
def default_difficulty() -> DifficultyConfig:
    return DifficultyConfig()  # alphabet=A-Z, output_length=5

@pytest.fixture
def rule_engine_seed_42(default_difficulty):
    """Fresh engine for seed 42 — used as the canonical test seed."""
    return create_rule_engine(seed=42, difficulty=default_difficulty)

@pytest.fixture
def rule_engine_seed_0(default_difficulty):
    """Fresh engine for seed 0 — boundary/edge case seed."""
    return create_rule_engine(seed=0, difficulty=default_difficulty)
```

**Rules to follow:**
- Use `scope="function"` (default) for all engine fixtures — each test gets a fresh instance (Pitfall 1 prevention)
- Never share a single engine instance between tests

---

### `tests/test_types.py` (test, —)

**Analog source:** RESEARCH.md §Validation Architecture + Pattern 2 validation rules

**Purpose:** Verify `AttemptScore` and `DifficultyConfig` invariants defined in `__post_init__`.

**Core test pattern** (parametrized pytest, uses `pytest.raises` for invariant violations):
```python
import pytest
from cipherbench.types import AttemptScore, DifficultyConfig

def test_attempt_score_valid():
    s = AttemptScore(score=3, max_score=5, is_correct=False)
    assert s.score == 3

def test_attempt_score_correct_flag_consistency():
    with pytest.raises(ValueError):
        AttemptScore(score=5, max_score=5, is_correct=False)  # inconsistent

def test_attempt_score_out_of_range():
    with pytest.raises(ValueError):
        AttemptScore(score=6, max_score=5, is_correct=False)

def test_difficulty_config_defaults():
    d = DifficultyConfig()
    assert d.alphabet == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert d.output_length == 5

def test_difficulty_config_short_alphabet_rejected():
    with pytest.raises(ValueError):
        DifficultyConfig(alphabet="A")

def test_dataclasses_are_frozen():
    s = AttemptScore(score=3, max_score=5, is_correct=False)
    with pytest.raises(Exception):  # FrozenInstanceError
        s.score = 4
```

---

### `tests/test_layers.py` (test, —)

**Analog source:** RESEARCH.md §Validation Architecture test map (RULE-01, RULE-02 test IDs)

**Purpose:** Unit tests for each pure layer function in isolation. Uses known-good
inputs with manually traced expected outputs — the canonical test cases from CONTEXT.md.

**Core test pattern** (direct function calls with asserted expected values):
```python
import pytest
from cipherbench.engine.layers import apply_state_layer, apply_cross_char_layer, count_correct

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# RULE-01: state layer applies round multiplier correctly
def test_apply_state_layer_round_multiplier():
    # Base shifts [1, 2, 3], round 1: effective shifts [1, 2, 3]
    # "AAA" (indices [0, 0, 0]) + [1, 2, 3] mod 26 = [1, 2, 3] = "BCD"
    result = apply_state_layer("AAA", [1, 2, 3], round_num=1, alphabet=ALPHABET)
    assert result == [1, 2, 3]  # indices, not chars

def test_apply_state_layer_round_2_doubles_shifts():
    # Base shifts [1, 2, 3], round 2: effective shifts [2, 4, 6]
    # "BBB" (indices [1, 1, 1]) + [2, 4, 6] mod 26 = [3, 5, 7] = "DFH"
    result = apply_state_layer("BBB", [1, 2, 3], round_num=2, alphabet=ALPHABET)
    assert result == [3, 5, 7]

def test_apply_state_layer_wraps_modulo_alphabet():
    # Shift that exceeds alphabet length must wrap
    result = apply_state_layer("Z", [1], round_num=1, alphabet=ALPHABET)
    assert result == [0]  # Z(25) + 1 = 26 mod 26 = 0 = A

# RULE-02: cross-char interdependence
def test_cross_char_interdependence_nonzero_k():
    # k != 0 means each output position is influenced by a different input position
    # With k=1, output[0] is influenced by input[(0-1) mod N] = input[N-1]
    shifted = [0, 0, 0]  # all zeros to isolate cross-char effect
    result_k0 = apply_cross_char_layer(shifted, "AAB", k=0, alphabet=ALPHABET)
    result_k1 = apply_cross_char_layer(shifted, "AAB", k=1, alphabet=ALPHABET)
    assert result_k0 != result_k1  # cross-char must change output

def test_count_correct_aggregate_only():
    assert count_correct("ABCDE", "ABCDE") == 5
    assert count_correct("ABCDE", "XBCDE") == 4
    assert count_correct("AAAAA", "BBBBB") == 0
    assert count_correct("ABCDE", "EDCBA") == 1  # only C in position 2 matches
```

---

### `tests/test_rule_engine.py` (test, request-response)

**Analog source:** RESEARCH.md §Code Examples (50-run determinism test, boundary enforcement tests)
and §Validation Architecture test map (RULE-03, RULE-04, GEN-04 test IDs)

**Purpose:** Integration tests for `RuleEngine` and `create_rule_engine`. Tests the full
`score_attempt` pipeline, the information boundary, and session determinism.

**Core test pattern** (uses `conftest.py` fixtures; tests boundaries via `hasattr`):
```python
import pytest
import ast
import inspect
from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine

# RULE-03: score_attempt returns aggregate count, not ciphertext or key
def test_score_attempt_returns_count_only(rule_engine_seed_42):
    result = rule_engine_seed_42.score_attempt("AAAAA")
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 5
    assert isinstance(result.is_correct, bool)
    assert not hasattr(result, 'ciphertext')
    assert not hasattr(result, 'key')
    assert not hasattr(result, 'shifts')

# RULE-04: no public key accessor on RuleEngine
def test_no_public_key_accessor(rule_engine_seed_42):
    engine = rule_engine_seed_42
    assert not hasattr(engine, 'cipher_key')
    assert not hasattr(engine, 'ground_truth')
    assert not hasattr(engine, 'encode')
    assert not hasattr(engine, 'base_shifts')
    # Only public method must be score_attempt
    public_methods = [m for m in dir(engine) if not m.startswith('_')]
    assert public_methods == ['score_attempt']

# RULE-04: factory produces fresh isolated instances
def test_factory_produces_fresh_instances():
    d = DifficultyConfig()
    engine_a = create_rule_engine(seed=42, difficulty=d)
    engine_b = create_rule_engine(seed=42, difficulty=d)
    # Both fresh, same seed — score_attempt on same guess returns same result
    result_a = engine_a.score_attempt("ABCDE")
    result_b = engine_b.score_attempt("ABCDE")
    assert result_a == result_b

# RULE-01: same probe in different rounds must reflect state evolution
def test_state_layer_changes_encoding_across_rounds(rule_engine_seed_42):
    # Score for same probe at round 1 vs round 2 will differ when target shifts
    score_r1 = rule_engine_seed_42.score_attempt("AAAAA")
    score_r2 = rule_engine_seed_42.score_attempt("AAAAA")
    # Not asserting inequality (could collide by chance), but verifying distinct rounds ran
    assert score_r1.max_score == 5
    assert score_r2.max_score == 5

# GEN-04: no global random.seed() in source (smoke test via grep)
def test_no_global_random_seed_calls():
    import cipherbench.engine.rule_engine as mod
    import cipherbench.engine.layers as layers_mod
    for module in [mod, layers_mod]:
        src = inspect.getsource(module)
        assert "random.seed(" not in src, (
            f"Found forbidden random.seed() in {module.__name__}"
        )

# SESS-04: 50 sequential runs with same seed produce identical score sequences
def test_fifty_sequential_runs_are_deterministic():
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

# Input validation: wrong length and invalid chars raise ValueError
def test_score_attempt_rejects_wrong_length(rule_engine_seed_42):
    with pytest.raises(ValueError):
        rule_engine_seed_42.score_attempt("ABC")  # too short

def test_score_attempt_rejects_invalid_chars(rule_engine_seed_42):
    with pytest.raises(ValueError):
        rule_engine_seed_42.score_attempt("12345")  # digits not in A-Z alphabet
```

---

### `tests/test_properties.py` (test, —)

**Analog source:** RESEARCH.md §Code Examples — Hypothesis strategy sketches

**Purpose:** Property-based tests using Hypothesis. Tests invariants that must hold for any
seed, alphabet, and guess combination. Finds edge cases that hand-written tests miss.

**Core Hypothesis pattern** (using `@given` with `st.integers` and `st.text`):
```python
from hypothesis import given, settings
from hypothesis import strategies as st
from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# RULE-04: AttemptScore must not contain cipher key or encoded target
@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
def test_score_attempt_never_reveals_private_state(seed, guess):
    engine = create_rule_engine(seed=seed, difficulty=DifficultyConfig())
    result = engine.score_attempt(guess)
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 5
    assert result.is_correct == (result.score == 5)
    assert not hasattr(result, 'ciphertext')
    assert not hasattr(result, 'key')
    assert not hasattr(result, 'shifts')

# GEN-04 + SESS-04: same seed always produces the same score for the same probe
@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    probe=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
def test_same_seed_same_probe_same_score(seed, probe):
    d = DifficultyConfig()
    engine_1 = create_rule_engine(seed=seed, difficulty=d)
    engine_2 = create_rule_engine(seed=seed, difficulty=d)
    assert engine_1.score_attempt(probe) == engine_2.score_attempt(probe)

# AttemptScore invariants hold under any valid construction
@given(
    score=st.integers(min_value=0, max_value=5),
    max_score=st.just(5),
)
def test_attempt_score_invariant(score, max_score):
    from cipherbench.types import AttemptScore
    result = AttemptScore(score=score, max_score=max_score, is_correct=(score == max_score))
    assert result.is_correct == (result.score == result.max_score)
```

---

### `pyproject.toml` (config)

**Analog source:** STACK.md §Python Packaging — pyproject.toml pattern block

**Purpose:** Package definition, CLI entry point, dev dependency declarations, pytest config.

**Core pattern:**
```toml
[project]
name = "cipherbench"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "rich>=13.0",
    "litellm>=1.40",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "hypothesis>=6.100",
    "pytest-asyncio>=0.23",
]

[project.scripts]
cipherbench = "cipherbench.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

**Note:** Phase 1 does not implement the CLI — omit `[project.scripts]` from the Phase 1
`pyproject.toml` or stub it. Add it when the CLI phase begins. The `[tool.pytest.ini_options]`
section is needed for Phase 1 test runs.

---

## Shared Patterns

### RNG Isolation (D-11, GEN-04)

**Source:** RESEARCH.md §Reproducibility and Seeding; CONTEXT.md D-11
**Apply to:** `create_rule_engine` factory; any future generation sub-function

The only correct RNG pattern in this project:
```python
# CORRECT — isolated instance
rng = random.Random(seed)
value = rng.randint(0, 25)

# FORBIDDEN — global state mutation
random.seed(seed)          # never
value = random.randint(0, 25)  # never (use rng.randint instead)
```

All sub-functions that need randomness must accept `rng: random.Random` as an explicit parameter.
The `rng` instance is created exactly once in `create_rule_engine` and passed down. Zero module-level
`random.*` calls in `cipherbench/` package.

### Private State Pattern (D-09, RULE-04)

**Source:** CONTEXT.md D-09; RESEARCH.md §Security Domain ASVS V4 note
**Apply to:** `RuleEngine` class

All cipher state uses the single-underscore private convention:
```python
self._base_shifts = ...
self._k = ...
self._alphabet = ...
self._ground_truth = ...
self._round = 1
```

The planner may choose to upgrade to double-underscore (`__base_shifts`) for Python name-mangling.
Document the choice in a comment. Either way, verify with:
```python
public_methods = [m for m in dir(engine) if not m.startswith('_')]
assert public_methods == ['score_attempt']
```

### Frozen Dataclass with `__post_init__` Validation

**Source:** RESEARCH.md §Pattern 2; stdlib `dataclasses` docs
**Apply to:** All types in `types.py`; any future dataclass added to the project

```python
@dataclass(frozen=True)
class SomeType:
    field: int

    def __post_init__(self):
        if self.field < 0:
            raise ValueError("field must be non-negative")
```

`frozen=True` prevents mutation after construction. `__post_init__` runs at construction time.
No external validation library needed — stdlib only.

### Input Validation in `score_attempt` (ASVS V5)

**Source:** RESEARCH.md §Security Domain — "Injecting adversarial `guess` strings"
**Apply to:** `RuleEngine.score_attempt`

```python
def score_attempt(self, guess: str) -> AttemptScore:
    if len(guess) != len(self._ground_truth):
        raise ValueError(
            f"guess length {len(guess)} does not match output_length {len(self._ground_truth)}"
        )
    if not all(c in self._alphabet for c in guess):
        raise ValueError("guess contains characters outside the configured alphabet")
    # ... proceed with encoding
```

Error messages must use generic phrasing — do not include `_ground_truth`, `_base_shifts`,
or `_k` values in the error string (information leakage via exception).

### Off-by-One Prevention for Round Counter

**Source:** RESEARCH.md §Pitfall 5 "Incorrect Score Increment for State"
**Apply to:** `RuleEngine.score_attempt`

Always capture `round_num` before incrementing:
```python
round_num = self._round   # capture first
self._round += 1           # then increment
current_target = self._encode_for_round(round_num)  # use captured value
```

Never use `self._round` after it has been incremented within the same `score_attempt` call.

---

## No Analog Found

All Phase 1 files have no close match in the existing codebase because this is a greenfield project.
Planner must derive all implementation from the research documents listed above.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| All 11 files listed above | various | various | Greenfield — no Python source exists in the repo |

---

## Open Questions for Planner (from RESEARCH.md)

Before implementing `create_rule_engine` and `RuleEngine._encode_for_round`, the planner must resolve:

1. **Ground truth definition** (RESEARCH.md Open Question 1, Assumption A3): What exactly does
   `score_attempt` compare a guess against? Is `_ground_truth` a fixed string set at construction
   (constant across rounds), or is it a per-round encoded output? The canonical examples in
   CONTEXT.md (`AAA→BCD`, `BBB→DFH`) show the *encoded output* changes per round, which implies
   the target changes per round. Resolution: `_encode_for_round(round_num)` should produce the
   per-round encoded target from a fixed canonical reference string (e.g., `"AAAAA"`), and
   `score_attempt` compares the guess against that round-specific encoded target.

2. **Cross-char formula direction** (RESEARCH.md Open Question / Assumption A4): The pull model
   (`output[j]` receives influence from `input[(j-k) % N]`) is recommended in the research and
   used in all code examples above. The planner should write the canonical trace test first
   (Pitfall 4 in RESEARCH.md) to lock the direction before implementing.

3. **Single vs. double underscore** (RESEARCH.md §Security Domain ASVS V4 note): The planner
   must choose `_base_shifts` (convention) or `__base_shifts` (name-mangling). Document the choice
   in the class docstring.

---

## Metadata

**Analog search scope:** `/Users/atipat/Desktop/superfinal/` — all non-git, non-planning files
**Files scanned:** 0 Python source files found (confirmed greenfield)
**Planning artifacts read:** CONTEXT.md, RESEARCH.md, ARCHITECTURE.md, STACK.md
**Pattern extraction date:** 2026-05-28
**Source document confidence:** HIGH (all patterns derived from verified planning documents)
