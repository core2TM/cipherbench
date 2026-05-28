# Phase 2: Puzzle Generator - Research

**Researched:** 2026-05-29
**Domain:** Python dataclass extension, SHA-256 hashing, seeded RNG, frozen dataclasses
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Extend `DifficultyConfig` in-place in `cipherbench/types.py` — add two optional fields with defaults. `DifficultyConfig()` with all defaults preserves Phase 1 behavior exactly. `create_rule_engine()` must be updated to read these fields instead of sampling them from the RNG.
- **D-02:** Add `state_change_rate: float = 1.0` to `DifficultyConfig`. Round multiplier formula changes from `base_shift * round_num` to `base_shift * (round_num * state_change_rate)`. Default `1.0` preserves current linear behavior exactly.
- **D-03:** Add `cross_char_depth: int = 1` to `DifficultyConfig`. Depth 1 = k in `[1, n-1]` (current single-offset behavior). Depth 2+ = multiple simultaneous cross-char offset links applied. The planner determines the exact multi-depth mechanism.
- **D-04:** `Puzzle` is a frozen dataclass in `cipherbench/puzzle.py` with fields: `seed: int`, `difficulty: DifficultyConfig`, `puzzle_hash: str`.
- **D-05:** `Puzzle` has a `create_engine() -> RuleEngine` method that calls `create_rule_engine(self.seed, self.difficulty)`. Phase 3 calls `puzzle.create_engine()` per session — never reuses an engine across sessions.
- **D-06:** Both `Puzzle` and `generate_puzzle()` live in `cipherbench/puzzle.py`. Import path: `from cipherbench.puzzle import Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD`.
- **D-07:** Hash computed from derived state: `base_shifts` (list of ints) + `k_list` (list of ints) + `ground_truth` (str) — the actual values produced by `create_rule_engine()` for the given seed + difficulty.
- **D-08:** Hash function: `hashlib.sha256().hexdigest()` — stdlib, no dependency.
- **D-09:** Verification via standalone `verify_puzzle(puzzle: Puzzle) -> None` that raises `ValueError('hash mismatch: expected {X}, got {Y}')` on mismatch.
- **D-10:** `EASY`, `MEDIUM`, `HARD` as module-level `DifficultyConfig` constants in `cipherbench/puzzle.py`.
- **D-11:** All three axes vary across tiers. Planner picks specific parameter values.
- **D-12:** Tier NOT stored in `Puzzle`. Standalone `get_tier(difficulty: DifficultyConfig) -> str` returns `'easy'`/`'medium'`/`'hard'`/`'custom'`.

### Claude's Discretion

- Exact parameter values for EASY/MEDIUM/HARD presets.
- Exact mechanism for `cross_char_depth > 1`.
- The canonical serialization format for hashing.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GEN-01 | Generator produces a reproducible puzzle from an integer seed — same seed always yields the same puzzle regardless of environment | `random.Random(seed)` isolated instance; `rng.sample(range(1,n), depth)` proved equivalent to `rng.randint(1,n-1)` for depth=1 across 1000 seeds; all derived values are deterministic integers |
| GEN-02 | Generator computes and stores a hash of the fully-rendered puzzle at creation; replaying the same seed asserts the same hash | `hashlib.sha256()` with `json.dumps(..., sort_keys=True).encode()` serialization; verified stable and cross-platform for integer and string JSON values |
| GEN-03 | Generator exposes configurable difficulty parameters that control puzzle complexity | `state_change_rate` and `cross_char_depth` added to `DifficultyConfig`; EASY/MEDIUM/HARD tiers produce 100K / 11.8M / 60.5M search space respectively with structurally distinct mixing depths |
</phase_requirements>

---

## Summary

Phase 2 builds the puzzle generation layer on top of the Phase 1 rule engine. The core work is: extend `DifficultyConfig` with two new fields, add a new pure function to `layers.py` for multi-depth cross-character mixing, update `create_rule_engine()` to consume the new fields instead of sampling them, and create `cipherbench/puzzle.py` with the `Puzzle` frozen dataclass, `generate_puzzle()` factory, `verify_puzzle()` integrity checker, and `EASY`/`MEDIUM`/`HARD` tier constants.

All required mechanisms are stdlib-only: `hashlib.sha256`, `json.dumps`, `random.Random`. No new dependencies are needed. The key implementation insight is that `rng.sample(range(1, n), depth)` is call-count-equivalent to `rng.randint(1, n-1)` for depth=1 — verified across 1000 seeds — so switching to the `sample`-based approach for `k_list` generation preserves all 47 existing Phase 1 tests without modification.

The `apply_state_layer` signature gains an optional `state_change_rate: float = 1.0` parameter and the effective-shift formula changes to `int(s * round_num * state_change_rate)`. At the default rate of 1.0 this produces bit-identical results to the current implementation for all integer base_shifts and round_nums — verified exhaustively. For cross-char depth > 1 the recommended mechanism is additive multi-source injection: for each output position `j`, iterate over all k values in `k_list` and accumulate the extra offsets — the existing `apply_cross_char_layer_multi` is a new function added alongside (not replacing) the existing `apply_cross_char_layer` to preserve all 16 Phase 1 layer tests.

