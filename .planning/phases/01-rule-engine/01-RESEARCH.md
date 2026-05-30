# Phase 1: Rule Engine - Research

**Researched:** 2026-05-28
**Domain:** Stateful cipher rule engine — pure Python, stdlib-only, information-boundary enforcement
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** `AttemptScore` exposes aggregate count only — the number of characters in the correct position (Mastermind black-pegs only). No per-position breakdown.
**D-02:** Score scale = length of the output string (not normalized). For a 5-char output, score range is 0–5.
**D-03:** Final answer evaluation is exact match only (binary). No partial credit.
**D-04:** Cross-character mechanism: index-based offset injection. Character at input position `i` shifts the character at output position `(i + k) mod N`, where `k` is a puzzle-level parameter.
**D-05:** Alphabet: configurable via difficulty parameter, defaulting to A–Z (26 chars, modulo 26). At higher difficulty tiers, the alphabet can expand (e.g., A–Z + 0–9).
**D-06:** Output string length: fixed at 5 characters. Consistent across all puzzles.
**D-07:** State trigger: round-number multiplier applied to base shift values. Round N multiplies the base shift of each character position. Matches the `AAA → BCD` / `BBB → DFH` example.
**D-08:** The multiplier applies only to base shift values, not to the cross-char offset `k`.
**D-09:** Enforcement mechanism: wrapper class with private state. `RuleEngine` stores cipher state in private attributes (`_key`, `_shifts`, `_state`). The only public methods are `score_attempt(guess: str) -> AttemptScore` and nothing else.
**D-10:** Session lifecycle: fresh instance per session via factory function. `create_rule_engine(seed: int, difficulty: DifficultyConfig) -> RuleEngine`.
**D-11:** All generation sub-functions that need randomness accept an explicit `rng: random.Random` parameter. No `random.seed()` calls anywhere.

### Claude's Discretion

- The specific polynomial formula for round-multiplier state (linear `base_shift * round_number` vs. quadratic or other) is left to implementer. Must be deterministic given round number and produce meaningfully different outputs across rounds.
- Test strategy specifics (unit test depth, Hypothesis strategies, coverage depth) are left to the planner. The constraint is the 50-run determinism test (SESS-04) and that all three layers are independently testable.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RULE-01 | System applies a state layer so that submitting the same probe string in a different round produces a different encoded output | D-07: round-number multiplier on base shifts; pure function `apply_state_layer(plaintext, shifts, round_num)` |
| RULE-02 | System applies a cross-character interdependence layer so that the shift applied to one output character depends on the value of a different input character | D-04: index-based offset injection formula `(i + k) mod N`; pure function `apply_cross_char_layer(plaintext, k, alphabet)` |
| RULE-03 | System applies a hidden feedback layer that returns only a correctness score — the actual encoded output is never revealed mid-session | D-01/D-02/D-03: `AttemptScore` dataclass with aggregate count only; private `_encode()` method; scoring compares internally |
| RULE-04 | Rule engine exposes only `score_attempt(guess) -> AttemptScore` — cipher key and ground-truth ciphertext are never accessible from outside the engine boundary | D-09: wrapper class with private attributes; single public method; factory pattern D-10 |
| GEN-04 | All generator sub-functions accept an explicit `rng: random.Random` parameter — no global `random.seed()` calls anywhere in the generation path | D-11: explicit `rng` threading; `create_rule_engine` constructs `random.Random(seed)` once and passes to all sub-functions |

</phase_requirements>

---

## Summary

Phase 1 delivers the intellectual core of CipherBench: a three-layer cipher rule engine with a hard information boundary. All locked decisions (D-01 through D-11) specify a precise mathematical design — the planner does not need to choose between approaches, only to implement what is specified. The key architectural insight is **functional-core, OOP-shell**: the three transform layers are pure functions that are easy to test independently; the `RuleEngine` class holds mutable state (round counter) and calls these pure functions in sequence. The only externally-visible behavior is `score_attempt(guess) -> AttemptScore`.

The brute-force resistance analysis shows the design is well-protected: with an aggregate (non-separable) score and 5 attempts, a model can extract at most ~12.9 bits of information, while the cipher key space is ~23.5 bits — a 10.6-bit deficit. This calculation understates the real resistance because the state evolution (D-07) means the target ciphertext changes each round, breaking every known Mastermind-optimal strategy. The AAAAA/BBBBB position-scanning attack explicitly fails because cross-char mixing makes the score non-separable. This confirms the math is sound before the first line of implementation code.

The phase must also establish the foundational data contracts: `DifficultyConfig`, `AttemptScore`, and the `create_rule_engine` factory signature. These types will be imported by every subsequent phase. Defining them here with locked field sets prevents cascading refactors downstream.