**Primary recommendation:** Keep the Phase 1 layer and engine interfaces backward-compatible by adding new functions/parameters with safe defaults. All 47 existing tests must continue to pass after the Phase 2 changes are applied.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Puzzle state derivation | Engine layer (`create_rule_engine`) | — | The factory is the single source of truth for `base_shifts`, `k_list`, `ground_truth` |
| Puzzle identity / hash | Generator layer (`puzzle.py`) | Engine layer (derives the state to be hashed) | `generate_puzzle()` calls `create_rule_engine()` internally, extracts private state via trusted factory access, then hashes |
| Difficulty configuration | Data layer (`types.py`) | Generator layer (tier constants) | `DifficultyConfig` is the shared data contract; `puzzle.py` defines EASY/MEDIUM/HARD as instances of it |
| Reproducibility enforcement | Generator layer (`verify_puzzle`) | — | `verify_puzzle()` re-derives hash from seed+difficulty and asserts equality |
| Tier classification | Generator layer (`get_tier`) | Scoring layer (Phase 4 calls it) | Pure lookup function; lives where the tier constants are defined |

---

## Standard Stack

### Core (stdlib only — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hashlib` (stdlib) | n/a | SHA-256 puzzle hash | Zero-dependency, reproducible hex string output [VERIFIED: Python stdlib] |
| `json` (stdlib) | n/a | Canonical serialization for hash input | Deterministic key ordering with `sort_keys=True`; safe for int + str values [VERIFIED: Python stdlib] |
| `dataclasses` (stdlib) | n/a | `Puzzle` frozen dataclass | Consistent with `DifficultyConfig` and `AttemptScore` from Phase 1 [VERIFIED: Python stdlib] |
| `random.Random(seed)` (stdlib) | n/a | RNG isolation | Already used in Phase 1; `rng.sample()` added for `k_list` generation [VERIFIED: Python stdlib] |

### No New Dependencies

This phase introduces no new PyPI packages. `pyproject.toml` does not need updating.

---

## Package Legitimacy Audit

> No external packages are introduced in this phase. All functionality uses Python stdlib.

No audit required — zero new installs.

---

## Architecture Patterns

### System Architecture Diagram

```
Integer seed + DifficultyConfig
        │
        ▼
generate_puzzle(seed, difficulty)
        │
        ├─── create_rule_engine(seed, difficulty)
        │         │
        │         ├── rng = random.Random(seed)
        │         ├── base_shifts = [rng.randint(...) × n]
        │         ├── k_list = rng.sample(range(1,n), depth)  ← NEW
        │         └── ground_truth = alphabet[0] * n
        │                   │
        │                   └── returns RuleEngine (private state)
        │
        ├─── extract derived state from engine._base_shifts, ._k_list, ._ground_truth
        │
        ├─── compute hash: sha256(json.dumps({base_shifts, k_list, ground_truth}, sort_keys=True))
        │
        └─── return Puzzle(seed=seed, difficulty=difficulty, puzzle_hash=hash)


verify_puzzle(puzzle)
        │
        ├─── re-run generate_puzzle(puzzle.seed, puzzle.difficulty)
        └─── assert new_hash == puzzle.puzzle_hash  (raises ValueError on mismatch)


Puzzle.create_engine()  → create_rule_engine(self.seed, self.difficulty)
                                    (used by Phase 3 SessionRunner)


get_tier(difficulty)
        ├─── if difficulty == EASY  → 'easy'
        ├─── if difficulty == MEDIUM → 'medium'
        ├─── if difficulty == HARD  → 'hard'
        └─── else                   → 'custom'
```

### Recommended Project Structure

```
cipherbench/
├── types.py          # DifficultyConfig extended in-place (state_change_rate, cross_char_depth)
├── puzzle.py         # NEW: Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD
├── engine/
│   ├── layers.py     # apply_state_layer (rate param added), apply_cross_char_layer_multi (NEW)
│   └── rule_engine.py # create_rule_engine updated (k_list, rate), RuleEngine updated (_k_list)
tests/
├── unit/
│   ├── test_engine/
│   │   ├── test_types.py           # existing — add tests for new DifficultyConfig fields
│   │   ├── test_layers.py          # existing — add tests for apply_cross_char_layer_multi
│   │   └── test_rule_engine.py     # existing — confirm backward compat
│   └── test_puzzle/
│       ├── __init__.py
│       └── test_puzzle.py          # NEW: all puzzle.py tests
└── test_properties.py              # existing — add Hypothesis test for verify_puzzle
```

### Pattern 1: DifficultyConfig Extension with Validation (D-01 to D-03)

**What:** Add two optional fields to the existing frozen dataclass with `__post_init__` validation. No existing fields change.

**When to use:** Any time a new configurability axis is added without breaking backward compat.

**Example:**
```python
# Source: Python stdlib dataclasses documentation [VERIFIED: Python stdlib]
@dataclass(frozen=True)
class DifficultyConfig:
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    output_length: int = 5
    state_change_rate: float = 1.0   # NEW D-02
    cross_char_depth: int = 1        # NEW D-03

    def __post_init__(self) -> None:
        if len(self.alphabet) < 2:
            raise ValueError("alphabet must have at least 2 characters")
        if self.output_length < 1:
            raise ValueError("output_length must be positive")
        # NEW validations:
        if self.state_change_rate <= 0.0:
            raise ValueError("state_change_rate must be positive")
        if not (1 <= self.cross_char_depth <= self.output_length - 1):
            raise ValueError(
                f"cross_char_depth must be in [1, output_length-1="
                f"{self.output_length - 1}], got {self.cross_char_depth}"
            )
```

**Backward compat proof:** `DifficultyConfig()` still produces `alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"`, `output_length=5`, `state_change_rate=1.0`, `cross_char_depth=1`. All 11 existing test_types.py tests still pass. [VERIFIED: manual code analysis]

### Pattern 2: Multi-Depth Cross-Character Layer (D-03 mechanism)

**What:** For each output position `j`, iterate over all `k` values in `k_list` and accumulate the extra offsets additively. Depth 1 with `k_list=[k]` produces bit-identical output to the current single-k implementation.

**When to use:** `cross_char_depth > 1` — add this as a new function `apply_cross_char_layer_multi` in `layers.py`. The existing `apply_cross_char_layer(k: int)` function is unchanged.

**Why additive multi-source:** The pull-model formula `source_pos = (j - k) % n` is already well-defined for single k. Applying it additively for each k in `k_list` is deterministic, testable in isolation, and each additional k contributes one new information-theoretic coupling that makes position isolation harder.

**Why not sequential application (call apply_cross_char_layer twice):** Sequential application with the same plaintext would not add new coupling because the second pass's `extra_offset` is drawn from the same `plaintext` string (the original probe), not from the intermediate result. The additive approach is conceptually cleaner.

**Example:**
```python
# Source: derived from existing apply_cross_char_layer in layers.py [VERIFIED: codebase]
def apply_cross_char_layer_multi(
    shifted_indices: list,
    plaintext: str,
    k_list: list,
    alphabet: str,
) -> str:
    """Apply cross-character offset injection with multiple k values (D-03, depth>1).

    For each output position j, accumulates extra offsets from each k in k_list.
    depth=1 (k_list=[k]) produces identical output to apply_cross_char_layer(k=k).
    """
    n = len(shifted_indices)
    result = []
    for j in range(n):
        base = shifted_indices[j]
        for k in k_list:
            source_pos = (j - k) % n
            extra_offset = alphabet.index(plaintext[source_pos])
            base = (base + extra_offset) % len(alphabet)
        result.append(alphabet[base])
    return "".join(result)
```

**Invariant verified:** `apply_cross_char_layer_multi([0,0,0], "ABC", [1], ALPHA) == apply_cross_char_layer([0,0,0], "ABC", 1, ALPHA) == "CAB"`. [VERIFIED: simulation in this research session]

### Pattern 3: k_list Sampling (create_rule_engine update)

**What:** Replace `k = rng.randint(1, n - 1)` with `k_list = rng.sample(range(1, n), difficulty.cross_char_depth)`.

**Key verification:** `rng.sample(range(1, n), 1)` produces the same result as `rng.randint(1, n-1)` for the same RNG state. Verified across 1000 seeds — zero mismatches. This means switching to `sample` for depth=1 is a zero-impact change to all existing Phase 1 tests.

**Why `rng.sample` over generating k values with individual `randint` calls:** `rng.sample` guarantees distinctness (no repeated k values in `k_list`) in a single call, avoiding any loop logic. Distinct k values are required — two identical k values in `k_list` would waste a coupling step.

**Max depth constraint:** `output_length=5` means valid k values are `{1, 2, 3, 4}`. Maximum possible distinct values = `output_length - 1 = 4`. The `__post_init__` validation in `DifficultyConfig` enforces `cross_char_depth <= output_length - 1`.

```python
# In create_rule_engine, replace:
# k = rng.randint(1, n - 1)
# With:
k_list = rng.sample(range(1, n), difficulty.cross_char_depth)
```

### Pattern 4: State Change Rate in apply_state_layer

**What:** Add `state_change_rate: float = 1.0` parameter to `apply_state_layer`. Formula changes from `s * round_num` to `int(s * round_num * state_change_rate)`.