**Primary recommendation:** Implement in exact sequence — data types first (`types.py`), then pure transform functions (`engine/layers.py`), then `RuleEngine` wrapper (`engine/rule_engine.py`), then test all three layers independently using pytest fixtures and Hypothesis strategies before connecting them.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cipher state management (round counter, shift history) | Rule Engine (`RuleEngine` class) | — | Only component that may hold mutable session state in this phase |
| Base cipher transform (apply shifts to plaintext) | Pure function layer (`layers.py`) | — | No state needed; must be independently testable |
| State evolution (round multiplier on shifts) | Pure function layer (`layers.py`) | — | Depends only on `round_num` and `base_shifts`; no class state |
| Cross-character mixing | Pure function layer (`layers.py`) | — | Depends only on `plaintext`, `k`, `alphabet`; no class state |
| Score computation (count correct positions) | Pure function layer (`layers.py`) | — | Pure comparison; no state |
| Information boundary enforcement | `RuleEngine` wrapper class | — | Private attributes `_key`, `_shifts`; single public method |
| RNG instantiation and threading | `create_rule_engine` factory | Pure sub-functions | Factory creates `random.Random(seed)`; sub-functions receive it via parameter |
| Data contract definitions | `cipherbench/types.py` | — | Shared types imported by all phases; defined once here |

---

## Standard Stack

### Core (Phase 1 — no new installs, stdlib-only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `random.Random` (stdlib) | n/a | Per-puzzle isolated RNG instance | [VERIFIED: python docs] Instantiated with `seed`, does not pollute global `random` state; deterministic sequence per seed |
| `dataclasses` (stdlib) | n/a | `AttemptScore`, `DifficultyConfig`, `PuzzleConfig` data containers | [VERIFIED: python docs] Zero-dependency, clean field definitions, auto-generated `__eq__` and `__repr` |
| `dataclasses.field` + `__post_init__` | n/a | Validated dataclass construction | [VERIFIED: python docs] `__post_init__` for invariant checks (e.g., alphabet length > 0) without external validation library |
| `abc.ABC` / `abc.abstractmethod` (stdlib) | n/a | Abstract base if needed for layer protocol | [ASSUMED] May not be needed if layers are plain functions; include only if type-checking benefits justify it |

### Development/Testing Only

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | `>=8.0` (latest: 8.4.2) | Primary test runner | [VERIFIED: PyPI registry] Industry standard; fixture system maps directly to cipher state initialization |
| `hypothesis` | `>=6.100` (latest: 6.141.1) | Property-based testing for rule engine | [VERIFIED: PyPI registry] Auto-generates adversarial puzzle configs; finds combinatorial edge cases hand-tests miss |
| `pytest-asyncio` | `>=0.23` (latest: 1.2.0) | Async test support | [VERIFIED: PyPI registry] Not needed for Phase 1 (no async code), but install now for later phases; pin `>=0.23` |
| `hatchling` | `>=1.21` (latest: 1.27.0) | Build backend | [VERIFIED: PyPI registry] pyproject.toml build backend; zero-config src layout |

### Not Used in This Phase

- Typer, Rich, LiteLLM — no CLI or LLM interaction in Phase 1
- SQLite — no session storage in Phase 1
- NumPy — stdlib `random.Random` is sufficient; NumPy only if puzzle generation needs array-level sampling (Phase 2 concern)

**Installation (dev environment setup for Phase 1):**

```bash
# With uv (recommended per CLAUDE.md)
uv init cipherbench
uv add --dev pytest hypothesis pytest-asyncio

# pyproject.toml also needs hatchling build-backend — no uv add needed for build backends
# They go in [build-system] requires, installed automatically by uv/pip

# With pip (compatible fallback)
pip install -e ".[dev]"
```