**Why `int()` truncation, not `round()`:** `int()` is unconditional floor-toward-zero truncation, which is deterministic and platform-independent. Python's `round()` uses banker's rounding (round-half-to-even) which can differ from integer truncation at exactly half-integer values (e.g., `int(4.5) == 4` vs `round(4.5) == 4` via banker's, but `round(3.5) == 4` vs `int(3.5) == 3`). For a reproducible cipher, deterministic truncation is required.

**Backward compat proof:** For `state_change_rate=1.0` and integer `s`, `round_num`: `int(s * round_num * 1.0) == s * round_num` for all values tested (s in [1,25], round_num in [1,5]). [VERIFIED: exhaustive check in this research session]

**Signature update:**
```python
def apply_state_layer(
    plaintext: str,
    base_shifts: list,
    round_num: int,
    alphabet: str,
    state_change_rate: float = 1.0,   # NEW — default preserves existing behavior
) -> list:
    effective_shifts = [int(s * round_num * state_change_rate) for s in base_shifts]
    indices = [alphabet.index(c) for c in plaintext]
    return [(idx + eff) % len(alphabet) for idx, eff in zip(indices, effective_shifts)]
```

### Pattern 5: RuleEngine Private State Update

**What:** `RuleEngine.__init__` accepts `k_list: list` instead of `k: int`. Stores `self._k_list` and `self._state_change_rate` (needed for `_encode_for_round`). The `_encode_for_round` method calls `apply_state_layer` with the rate, and `apply_cross_char_layer_multi` with `k_list`.

**Backward compat for existing tests:** The `test_cipher_key_not_accessible` test checks that `engine` does NOT have a public attribute `base_shifts` or `encode`. It does NOT check for `_k` or `_k_list` by name. The `test_no_public_key_accessor` checks that the only public method is `score_attempt`. Neither test is broken by renaming `_k` to `_k_list` or adding `_state_change_rate`. [VERIFIED: test code review]

**Key note:** `difficulty` is not currently stored as a full attribute on `RuleEngine` — only `difficulty.alphabet` is stored as `self._alphabet`. Phase 2 requires also storing `state_change_rate` and `k_list` as private attributes. The cleanest approach: store `self._k_list = k_list` and `self._state_change_rate = difficulty.state_change_rate`.

### Pattern 6: Puzzle Frozen Dataclass and generate_puzzle

**What:** `Puzzle` is a frozen dataclass. `generate_puzzle()` calls `create_rule_engine()` internally, extracts derived state from the engine's private attributes (trusted factory access), computes the SHA-256 hash, and returns an immutable `Puzzle`.

**Trusted factory access:** `generate_puzzle()` is a trusted factory function (not external caller code). Accessing `engine._base_shifts`, `engine._k_list`, `engine._ground_truth` within this function is intentional and consistent with the Phase 1 "single-underscore for convention, not mechanical barrier" decision.

**Example:**
```python
# Source: stdlib dataclasses, hashlib, json [VERIFIED: Python stdlib]
import hashlib, json
from dataclasses import dataclass
from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine, RuleEngine

@dataclass(frozen=True)
class Puzzle:
    seed: int
    difficulty: DifficultyConfig
    puzzle_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if not self.puzzle_hash:
            raise ValueError("puzzle_hash must be non-empty")

    def create_engine(self) -> RuleEngine:
        """Return a fresh RuleEngine for this puzzle's seed + difficulty."""
        return create_rule_engine(self.seed, self.difficulty)


def _derive_hash(engine) -> str:
    """Compute SHA-256 hash of the engine's derived state (internal helper)."""
    payload = json.dumps(
        {
            "base_shifts": engine._base_shifts,
            "ground_truth": engine._ground_truth,
            "k_list": engine._k_list,
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def generate_puzzle(seed: int, difficulty: DifficultyConfig = None) -> Puzzle:
    if difficulty is None:
        difficulty = DifficultyConfig()
    engine = create_rule_engine(seed, difficulty)
    puzzle_hash = _derive_hash(engine)
    return Puzzle(seed=seed, difficulty=difficulty, puzzle_hash=puzzle_hash)


def verify_puzzle(puzzle: Puzzle) -> None:
    """Re-derive hash and assert it matches stored hash. Raises ValueError on mismatch."""
    engine = create_rule_engine(puzzle.seed, puzzle.difficulty)
    expected = _derive_hash(engine)
    if expected != puzzle.puzzle_hash:
        raise ValueError(
            f"hash mismatch: expected {expected}, got {puzzle.puzzle_hash}"
        )
```

### Pattern 7: Canonical Hash Serialization

**What:** `json.dumps({"base_shifts": ..., "ground_truth": ..., "k_list": ...}, sort_keys=True).encode()`

**Why JSON with `sort_keys=True`:** Python's `json.dumps` with `sort_keys=True` produces deterministic key ordering across all Python versions and platforms for integer and string values. No float formatting concerns because `base_shifts` (list of ints), `k_list` (list of ints), and `ground_truth` (str) are all JSON-safe types without float ambiguity. [VERIFIED: empirical test in this research session]

**Verified output example:**
```
Input: {"base_shifts": [21, 4, 1, 24, 9], "k_list": [2], "ground_truth": "AAAAA"}
JSON string (sort_keys=True): '{"base_shifts": [21, 4, 1, 24, 9], "ground_truth": "AAAAA", "k_list": [2]}'
SHA-256: 1a7a949f36bd9887... (64-char hex)
```

**Why not `repr()` or `str()`:** Python's `repr()` and `str()` for lists and dicts do not guarantee ordering across Python versions. JSON with `sort_keys=True` is a cross-version contract.

### Pattern 8: Difficulty Tier Constants (D-10 to D-12)

**Recommended parameters (Claude's Discretion — see analysis below):**

```python
# Source: complexity analysis in this research session [VERIFIED: simulation]
EASY = DifficultyConfig(
    alphabet="ABCDEFGHIJ",        # 10 chars
    output_length=5,
    state_change_rate=1.0,
    cross_char_depth=1,
)

MEDIUM = DifficultyConfig(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",  # 26 chars (A-Z)
    output_length=5,
    state_change_rate=1.5,
    cross_char_depth=2,
)

HARD = DifficultyConfig(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",  # 36 chars (A-Z + 0-9)
    output_length=5,
    state_change_rate=2.0,
    cross_char_depth=3,
)
```

**Measurably distinct complexity (GEN-03):**

| Tier | Alphabet Size | Search Space | Entropy (bits) | Depth | Rate |
|------|--------------|-------------|----------------|-------|------|
| EASY | 10 | 100,000 | 16.6 | 1 | 1.0 |
| MEDIUM | 26 | 11,881,376 | 23.5 | 2 | 1.5 |
| HARD | 36 | 60,466,176 | 25.8 | 3 | 2.0 |

All three axes change together, producing quantitative (119x search space jump from EASY to MEDIUM) and qualitative (cross-char coupling depth) differences. [VERIFIED: simulation in this research session]

**`get_tier` implementation:**
```python
def get_tier(difficulty: DifficultyConfig) -> str:
    if difficulty == EASY:
        return "easy"
    if difficulty == MEDIUM:
        return "medium"
    if difficulty == HARD:
        return "hard"
    return "custom"
```

`DifficultyConfig` is a frozen dataclass, so `==` uses `dataclass`-generated equality (field-by-field comparison). Two configs with identical fields compare equal. [VERIFIED: Python stdlib dataclasses documentation]

### Anti-Patterns to Avoid

- **Global `random.seed()` in `generate_puzzle()`:** Not applicable — `create_rule_engine()` already uses isolated `rng`. `generate_puzzle()` must not call `random.seed()` either. [VERIFIED: GEN-04 source inspection tests cover this]
- **Hashing `seed + difficulty` as inputs:** This only proves round-trip identity, not derivation stability. A platform-specific RNG implementation difference would not be caught. Hash the derived state (D-07). [VERIFIED: CONTEXT.md D-07 rationale]
- **Using `repr()` or `str()` for hash serialization:** Non-deterministic across Python versions for dicts/lists. Use `json.dumps(sort_keys=True)`.
- **Sequential application of apply_cross_char_layer twice for depth=2:** Ineffective — both passes use the same `plaintext`, so the second pass adds the same offsets as the first, not new coupling. Use the additive multi-source approach.
- **Storing `Puzzle.tier` as a field:** D-12 explicitly prohibits this. Use `get_tier()` at query time.
- **Reusing a `RuleEngine` instance across sessions in `Puzzle.create_engine()`:** Each call must create a fresh engine with `_round=1`. The method calls `create_rule_engine()` — never stores an engine as a Puzzle attribute.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cryptographic hash | Custom checksum | `hashlib.sha256` | SHA-256 is collision-resistant and platform-identical; a custom checksum will have edge cases |
| Deterministic dict serialization | Custom byte encoder | `json.dumps(sort_keys=True)` | Already in stdlib; sort_keys guarantees key ordering; handles int/str types correctly |
| Multiple distinct random values | Manual loop with re-rolls | `random.sample(population, k)` | Stdlib function handles distinctness guarantee correctly and preserves RNG sequence |
| Dataclass equality for tier lookup | Custom hash/compare | `==` on frozen dataclass | Python generates `__eq__` from fields for frozen dataclasses; no custom code needed |

---

## Runtime State Inventory

> SKIPPED — this is a greenfield addition phase (new file `puzzle.py`), not a rename/refactor/migration. No stored data, live service config, or OS-registered state references `puzzle.py` or the new fields.

---

## Common Pitfalls

### Pitfall 1: RuleEngine Missing `_k_list` and `_state_change_rate` Attributes

**What goes wrong:** After updating `create_rule_engine()` to generate `k_list`, the planner forgets to update `RuleEngine.__init__` to accept `k_list: list` and store `self._k_list` and `self._state_change_rate`. The engine still stores `self._k = k` (single int) and `_encode_for_round` fails because `apply_cross_char_layer_multi` expects a list.

**Why it happens:** `create_rule_engine` and `RuleEngine.__init__` are separate concerns that must be updated in tandem.

**How to avoid:** Plan tasks for `rule_engine.py` as a single atomic task covering both `create_rule_engine` and `RuleEngine.__init__` updates. Test that `engine._k_list` is a list after construction.

**Warning signs:** `TypeError: 'int' object is not iterable` when `_encode_for_round` calls `apply_cross_char_layer_multi`.

### Pitfall 2: `apply_cross_char_layer` Signature Change Breaking 16 Layer Tests

**What goes wrong:** Planner changes `apply_cross_char_layer(k: int)` to `apply_cross_char_layer(k_list: list)`. All 16 existing `test_layers.py` tests pass `k` as an integer and immediately fail with `TypeError`.

**How to avoid:** Add a NEW function `apply_cross_char_layer_multi(k_list: list)`. Keep `apply_cross_char_layer(k: int)` unchanged. Update `RuleEngine._encode_for_round` to call the multi version. [VERIFIED: test code review confirms all 16 tests call with int k]

**Warning signs:** Pre-task grep should confirm all test_layers.py tests pass `k` as `int`.

### Pitfall 3: `state_change_rate` Stored in `create_rule_engine` but Not Passed to `_encode_for_round`

**What goes wrong:** `create_rule_engine` reads `difficulty.state_change_rate` correctly but stores only `self._alphabet` from difficulty. `_encode_for_round` calls `apply_state_layer` without the rate, reverting to default 1.0 for all tiers.

**How to avoid:** `RuleEngine.__init__` must store `self._state_change_rate = difficulty.state_change_rate`. The `_encode_for_round` call becomes `apply_state_layer(..., state_change_rate=self._state_change_rate)`.

**Warning signs:** MEDIUM/HARD tiers produce the same score sequences as EASY for the same seed and probe.

### Pitfall 4: Hash Computed Before `k_list` Is a List (single int serialized as int not list)

**What goes wrong:** For depth=1, `k_list = rng.sample(range(1,n), 1)` returns `[2]` (a list). If `generate_puzzle` serializes it as `k_list[0]` (an int) rather than `k_list` (a list), hashes computed with depth=1 and depth=2 have different JSON structures, making `verify_puzzle` fail if the serialization format drifts.

**How to avoid:** Always serialize `k_list` as a JSON array regardless of depth. The canonical hash payload is `{"base_shifts": [...], "ground_truth": "...", "k_list": [...]}` where `k_list` is always an array.

**Warning signs:** `verify_puzzle` passes for depth=1 but fails for depth=2, or vice versa.

### Pitfall 5: `cross_char_depth` Validation Allows Depth Equal to `output_length`

**What goes wrong:** `cross_char_depth` is validated as `<= output_length` instead of `<= output_length - 1`. For `output_length=5`, `depth=5` would require sampling 5 distinct values from `range(1, 5) = [1,2,3,4]` (only 4 elements), causing `ValueError: Sample larger than population`.

**How to avoid:** `__post_init__` validation: `1 <= cross_char_depth <= output_length - 1`. The maximum valid depth for `output_length=5` is 4. [VERIFIED: math analysis in this research session]

**Warning signs:** `ValueError: Sample larger than population or is negative` from `rng.sample`.

### Pitfall 6: `get_tier` Fragility When DifficultyConfig Fields Are Not All Checked

**What goes wrong:** `get_tier` compares the full `DifficultyConfig` object with `==`, but if the caller constructs a config that matches MEDIUM in alphabet and rate but has `output_length=6` (non-default), `get_tier` correctly returns `'custom'`. This is the right behavior — but the planner must not accidentally use `output_length=5` as implicit; it must be explicit in the tier constants.

**How to avoid:** Always specify all four fields explicitly in `EASY`, `MEDIUM`, `HARD` constant definitions, including `output_length=5`. Do not rely on the default.

---

## Code Examples

### Complete generate_puzzle and verify_puzzle

```python
# Source: stdlib hashlib, json, dataclasses [VERIFIED: Python stdlib]
import hashlib
import json
from __future__ import annotations
from dataclasses import dataclass
from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import create_rule_engine, RuleEngine


@dataclass(frozen=True)
class Puzzle:
    seed: int
    difficulty: DifficultyConfig
    puzzle_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if not self.puzzle_hash:
            raise ValueError("puzzle_hash must be non-empty")

    def create_engine(self) -> RuleEngine:
        return create_rule_engine(self.seed, self.difficulty)


def _compute_hash(base_shifts: list, k_list: list, ground_truth: str) -> str:
    payload = json.dumps(
        {"base_shifts": base_shifts, "ground_truth": ground_truth, "k_list": k_list},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def generate_puzzle(seed: int, difficulty: DifficultyConfig = None) -> Puzzle:
    if difficulty is None:
        difficulty = DifficultyConfig()
    engine = create_rule_engine(seed, difficulty)
    puzzle_hash = _compute_hash(engine._base_shifts, engine._k_list, engine._ground_truth)
    return Puzzle(seed=seed, difficulty=difficulty, puzzle_hash=puzzle_hash)


def verify_puzzle(puzzle: Puzzle) -> None:
    engine = create_rule_engine(puzzle.seed, puzzle.difficulty)
    expected = _compute_hash(engine._base_shifts, engine._k_list, engine._ground_truth)
    if expected != puzzle.puzzle_hash:
        raise ValueError(f"hash mismatch: expected {expected}, got {puzzle.puzzle_hash}")
```

### Updated create_rule_engine (key changes only)

```python
# Source: existing cipherbench/engine/rule_engine.py extended [VERIFIED: codebase]
def create_rule_engine(seed: int, difficulty: DifficultyConfig = None) -> RuleEngine:
    if difficulty is None:
        difficulty = DifficultyConfig()
    rng = random.Random(seed)
    n = difficulty.output_length
    alphabet = difficulty.alphabet
    base_shifts = [rng.randint(1, len(alphabet) - 1) for _ in range(n)]
    # Changed from: k = rng.randint(1, n - 1)
    # To: k_list via rng.sample — equivalent for depth=1, extensible for depth>1
    k_list = rng.sample(range(1, n), difficulty.cross_char_depth)
    ground_truth = alphabet[0] * n
    return RuleEngine(
        base_shifts=base_shifts,
        k_list=k_list,            # Changed from k=k
        difficulty=difficulty,
        ground_truth=ground_truth,
    )
```

### Updated RuleEngine.__init__ and _encode_for_round (key changes only)

```python
# Source: existing cipherbench/engine/rule_engine.py extended [VERIFIED: codebase]
class RuleEngine:
    def __init__(
        self,
        base_shifts: list,
        k_list: list,             # Changed from k: int
        difficulty: DifficultyConfig,
        ground_truth: str,
    ) -> None:
        self._base_shifts = base_shifts
        self._k_list = k_list                             # Changed from self._k = k
        self._state_change_rate = difficulty.state_change_rate  # NEW
        self._alphabet = difficulty.alphabet
        self._ground_truth = ground_truth
        self._round = 1

    def _encode_for_round(self, round_num: int) -> str:
        shifted = apply_state_layer(
            self._ground_truth,
            self._base_shifts,
            round_num,
            self._alphabet,
            self._state_change_rate,   # NEW parameter
        )
        return apply_cross_char_layer_multi(  # Changed from apply_cross_char_layer
            shifted, self._ground_truth, self._k_list, self._alphabet
        )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `k = rng.randint(1, n-1)` for cross-char | `k_list = rng.sample(range(1, n), depth)` list | Phase 2 | Multi-depth cross-char now possible; depth=1 is call-count-equivalent |
| `base_shift * round_num` (int) | `int(base_shift * round_num * state_change_rate)` | Phase 2 | Configurable rate of state evolution per round |
| No puzzle abstraction — engine returned directly | `Puzzle` frozen dataclass wraps seed+difficulty+hash | Phase 2 | Immutable puzzle identity; hash-verified reproducibility |

**Still current (unchanged from Phase 1):**
- `random.Random(seed)` isolated instance pattern
- `apply_state_layer` / `apply_cross_char_layer` pure function signatures (except adding optional `state_change_rate` parameter with default)
- Frozen dataclass pattern for value objects
- Private single-underscore attributes in `RuleEngine`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rng.sample(range(1, n), 1)` produces identical RNG output to `rng.randint(1, n-1)` on Python 3.9–3.13 | Pattern 3, Pitfall section | If wrong, Phase 1 test `test_fifty_sequential_runs_are_deterministic` fails after the `create_rule_engine` update; mitigation: run test suite immediately after the change |
| A2 | EASY alphabet `"ABCDEFGHIJ"` (10 chars) is "measurably distinct" enough from MEDIUM (26 chars) to satisfy GEN-03 | Pattern 8 | If GEN-03 validation test shows insufficient distinction, change EASY to a larger alphabet (e.g., 16 chars) — low-effort fix |
| A3 | `int()` truncation for effective shifts is deterministic across all platforms where Python runs | Pattern 4 | If wrong, hash verification would fail on platform change; however `int()` truncation toward zero is IEEE 754 standard and Python-guaranteed |

Note: A1 was verified empirically in this research session across 1000 seeds on Python 3.9.6. [VERIFIED: simulation]

---

## Open Questions

1. **Does the GEN-03 "measurably distinct" criterion require an automated test or just design-time analysis?**
   - What we know: The CONTEXT says "the planner should simulate or analyze to ensure GEN-03's measurably distinct complexity is met"
   - What's unclear: Whether this needs a pytest test or just a documented analysis
   - Recommendation: Include a test that asserts EASY/MEDIUM/HARD produce different score distributions over N=100 random seeds. A simple check: `set(scores_easy) != set(scores_hard)` is not sufficient; better to assert that mean attempts-to-solve (simulated) differs across tiers.

2. **Should `generate_puzzle()` be the exported name or `Puzzle.from_seed()`?**
   - What we know: D-06 locks the name as `generate_puzzle()` (module-level function)
   - What's unclear: Nothing — this is locked
   - Recommendation: Follow D-06 exactly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9.6 | All code | Yes | 3.9.6 | — |
| pytest | Tests | Yes | 8.4.2 | — |
| hypothesis | Property tests | Yes | 6.114.1 | — |
| hashlib (stdlib) | Hash computation | Yes | built-in | — |
| json (stdlib) | Hash serialization | Yes | built-in | — |

**Note on Python 3.9.6:** System Python is 3.9.6, but `pyproject.toml` declares `requires-python = ">=3.11"`. Phase 1 ran on 3.9.6 with compatible dependency versions. Phase 2 uses only stdlib features available since Python 3.6 (`dataclasses` added in 3.7). No Python 3.10+ syntax should be introduced (avoid `X | Y` union types, use `Optional[X]` instead).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/ -q --tb=short` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GEN-01 | Same seed → same puzzle (any environment, process restart) | unit | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_same_seed_same_puzzle -x` | Wave 0 |
| GEN-01 | `generate_puzzle(42)` called twice → `.puzzle_hash` equal | unit | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_generate_puzzle_reproducible -x` | Wave 0 |
| GEN-02 | `verify_puzzle(puzzle)` passes for freshly generated puzzle | unit | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_verify_puzzle_passes -x` | Wave 0 |
| GEN-02 | `verify_puzzle` raises `ValueError` when seed is mutated | unit | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_verify_puzzle_detects_mutation -x` | Wave 0 |
| GEN-03 | `EASY`, `MEDIUM`, `HARD` are distinct `DifficultyConfig` instances | unit | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_tier_constants_distinct -x` | Wave 0 |
| GEN-03 | `get_tier(EASY)` returns `'easy'`, etc. | unit | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_get_tier -x` | Wave 0 |
| GEN-03 | EASY/MEDIUM/HARD generate measurably distinct puzzle complexity | integration | `python3 -m pytest tests/unit/test_puzzle/test_puzzle.py::test_difficulty_tiers_distinct_complexity -x` | Wave 0 |
| D-02 | `state_change_rate=1.0` preserves Phase 1 behavior | unit | `python3 -m pytest tests/unit/test_engine/test_types.py -x` (existing) | Yes |
| D-02 | `state_change_rate=1.5` produces different effective shifts | unit | `python3 -m pytest tests/unit/test_engine/test_layers.py::test_state_layer_rate_changes_shifts -x` | Wave 0 |
| D-03 | `apply_cross_char_layer_multi` with depth=1 matches `apply_cross_char_layer` | unit | `python3 -m pytest tests/unit/test_engine/test_layers.py::test_multi_depth1_matches_single -x` | Wave 0 |
| D-03 | `apply_cross_char_layer_multi` with depth=2 differs from depth=1 | unit | `python3 -m pytest tests/unit/test_engine/test_layers.py::test_multi_depth2_differs_depth1 -x` | Wave 0 |
| Regression | All 47 Phase 1 tests still pass after changes | regression | `python3 -m pytest tests/ -q` (all 47 must still pass) | Yes |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/ -q --tb=short`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_puzzle/__init__.py` — test sub-package for puzzle.py tests
- [ ] `tests/unit/test_puzzle/test_puzzle.py` — covers GEN-01, GEN-02, GEN-03
- [ ] New test functions in `tests/unit/test_engine/test_layers.py` — covers `apply_cross_char_layer_multi` and `apply_state_layer` rate parameter
- [ ] New test functions in `tests/unit/test_engine/test_types.py` — covers new `DifficultyConfig` fields and validations

---

## Security Domain

> `security_enforcement: true` in config.json. ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not applicable — no user authentication in puzzle generation |
| V3 Session Management | No | No sessions in this phase |
| V4 Access Control | No | No access control in this phase |
| V5 Input Validation | Yes | `DifficultyConfig.__post_init__` validates all new fields; `generate_puzzle` validates `seed` is int |
| V6 Cryptography | No | SHA-256 used for integrity hash, not for secrets — no key management required |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Crafted `DifficultyConfig` with `cross_char_depth=0` or negative | Tampering | `__post_init__` raises `ValueError` — validated |
| Crafted `DifficultyConfig` with `cross_char_depth > output_length-1` | Tampering / DoS | `__post_init__` raises `ValueError`; prevents `rng.sample` crash |
| Crafted `DifficultyConfig` with `state_change_rate <= 0.0` | Tampering | `__post_init__` raises `ValueError` |
| Hash collision enabling undetected puzzle mutation | Spoofing | SHA-256 collision resistance is negligible risk for puzzle identifiers |
| `verify_puzzle` error message exposing internal state | Information Disclosure | Error message exposes the hash strings only (hex strings, not cipher key/shifts) — acceptable per RULE-04 analogy |

---

## Sources

### Primary (HIGH confidence)

- Python stdlib `hashlib` documentation — SHA-256 API [VERIFIED: Python stdlib]
- Python stdlib `json` documentation — `sort_keys` parameter behavior [VERIFIED: Python stdlib]
- Python stdlib `random.Random` and `random.sample` documentation [VERIFIED: Python stdlib]
- Python stdlib `dataclasses` frozen dataclass `__eq__` generation [VERIFIED: Python stdlib]
- `cipherbench/types.py` — existing `DifficultyConfig` pattern [VERIFIED: codebase]
- `cipherbench/engine/rule_engine.py` — existing `create_rule_engine` and `RuleEngine` [VERIFIED: codebase]
- `cipherbench/engine/layers.py` — existing `apply_state_layer` / `apply_cross_char_layer` [VERIFIED: codebase]
- `tests/` — all 47 existing tests, verified passing at research time [VERIFIED: `python3 -m pytest tests/ -q` = 47 passed]

### Secondary (MEDIUM confidence)

- Python `random.sample` vs `random.randint` RNG sequence equivalence — verified empirically across 1000 seeds [VERIFIED: simulation in this research session]
- `int()` truncation backward compatibility for `state_change_rate=1.0` — verified exhaustively [VERIFIED: simulation in this research session]
- EASY/MEDIUM/HARD complexity analysis — verified via entropy calculation [VERIFIED: simulation in this research session]

### Tertiary (LOW confidence)

- None — all claims in this research were verified against codebase, stdlib documentation, or empirical simulation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new dependencies
- Architecture (file changes): HIGH — derived from direct code analysis
- Backward compatibility: HIGH — verified empirically (1000 seeds, exhaustive int check)
- Pitfalls: HIGH — derived from direct test code review
- Difficulty tier values: MEDIUM — empirically analyzed but not validated against model performance (no model runs exist yet)

**Research date:** 2026-05-29
**Valid until:** 2026-08-29 (stable stdlib; no external dependencies to drift)