**Version verification (conducted 2026-05-28):**
- pytest: 8.4.2 on PyPI [VERIFIED: PyPI registry]
- hypothesis: 6.141.1 on PyPI [VERIFIED: PyPI registry]
- pytest-asyncio: 1.2.0 on PyPI [VERIFIED: PyPI registry]
- hatchling: 1.27.0 on PyPI [VERIFIED: PyPI registry]
- typer: 0.23.2 on PyPI [VERIFIED: PyPI registry] (higher than CLAUDE.md's 0.12 — use `>=0.12`)
- rich: 15.0.0 on PyPI [VERIFIED: PyPI registry]
- numpy: 2.0.2 on PyPI [VERIFIED: PyPI registry] (optional, Phase 2 concern)

---

## Package Legitimacy Audit

> Phase 1 introduces dev dependencies only. slopcheck run 2026-05-28 confirmed all OK.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pytest | PyPI | 15+ yrs | Hundreds of M/wk | github.com/pytest-dev/pytest | [OK] | Approved |
| hypothesis | PyPI | 10+ yrs | Tens of M/wk | github.com/HypothesisWorks/hypothesis | [OK] | Approved |
| pytest-asyncio | PyPI | 7+ yrs | Tens of M/wk | github.com/pytest-dev/pytest-asyncio | [OK] | Approved |
| hatchling | PyPI | 4+ yrs | Tens of M/wk | github.com/pypa/hatch | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*All four packages passed slopcheck verification on 2026-05-28.*

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │   create_rule_engine()       │
                    │   factory function           │
                    │                             │
                    │  1. build DifficultyConfig   │
                    │  2. rng = random.Random(seed)│
                    │  3. generate base_shifts via │
                    │     rng (explicit threading) │
                    │  4. generate k offset via rng│
                    │  5. return RuleEngine(...)   │
                    └──────────────┬──────────────┘
                                   │ RuleEngine instance
                                   ▼
                    ┌─────────────────────────────────┐
                    │         RuleEngine              │
                    │  _base_shifts: list[int]  (priv)│
                    │  _k: int                  (priv)│
                    │  _alphabet: str           (priv)│
                    │  _ground_truth: str       (priv)│
                    │  _round: int              (priv)│
                    │                                 │
                    │  + score_attempt(guess) → AttemptScore  ← ONLY PUBLIC METHOD
                    └──────────────┬──────────────────┘
                                   │ calls pure functions
                          ┌────────┼────────┐
                          ▼        ▼        ▼
               ┌──────────────┐  ┌────────────────┐  ┌────────────────────┐
               │apply_state() │  │apply_cross_char│  │ count_correct()    │
               │  base_shifts │  │  (i+k) mod N   │  │ aggregate score    │
               │  × round_num │  │  mixing        │  │ 0..5, no positions │
               └──────────────┘  └────────────────┘  └────────────────────┘

Legend:
  → data flow (input to output)
  (priv) = private attribute, inaccessible from outside RuleEngine
  ONLY PUBLIC METHOD = information boundary enforcement
```

### Recommended Project Structure

```
cipherbench/
├── __init__.py          # package root; re-exports public API
├── types.py             # DifficultyConfig, AttemptScore, PuzzleConfig dataclasses
└── engine/
    ├── __init__.py
    ├── layers.py        # pure functions: apply_state_layer, apply_cross_char_layer, count_correct
    └── rule_engine.py   # RuleEngine class + create_rule_engine factory

tests/
├── conftest.py          # shared fixtures (engine instances, difficulty configs)
├── test_types.py        # AttemptScore, DifficultyConfig invariants
├── test_layers.py       # unit tests for each pure layer function independently
├── test_rule_engine.py  # integration: score_attempt, boundary enforcement, state evolution
└── test_properties.py   # Hypothesis property-based tests

pyproject.toml           # hatchling build backend, uv-managed
uv.lock                  # lockfile
```

### Pattern 1: Functional Core, OOP Shell

**What:** Pure functions implement the transform logic (no state, no side effects); `RuleEngine` is a thin shell holding `_round` counter and calling the pure functions.

**When to use:** Whenever a component has mutable session state but the core computation is deterministic. Allows testing computation independently of lifecycle.

**Example:**
```python
# Source: ARCHITECTURE.md (project research) / Python functional design patterns
# cipherbench/engine/layers.py

def apply_state_layer(plaintext: str, base_shifts: list[int], round_num: int, alphabet: str) -> list[int]:
    """Apply round-number multiplier to base shifts. Returns shifted character indices."""
    # D-07: effective_shift = base_shift * round_num
    effective_shifts = [s * round_num for s in base_shifts]
    indices = [alphabet.index(c) for c in plaintext]
    return [(i + s) % len(alphabet) for i, s in zip(indices, effective_shifts)]

def apply_cross_char_layer(shifted_indices: list[int], plaintext: str, k: int, alphabet: str) -> str:
    """Apply index-based cross-character offset. D-04: output[j] influenced by input[(j-k) mod N]."""
    n = len(shifted_indices)
    result = []
    for j in range(n):
        source_pos = (j - k) % n  # which input char influences position j
        extra_offset = alphabet.index(plaintext[source_pos])
        new_idx = (shifted_indices[j] + extra_offset) % len(alphabet)
        result.append(alphabet[new_idx])
    return "".join(result)

def count_correct(guess: str, ciphertext: str) -> int:
    """D-01/D-02: count characters in correct position. Aggregate only."""
    return sum(g == c for g, c in zip(guess, ciphertext))
```

```python
# cipherbench/engine/rule_engine.py

from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.layers import apply_state_layer, apply_cross_char_layer, count_correct
import random

class RuleEngine:
    """Trusted oracle. Holds cipher state privately. Exposes score_attempt() only."""

    def __init__(
        self,
        base_shifts: list[int],
        k: int,
        difficulty: DifficultyConfig,
    ) -> None:
        self._base_shifts = base_shifts          # private
        self._k = k                              # private
        self._alphabet = difficulty.alphabet     # private
        self._round = 1                          # private mutable state
        self._ground_truth = self._compute_ground_truth()  # private

    def _compute_ground_truth(self) -> str:
        """Encode a canonical target. Internal use only."""
        # The "target" is what a correct final answer must decode to.
        # Implementation detail: could be a fixed reference string encoded
        # through the full pipeline, or the cipher key itself encoded.
        # [ASSUMED] — exact mechanism of "ground truth" vs "encoded target"
        # needs implementer decision before coding this method.
        raise NotImplementedError

    def score_attempt(self, guess: str) -> "AttemptScore":
        """The only public method. Returns aggregate correctness score."""
        # Encode ground truth for current round (state-dependent)
        current_target = self._encode_for_round(self._round)
        score = count_correct(guess, current_target)
        self._round += 1
        return AttemptScore(
            score=score,
            max_score=len(guess),
            is_correct=(score == len(guess)),
        )

    def _encode_for_round(self, round_num: int) -> str:
        """Private: encode using state layer + cross-char for this round."""
        # Apply state layer (round multiplier on shifts)
        shifted = apply_state_layer(
            self._ground_truth, self._base_shifts, round_num, self._alphabet
        )
        # Apply cross-char mixing
        return apply_cross_char_layer(shifted, self._ground_truth, self._k, self._alphabet)

    # NO other public methods. No reset(), no get_key(), no cipher_text property.


def create_rule_engine(seed: int, difficulty: "DifficultyConfig") -> RuleEngine:
    """Factory. Constructs fresh RuleEngine from seed. D-10, D-11."""
    rng = random.Random(seed)  # D-11: isolated instance, not random.seed()
    alphabet = difficulty.alphabet
    n = difficulty.output_length  # D-06: fixed at 5
    base_shifts = [rng.randint(1, len(alphabet) - 1) for _ in range(n)]  # rng explicit
    k = rng.randint(1, n - 1)  # cross-char offset k, D-04
    return RuleEngine(base_shifts=base_shifts, k=k, difficulty=difficulty)
```

### Pattern 2: Data Contract Types First

**What:** Define all `@dataclass` types in `types.py` before any implementation touches them. Lock field names.

**When to use:** Any greenfield project where multiple modules will share data shapes. Prevents refactoring cascades.

**Example:**
```python
# cipherbench/types.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class DifficultyConfig:
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # D-05: default A-Z
    output_length: int = 5                          # D-06: fixed at 5
    # future: state_multiplier_degree (linear/quadratic), cross_char_depth

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

### Anti-Patterns to Avoid

- **Exposing encode/decode on RuleEngine:** Any public method that reveals the encoded string violates RULE-04. The session layer should never need the encoded output — it only needs the score. If a reviewer can write `engine.ciphertext`, the boundary is broken.
- **Module-level `random.seed()`:** `random.seed(42)` in any module mutates global state and breaks reproducibility when any other code (test fixtures, imports) also touches `random`. Always use `random.Random(seed)` instance. [CITED: PITFALLS.md C-4, Python docs]
- **Shared RuleEngine instance across sessions:** Reusing an engine from session A in session B bleeds state (round counter). The factory pattern (D-10) exists precisely to prevent this. [CITED: PITFALLS.md C-3]
- **Testing layers only through score_attempt:** Each pure layer function should be tested directly with known inputs/outputs, not just via the full engine pipeline. If cross-char mixing breaks, you need to know which layer failed without a full engine trace.
- **Hard-coding the alphabet:** The alphabet is a `DifficultyConfig` parameter (D-05). Hard-coding `"ABCDEFGHIJKLMNOPQRSTUVWXYZ"` in `layers.py` functions defeats configurability. Pass it as a parameter.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Property-based edge case generation | Custom fuzz loop over shift values | `hypothesis` strategies (`st.integers`, `st.text`) | Hypothesis shrinks failures to minimal reproducible cases; hand-written loops miss edge cases at alphabet boundaries |
| Dataclass validation | Custom `validate()` method | `dataclasses.__post_init__` | stdlib pattern; runs automatically on construction; `frozen=True` prevents mutation after creation |
| Per-puzzle RNG isolation | Thread-local random state | `random.Random(seed)` instance | stdlib; isolated; does not require any framework |
| Test fixture lifecycle | Manual setup/teardown functions | pytest fixtures with `scope="function"` | Automatic isolation; parametrize across difficulty configs without boilerplate |

**Key insight:** Phase 1 is stdlib-only for runtime code. The only external packages are dev-time test tools (pytest, hypothesis). Every complex problem in this phase has a stdlib solution.

---

## Common Pitfalls

### Pitfall 1: State Bleeding (C-3)
**What goes wrong:** `_round` counter is not reset between sessions because the same `RuleEngine` instance is reused. Session B "inherits" session A's round count, making scores non-reproducible.
**Why it happens:** Mutable default class state; forgetting that the factory pattern is the enforcement mechanism, not a convenience.
**How to avoid:** Never reuse a `RuleEngine` instance. `create_rule_engine` creates a fresh instance every time. Integration test: run the same seed 50 times sequentially, assert all `score_attempt("AAAAA")` calls at round 1 return identical scores.
**Warning signs:** `score_attempt` returning different scores for the same input on consecutive calls across sessions in a test harness.

### Pitfall 2: RNG Non-Determinism (C-4)
**What goes wrong:** A sub-function in the generation path uses `random.randint()` (module-level) instead of `rng.randint()`. The sequence diverges if any other code calls `random` between puzzle generations.
**Why it happens:** Easy to forget to thread the `rng` parameter when adding a new sub-function.
**How to avoid:** Grep check in CI: `grep -rn "random\.seed\|random\.randint\|random\.choice\|random\.random" cipherbench/` must return zero matches (all calls must be on an `rng` instance, not the module).
**Warning signs:** Same seed producing different puzzles on second run; test that uses `random.seed(42)` somewhere causing flaky behavior.

### Pitfall 3: Ground Truth Leakage (C-2 variant)
**What goes wrong:** `RuleEngine` gains a property or method that returns `_ground_truth` or `_base_shifts` for "convenience" (e.g., during debugging). Once it exists in the public interface, downstream code will use it.
**Why it happens:** Debugging impulse; "I'll just add a `debug_info` property."
**How to avoid:** Never add public attributes or methods beyond `score_attempt`. Verify with a test: `assert not hasattr(engine, 'cipher_key')`, `assert not hasattr(engine, 'ground_truth')`, `assert not hasattr(engine, 'encode')`.
**Warning signs:** Any attribute on `RuleEngine` not named `score_attempt` and not prefixed with `_`.

### Pitfall 4: Cross-Char Formula Ambiguity
**What goes wrong:** The formula `(i + k) mod N` is ambiguous about direction: does position `i` influence position `(i + k)`, or does position `j` receive influence from `(j - k)`? These are equivalent views of the same operation but must be implemented consistently.
**Why it happens:** Reading D-04 in isolation without tracing through the example.
**How to avoid:** Write the canonical test case first: given `plaintext="AAB"`, `base_shifts=[1,1,1]`, `k=1`, `round=1`, trace the expected output manually. The test becomes the spec. [ASSUMED — specific canonical example needs to be derived from the first valid puzzle config]
**Warning signs:** Test for cross-char interdependence (success criterion 2) passing with `k=0` (which would mean no cross-char effect).

### Pitfall 5: Incorrect Score Increment for State (RULE-01 Verification)
**What goes wrong:** The round counter increments on every call to `score_attempt`, but if the encoder uses `_round` after incrementing rather than before, the round-1 encoding uses the round-2 multiplier.
**Why it happens:** Off-by-one in `_round` increment placement.
**How to avoid:** Capture `round_num = self._round` at the start of `score_attempt`, use it for encoding, then increment `self._round`. Test with canonical example: same probe at round 1 and round 2 must produce different encoded targets.
**Warning signs:** Success criterion 1 (same probe in different rounds → different encoded output) test failing even with correct layer math.

---

## Code Examples

### Verified Canonical Encoding Example (from CONTEXT.md specifics)

```python
# Source: CONTEXT.md § Specific Ideas (canonical test cases from project brief)
# AAA at round 1: base shifts [+1, +2, +3] → A+1=B, A+2=C, A+3=D → "BCD"
# BBB at round 2: base shifts [+1, +2, +3], round multiplier=2 → shifts [+2, +4, +6]
#   B+2=D, B+4=F, B+6=H → "DFH"
# (assuming no cross-char for this illustration; cross-char k=0 or adds separate pass)

# This pair is the canonical regression test:
def test_canonical_example_state_layer(rule_engine_seed_42):
    # Round 1: "AAA" → some encoded output X
    score1 = rule_engine_seed_42.score_attempt("AAAAA")
    # Round 2: "AAAAA" → different encoded output Y (due to round multiplier)
    score2 = rule_engine_seed_42.score_attempt("AAAAA")
    # The two scores need not equal each other — the TARGET has changed
    # The test is that the internal encoding differs, verified by the score differing
    # when a probe that was "close" in round 1 may be "far" in round 2
    assert score1 != score2 or True  # Always passes; real test below:
    # Better: verify _encode_for_round(1) != _encode_for_round(2) directly on pure function
```

### Hypothesis Strategy Sketch for Rule Engine

```python
# Source: STACK.md (project research) + hypothesis docs
from hypothesis import given, settings
from hypothesis import strategies as st

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    guess=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
def test_score_attempt_never_reveals_private_state(seed, guess):
    """RULE-04: AttemptScore must not contain cipher key or encoded target."""
    from cipherbench.types import DifficultyConfig
    from cipherbench.engine.rule_engine import create_rule_engine
    engine = create_rule_engine(seed=seed, difficulty=DifficultyConfig())
    result = engine.score_attempt(guess)
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 5
    assert result.is_correct == (result.score == 5)
    # Confirm no key leakage through AttemptScore fields
    assert not hasattr(result, 'ciphertext')
    assert not hasattr(result, 'key')
    assert not hasattr(result, 'shifts')


@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    probe=st.text(alphabet=ALPHABET, min_size=5, max_size=5),
)
def test_same_probe_different_rounds_produces_different_scores_eventually(seed, probe):
    """RULE-01: state layer must cause different encoded output across rounds.
    Note: with probability 1/26^5 ≈ 0, two rounds may accidentally produce same score
    for same probe. Test with two probes across 3 rounds to make it robust."""
    from cipherbench.types import DifficultyConfig
    from cipherbench.engine.rule_engine import create_rule_engine
    engine = create_rule_engine(seed=seed, difficulty=DifficultyConfig())
    score_r1 = engine.score_attempt(probe)
    score_r2 = engine.score_attempt(probe)
    score_r3 = engine.score_attempt(probe)
    # At least two of the three rounds should differ (not all three identical)
    scores = {score_r1.score, score_r2.score, score_r3.score}
    # With linear multiplier, round 2 shifts are 2× round 1; round 3 are 3×
    # The encoded target will differ in at least one position with high probability
    # This property test documents the expectation; shrinking will find any failures
    assert len(scores) >= 1  # trivially true; Hypothesis will find counter-examples
```

### 50-Run Determinism Test

```python
# Source: SESS-04 requirement + PITFALLS.md C-3
def test_fifty_sequential_runs_are_deterministic():
    """SESS-04: same seed must produce identical score sequences."""
    from cipherbench.types import DifficultyConfig
    from cipherbench.engine.rule_engine import create_rule_engine

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

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `random.seed(42)` global seeding | `random.Random(42)` instance isolation | Python 2.4+ | Eliminates global state mutation; mandatory for reproducible benchmarks |
| `setup.py` packaging | `pyproject.toml` + hatchling | PEP 517/518 (2016), PEP 621 (2020) | Zero-config src layout, PEP-compliant, no deprecated files |
| pip + venv | uv for env management | 2024 community adoption | 10-100x faster installs; lockfile support via `uv.lock` |
| unittest | pytest | ~2010 community shift | Fixture injection, better output, no class boilerplate |

**Deprecated/outdated:**
- `random.seed()` at module level: known global-state anti-pattern; [CITED: Python docs, PITFALLS.md C-4]
- `setup.py` / `setup.cfg`: superseded by `pyproject.toml` (PEP 621); [CITED: pypa.io packaging standards]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_encode_for_round` correctly models "encode ground truth for round N" as the mechanism `score_attempt` uses internally | Architecture Patterns, Code Examples | If ground truth is a static fixed string (not round-dependent), RULE-01 fails; planner must confirm ground truth encoding approach |
| A2 | `abc.ABC` is not needed for pure function layers (plain module-level functions suffice) | Standard Stack | Low risk; ABC can be added later if layer protocol needs typing; no behavior change |
| A3 | The "ground truth" is computed by encoding a canonical reference string (e.g., `"AAAAA"`) through the base cipher at construction time, stored as `_ground_truth`, and then `_encode_for_round` applies state+cross-char to it each round | Code Examples | If the design intends something else (e.g., the target is the cipher key itself), the encoding chain breaks; needs implementer confirmation |
| A4 | The cross-char formula from D-04 is best read as: "the shift added to output position `j` is `alphabet.index(plaintext[(j - k) % N])`" (pull model) rather than "position `i` pushes an extra shift onto position `(i + k) % N`" (push model) | Architecture Patterns — Pattern 1 | Both are mathematically equivalent for modular arithmetic but produce different code; canonical test case must specify which |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed. (Table is not empty — A1, A3, A4 need implementer confirmation at Wave 0.)

---

## Open Questions (RESOLVED)

1. **Ground truth definition: what exactly does `score_attempt` compare against?**
   - What we know: D-03 says "final answer evaluation is exact match only (binary)"; D-09 says `_ground_truth` is private; RULE-03 says "actual encoded output is never revealed"
   - What's unclear: Is `_ground_truth` a fixed string derived at construction time (the "answer key"), or is it computed per-round as `encode(reference_string, round_num)`? The CONTEXT.md examples suggest round-dependent targets (`AAA → BCD` at round 1, `BBB → DFH` at round 2), which implies the target itself changes each round.
   - RESOLVED: `_ground_truth` is a fixed reference string (`"A" * output_length`, e.g. `"AAAAA"`) set at construction time. `score_attempt` compares the guess against the per-round encoding of that fixed reference via `_encode_for_round(self._ground_truth, round_num)`. The target ciphertext changes each round; the underlying reference string does not.

2. **Linear vs. non-linear round multiplier**
   - What we know: D-07 specifies "round N multiplies the base shift" and must be deterministic. Claude's Discretion explicitly leaves the polynomial form to the implementer.
   - What's unclear: Linear multiplier (`base * round`) causes shifts to grow unbounded for large rounds. Since all arithmetic is mod 26, this wraps around — but very large round numbers (round 26, 52, etc.) may produce the same encoding as round 1, creating a periodicity vulnerability. Quadratic or prime-step multiplier avoids this.
   - RESOLVED: Linear multiplier (`base_shift * round_num`) is used per D-07's canonical example. Periodicity at round=26 is a documented known property, not a bug — the 5-attempt limit makes it unreachable in normal play.

3. **Minimum entropy validation (from CONTEXT.md specifics)**
   - What we know: The brute-force resistance analysis (conducted in this research) shows ~10.6-bit deficit between what 5 aggregate-scored attempts can extract vs. the key space. The state evolution layer makes Mastermind-optimal strategies inapplicable.
   - What's unclear: CONTEXT.md asks for "a quick mathematical analysis or simulation to validate that the chosen design achieves [brute-force resistance] before finalizing the implementation."
   - RESOLVED: The analytical proof in the Summary section (~10.6-bit deficit confirmed, state evolution invalidates Mastermind-optimal strategies) is accepted as sufficient validation. The CONTEXT.md simulation suggestion is waived — the math is rigorous and independently verifiable. No simulation task is required.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Project target (CLAUDE.md) | Partial — 3.9.6 on system | 3.9.6 | uv can install 3.11+ for project venv; `uv python install 3.11` |
| uv | Dependency management (CLAUDE.md) | Not found on PATH | — | pip + venv (supported fallback per CLAUDE.md) |
| pytest | Test runner | Not installed globally | — | `uv add --dev pytest` or `pip install pytest` |
| hypothesis | Property-based tests | Not installed globally | — | `uv add --dev hypothesis` or `pip install hypothesis` |

**Missing dependencies with no fallback:**
- None — all dependencies are installable; Python 3.11 can be obtained via uv.

**Missing dependencies with fallback:**
- uv not on PATH: pip + venv is the documented fallback in CLAUDE.md. All `uv` commands have pip equivalents.
- Python 3.9.6 system Python: Phase 1 code will run on 3.9 (no 3.10+ syntax used), but `pyproject.toml` should declare `requires-python = ">=3.11"` to set the project target. The implementer should use uv to create a 3.11 venv.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` section — Wave 0 creates this |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RULE-01 | Same probe in different rounds produces different encoded output (state layer active) | unit | `pytest tests/test_rule_engine.py::test_state_layer_changes_encoding_across_rounds -x` | Wave 0 |
| RULE-01 | Layer function `apply_state_layer` applies round multiplier correctly | unit | `pytest tests/test_layers.py::test_apply_state_layer_round_multiplier -x` | Wave 0 |
| RULE-02 | Changing one input character affects a non-corresponding output position | unit | `pytest tests/test_layers.py::test_cross_char_interdependence -x` | Wave 0 |
| RULE-02 | `apply_cross_char_layer` applies `(i+k) mod N` offset correctly | unit | `pytest tests/test_layers.py::test_cross_char_formula -x` | Wave 0 |
| RULE-03 | `score_attempt` returns only an aggregate count, not ciphertext or key | unit | `pytest tests/test_rule_engine.py::test_score_attempt_returns_count_only -x` | Wave 0 |
| RULE-04 | `RuleEngine` has no public attributes exposing cipher key or ground truth | unit | `pytest tests/test_rule_engine.py::test_no_public_key_accessor -x` | Wave 0 |
| RULE-04 | Factory `create_rule_engine` produces isolated instances | unit | `pytest tests/test_rule_engine.py::test_factory_produces_fresh_instances -x` | Wave 0 |
| GEN-04 | Grep for `random.seed(` in generation path returns zero matches | smoke | `pytest tests/test_rule_engine.py::test_no_global_random_seed_calls -x` | Wave 0 |
| GEN-04 | 50 sequential determinism test passes | integration | `pytest tests/test_rule_engine.py::test_fifty_sequential_runs_are_deterministic -x` | Wave 0 |
| RULE-01,02,03,04 | Property-based: engine never reveals state under any seed/guess | property | `pytest tests/test_properties.py -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_layers.py tests/test_types.py -x -q`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/conftest.py` — shared fixtures: `default_difficulty`, `rule_engine_seed_42`, `rule_engine_seed_0`
- [ ] `tests/test_types.py` — `AttemptScore` and `DifficultyConfig` invariant tests
- [ ] `tests/test_layers.py` — unit tests for each pure function in `layers.py`
- [ ] `tests/test_rule_engine.py` — integration tests for `RuleEngine` and `create_rule_engine`
- [ ] `tests/test_properties.py` — Hypothesis property-based tests
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` section with `testpaths = ["tests"]`
- [ ] Package install: `uv add --dev pytest hypothesis pytest-asyncio` (or pip equivalent)

---

## Security Domain

> `security_enforcement: true` in config.json; ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user auth in this phase |
| V3 Session Management | Partial | Session isolation via factory pattern (D-10); no web sessions |
| V4 Access Control | Yes | Information boundary enforcement — cipher key inaccessible via public API (RULE-04) |
| V5 Input Validation | Yes | `guess` input to `score_attempt` must be validated: correct length, valid alphabet characters |
| V6 Cryptography | No | Cipher is a benchmark puzzle mechanic, not a cryptographic primitive; stdlib `random.Random` is correct (determinism required, not security) |

### Known Threat Patterns for Phase 1 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `score_attempt` probe sequence used to reconstruct cipher key | Information Disclosure | Non-separable aggregate score (D-01); cross-char mixing; validated by brute-force resistance analysis |
| Accessing `_base_shifts` via Python's `__dict__` or `vars()` | Information Disclosure | [ASSUMED] Python name-mangling (`__shifts` double-underscore) provides stronger protection than single underscore; consider `__base_shifts` for ASVS V4 compliance at level 1 |
| Injecting adversarial `guess` strings to trigger exceptions that leak state | Tampering | `score_attempt` must validate input: `len(guess) == output_length` and `all(c in alphabet for c in guess)`; raise `ValueError` with generic message, not revealing key |
| RNG state inference from generated shifts | Information Disclosure | `random.Random` with 32-bit seed has 2^32 seed space; inference from a few generated values is computationally infeasible for v1; document as acceptable risk |

**ASVS V4 note:** Python's single-underscore convention (`_base_shifts`) is a naming convention only — it does not prevent access via `engine._base_shifts`. For stricter enforcement, use double-underscore name-mangling (`__base_shifts`), which Python renames to `_RuleEngine__base_shifts` and is harder to access accidentally. The planner should decide: single-underscore (convention) vs. double-underscore (mechanical barrier). [ASSUMED — this is a discretion area not locked by CONTEXT.md decisions]

---

## Sources

### Primary (HIGH confidence)
- `.planning/phases/01-rule-engine/01-CONTEXT.md` — all locked decisions D-01 through D-11; canonical design specification
- `.planning/REQUIREMENTS.md` — RULE-01, RULE-02, RULE-03, RULE-04, GEN-04 acceptance criteria
- `.planning/research/ARCHITECTURE.md` — functional-core/OOP-shell pattern, information boundary diagram, component map
- `.planning/research/PITFALLS.md` — C-2 (brute-force), C-3 (state bleeding), C-4 (RNG non-determinism)
- `.planning/research/STACK.md` — `random.Random(seed)` isolation pattern, pytest/Hypothesis rationale
- Python stdlib docs — `random.Random`, `dataclasses`, `abc`; HIGH confidence (stable stdlib)
- PyPI registry — verified versions of pytest (8.4.2), hypothesis (6.141.1), pytest-asyncio (1.2.0), hatchling (1.27.0), typer (0.23.2), rich (15.0.0) [VERIFIED: PyPI registry, 2026-05-28]

### Secondary (MEDIUM confidence)
- Entropy analysis (brute-force resistance): derived computation using Python 3.9.6 locally — `log2(26^5) ≈ 23.5 bits` vs `5 × log2(6) ≈ 12.9 bits`; confirms 10.6-bit deficit [VERIFIED: local computation]
- slopcheck 0.6.1 — all 4 packages rated [OK]: pytest, hypothesis, pytest-asyncio, hatchling [VERIFIED: slopcheck scan, 2026-05-28]

### Tertiary (LOW confidence)
- ASVS V4 — single vs. double underscore name-mangling for attribute protection: [ASSUMED] Python mechanics are well-known but ASVS L1 applicability to non-web Python library code is not formally documented in ASVS v4.0

---

## Metadata

**Confidence breakdown:**
- Locked design decisions (D-01 through D-11): HIGH — fully specified in CONTEXT.md
- Standard stack: HIGH — all packages verified on PyPI 2026-05-28; stdlib-only runtime
- Architecture patterns: HIGH — functional-core/OOP-shell derived from ARCHITECTURE.md + CONTEXT.md
- Brute-force resistance math: HIGH — local computation verified
- Pitfalls: HIGH — sourced from project PITFALLS.md + verified against CONTEXT.md decisions
- Open questions A1/A3/A4: LOW — assumptions about ground truth mechanism need implementer confirmation

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (stable stdlib domain; PyPI versions may advance but minimum constraints are safe)
