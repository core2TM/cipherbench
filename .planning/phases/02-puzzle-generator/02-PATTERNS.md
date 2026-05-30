# Phase 2: Puzzle Generator - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 6
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `cipherbench/types.py` | model (data contract) | transform | self (in-place extension) | exact |
| `cipherbench/engine/layers.py` | utility (pure functions) | transform | self (in-place extension) | exact |
| `cipherbench/engine/rule_engine.py` | service (stateful factory) | request-response | self (in-place extension) | exact |
| `cipherbench/puzzle.py` | service (factory + value object) | request-response | `cipherbench/engine/rule_engine.py` + `cipherbench/types.py` | role-match |
| `tests/unit/test_puzzle/__init__.py` | config (package init) | n/a | `tests/unit/test_engine/__init__.py` | exact |
| `tests/unit/test_puzzle/test_puzzle.py` | test | request-response | `tests/unit/test_engine/test_types.py` + `tests/unit/test_engine/test_rule_engine.py` | role-match |

---

## Pattern Assignments

### `cipherbench/types.py` (model, transform) — MODIFY

**Analog:** `cipherbench/types.py` lines 1–70 (self — in-place extension)

**Module docstring pattern** (lines 1–8):
```python
"""CipherBench data contracts.

Defines the shared frozen dataclasses that all phases import.
These types are the stable public API surface — field names and validation
rules are locked by decisions D-01 through D-06 and D-09.

NO imports from cipherbench.engine — this is the pure data layer.
"""
from dataclasses import dataclass
```

**Frozen dataclass with `__post_init__` pattern** (lines 12–36):
```python
@dataclass(frozen=True)
class DifficultyConfig:
    """...docstring..."""

    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    output_length: int = 5

    def __post_init__(self) -> None:
        if len(self.alphabet) < 2:
            raise ValueError("alphabet must have at least 2 characters")
        if self.output_length < 1:
            raise ValueError("output_length must be positive")
```

**What to add — two new fields with validation** (append to field list and `__post_init__`):
```python
    state_change_rate: float = 1.0   # D-02: round multiplier rate; default 1.0 preserves Phase 1 behavior
    cross_char_depth: int = 1        # D-03: simultaneous cross-char offset links; default 1 = current behavior

    def __post_init__(self) -> None:
        if len(self.alphabet) < 2:
            raise ValueError("alphabet must have at least 2 characters")
        if self.output_length < 1:
            raise ValueError("output_length must be positive")
        # NEW validations (D-02, D-03):
        if self.state_change_rate <= 0.0:
            raise ValueError("state_change_rate must be positive")
        if not (1 <= self.cross_char_depth <= self.output_length - 1):
            raise ValueError(
                f"cross_char_depth must be in [1, output_length-1="
                f"{self.output_length - 1}], got {self.cross_char_depth}"
            )
```

**Docstring update pattern** — extend the class docstring `Fields` section by adding:
```
state_change_rate : float
    Multiplier applied to the round number in the state layer. Default: 1.0 (D-02).
    At 1.0 the formula is ``base_shift * round_num`` (Phase 1 behavior preserved).
    Values > 1.0 accelerate cipher state evolution; must be positive.
cross_char_depth : int
    Number of simultaneous cross-character offset links applied. Default: 1 (D-03).
    Depth 1 is equivalent to the Phase 1 single-k behavior.
    Must be in [1, output_length - 1]; maximum 4 for the default output_length=5.
```

**No new imports needed** — `dataclasses` already imported.

---

### `cipherbench/engine/layers.py` (utility, transform) — MODIFY

**Analog:** `cipherbench/engine/layers.py` lines 1–129 (self — extend, do not replace)

**Module docstring + import pattern** (lines 1–17):
```python
"""Pure cipher layer functions — the functional core of CipherBench.
...
"""

from __future__ import annotations
```

**Existing `apply_state_layer` signature to MODIFY** (lines 20–52) — add `state_change_rate` parameter with default:
```python
def apply_state_layer(
    plaintext: str,
    base_shifts: list,
    round_num: int,
    alphabet: str,
    state_change_rate: float = 1.0,   # NEW D-02 — default preserves existing behavior
) -> list:
    """Apply round-number multiplier to base shifts and shift each plaintext character.
    ...
    state_change_rate : float
        Multiplier applied to round_num. Default 1.0 preserves Phase 1 linear behavior.
        effective_shift = int(base_shift * round_num * state_change_rate).
    ...
    """
    effective_shifts = [int(s * round_num * state_change_rate) for s in base_shifts]
    indices = [alphabet.index(c) for c in plaintext]
    return [(idx + eff) % len(alphabet) for idx, eff in zip(indices, effective_shifts)]
```

**Key formula change:** `s * round_num` becomes `int(s * round_num * state_change_rate)`.
At `state_change_rate=1.0` and integer inputs this is bit-identical to the original.

**Existing `apply_cross_char_layer` — DO NOT MODIFY** (lines 55–104):
```python
# Keep the existing function exactly as-is to preserve all 16 test_layers.py tests.
# The function signature apply_cross_char_layer(shifted_indices, plaintext, k: int, alphabet)
# must remain unchanged.
```

**New function to ADD** — `apply_cross_char_layer_multi` (append after `apply_cross_char_layer`):
```python
def apply_cross_char_layer_multi(
    shifted_indices: list,
    plaintext: str,
    k_list: list,
    alphabet: str,
) -> str:
    """Apply cross-character offset injection with multiple k values (D-03, depth > 1).

    For each output position ``j``, accumulates extra offsets from each ``k`` in
    ``k_list`` additively.  With ``k_list=[k]`` (depth=1) the output is identical
    to ``apply_cross_char_layer(k=k)``.

    Implements RULE-02 for cross_char_depth >= 1.  Called by RuleEngine._encode_for_round
    instead of apply_cross_char_layer when depth > 1.

    Parameters
    ----------
    shifted_indices : list[int]
        Output of ``apply_state_layer``.
    plaintext : str
        Original probe string (used for extra_offset derivation).
    k_list : list[int]
        List of cross-character offset distances.  One entry per coupling link.
    alphabet : str
        Character set in use.

    Returns
    -------
    str
        Encoded output string of the same length as ``shifted_indices``.
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

**Import update to `rule_engine.py`** — the import line in `rule_engine.py` (line 41) must add `apply_cross_char_layer_multi`:
```python
from cipherbench.engine.layers import (
    apply_state_layer,
    apply_cross_char_layer,
    apply_cross_char_layer_multi,  # NEW
    count_correct,
)
```

---

### `cipherbench/engine/rule_engine.py` (service, request-response) — MODIFY

**Analog:** `cipherbench/engine/rule_engine.py` lines 1–208 (self — targeted changes)

**Import block — add `apply_cross_char_layer_multi`** (line 41):
```python
from __future__ import annotations

import random

from cipherbench.types import AttemptScore, DifficultyConfig
from cipherbench.engine.layers import (
    apply_state_layer,
    apply_cross_char_layer,
    apply_cross_char_layer_multi,  # NEW
    count_correct,
)
```

**`RuleEngine.__init__` — change `k: int` to `k_list: list` and add `_state_change_rate`** (lines 56–67):

Current:
```python
def __init__(
    self,
    base_shifts: list,
    k: int,
    difficulty: DifficultyConfig,
    ground_truth: str,
) -> None:
    self._base_shifts = base_shifts
    self._k = k
    self._alphabet = difficulty.alphabet
    self._ground_truth = ground_truth
    self._round = 1
```

Replace with:
```python
def __init__(
    self,
    base_shifts: list,
    k_list: list,              # Changed from k: int (D-03)
    difficulty: DifficultyConfig,
    ground_truth: str,
) -> None:
    self._base_shifts = base_shifts
    self._k_list = k_list                              # Changed from self._k = k
    self._state_change_rate = difficulty.state_change_rate  # NEW (D-02)
    self._alphabet = difficulty.alphabet
    self._ground_truth = ground_truth
    self._round = 1
```

**`RuleEngine._encode_for_round` — update both layer calls** (lines 123–147):

Current:
```python
def _encode_for_round(self, round_num: int) -> str:
    shifted = apply_state_layer(
        self._ground_truth, self._base_shifts, round_num, self._alphabet
    )
    return apply_cross_char_layer(shifted, self._ground_truth, self._k, self._alphabet)
```

Replace with:
```python
def _encode_for_round(self, round_num: int) -> str:
    shifted = apply_state_layer(
        self._ground_truth,
        self._base_shifts,
        round_num,
        self._alphabet,
        self._state_change_rate,   # NEW (D-02)
    )
    return apply_cross_char_layer_multi(  # Changed from apply_cross_char_layer (D-03)
        shifted, self._ground_truth, self._k_list, self._alphabet
    )
```

**`create_rule_engine` — replace `k = rng.randint` with `k_list = rng.sample` and update `RuleEngine()` call** (lines 153–207):

Change line 193–194:
```python
# OLD:
k = rng.randint(1, n - 1)

# NEW (D-03): rng.sample is call-count-equivalent for depth=1, verified across 1000 seeds
k_list = rng.sample(range(1, n), difficulty.cross_char_depth)
```

Change `return RuleEngine(...)` call (line 202–207):
```python
return RuleEngine(
    base_shifts=base_shifts,
    k_list=k_list,            # Changed from k=k
    difficulty=difficulty,
    ground_truth=ground_truth,
)
```

**Docstring update for `create_rule_engine`** — update the docstring to reference `k_list` and `cross_char_depth` instead of `k`.

**Backward compat guarantee:** Existing `test_no_public_key_accessor` checks for public methods only — does not reference `_k` or `_k_list` by name, so renaming `_k` to `_k_list` does not break it. `test_cipher_key_not_accessible` checks `not hasattr(engine, 'base_shifts')` etc. — not broken by the rename.

---

### `cipherbench/puzzle.py` (service + value object, request-response) — CREATE

**Primary analog:** `cipherbench/engine/rule_engine.py` (frozen dataclass + factory function pattern)
**Secondary analog:** `cipherbench/types.py` (frozen dataclass with `__post_init__` validation)

**Module docstring pattern** — follow the same style as `rule_engine.py` lines 1–35:
```python
"""CipherBench puzzle generation layer.

Provides:
  Puzzle            — frozen dataclass: seed, difficulty, puzzle_hash
  generate_puzzle   — the only authorized Puzzle constructor (D-06)
  verify_puzzle     — hash-based integrity assertion (GEN-02, D-09)
  get_tier          — maps DifficultyConfig to tier name (D-12)
  EASY, MEDIUM, HARD — canonical DifficultyConfig tier presets (D-10)

Design decisions implemented here:
  D-04  Puzzle.create_engine() calls create_rule_engine — never reuses an engine.
  D-07  Hash covers derived state: base_shifts + k_list + ground_truth.
  D-08  hashlib.sha256 with json.dumps(sort_keys=True) serialization.
  D-09  verify_puzzle raises ValueError on hash mismatch — caller handles.
  D-10  EASY/MEDIUM/HARD constants defined here; all fields explicit.
  D-12  get_tier returns 'easy'/'medium'/'hard'/'custom' — tier not stored in Puzzle.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from cipherbench.types import DifficultyConfig
from cipherbench.engine.rule_engine import RuleEngine, create_rule_engine
```

**`Puzzle` frozen dataclass** — follow `DifficultyConfig` pattern (types.py lines 12–36) and `AttemptScore` pattern (types.py lines 39–69):
```python
@dataclass(frozen=True)
class Puzzle:
    """Immutable puzzle identity: seed + difficulty + derived-state hash.

    Frozen after construction (D-09). Two Puzzles with the same seed + difficulty
    are the same puzzle — equality via dataclass-generated __eq__.

    Never construct directly. Use generate_puzzle(seed, difficulty) (D-06).

    Fields
    ------
    seed : int
        Integer RNG seed. Same seed + difficulty always produces the same puzzle.
    difficulty : DifficultyConfig
        Difficulty configuration used to derive the puzzle state.
    puzzle_hash : str
        SHA-256 hex digest of the derived engine state (base_shifts + k_list +
        ground_truth). Proves bit-for-bit RNG determinism (GEN-02, D-07).
    """

    seed: int
    difficulty: DifficultyConfig
    puzzle_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if not self.puzzle_hash:
            raise ValueError("puzzle_hash must be non-empty")

    def create_engine(self) -> RuleEngine:
        """Return a fresh RuleEngine for this puzzle's seed and difficulty (D-05).

        Each call creates an independent engine instance with _round=1.
        Never reuse the returned engine across sessions (D-10).
        """
        return create_rule_engine(self.seed, self.difficulty)
```

**Private hash helper** — internal function, not exported:
```python
def _compute_hash(base_shifts: list, k_list: list, ground_truth: str) -> str:
    """Compute SHA-256 hex digest of derived puzzle state (D-07, D-08).

    Serialization: json.dumps with sort_keys=True — deterministic across
    all Python versions and platforms for int/str values (no float ambiguity).
    k_list is always serialized as a JSON array, even at depth=1.
    """
    payload = json.dumps(
        {"base_shifts": base_shifts, "ground_truth": ground_truth, "k_list": k_list},
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()
```

**`generate_puzzle` factory** — follow `create_rule_engine` pattern (rule_engine.py lines 153–207):
```python
def generate_puzzle(seed: int, difficulty: DifficultyConfig = None) -> Puzzle:
    """Construct a Puzzle from a seed and difficulty configuration (GEN-01, GEN-02).

    This is the ONLY authorized way to construct a Puzzle (D-06).
    Calls create_rule_engine internally to derive base_shifts, k_list,
    and ground_truth, then hashes them for integrity verification.

    Parameters
    ----------
    seed : int
        Integer RNG seed. Same seed + difficulty yields the same Puzzle.
    difficulty : DifficultyConfig, optional
        Difficulty tier. Defaults to DifficultyConfig() (A-Z, length 5).

    Returns
    -------
    Puzzle
        Immutable puzzle with seed, difficulty, and SHA-256 hash of derived state.
    """
    if difficulty is None:
        difficulty = DifficultyConfig()
    engine = create_rule_engine(seed, difficulty)
    puzzle_hash = _compute_hash(engine._base_shifts, engine._k_list, engine._ground_truth)
    return Puzzle(seed=seed, difficulty=difficulty, puzzle_hash=puzzle_hash)
```

**`verify_puzzle` standalone function** — follow error-raising pattern from `score_attempt` (rule_engine.py lines 101–108):
```python
def verify_puzzle(puzzle: Puzzle) -> None:
    """Re-derive the puzzle hash and assert it matches the stored value (GEN-02, D-09).

    Raises
    ------
    ValueError
        If the re-derived hash does not match puzzle.puzzle_hash.
        Message format: 'hash mismatch: expected {X}, got {Y}'.
    """
    engine = create_rule_engine(puzzle.seed, puzzle.difficulty)
    expected = _compute_hash(engine._base_shifts, engine._k_list, engine._ground_truth)
    if expected != puzzle.puzzle_hash:
        raise ValueError(
            f"hash mismatch: expected {expected}, got {puzzle.puzzle_hash}"
        )
```

**Tier constants and `get_tier`** — all four fields explicit to avoid `get_tier` fragility (D-12):
```python
EASY = DifficultyConfig(
    alphabet="ABCDEFGHIJ",
    output_length=5,
    state_change_rate=1.0,
    cross_char_depth=1,
)

MEDIUM = DifficultyConfig(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    output_length=5,
    state_change_rate=1.5,
    cross_char_depth=2,
)

HARD = DifficultyConfig(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    output_length=5,
    state_change_rate=2.0,
    cross_char_depth=3,
)


def get_tier(difficulty: DifficultyConfig) -> str:
    """Return the tier name for a given DifficultyConfig (D-12).

    Uses frozen dataclass __eq__ (field-by-field comparison).
    Returns 'custom' for any config not matching a named preset.
    """
    if difficulty == EASY:
        return "easy"
    if difficulty == MEDIUM:
        return "medium"
    if difficulty == HARD:
        return "hard"
    return "custom"
```

---

### `tests/unit/test_puzzle/__init__.py` (config, n/a) — CREATE

**Analog:** `tests/unit/test_engine/__init__.py` — the file is empty (one blank line).

```python
# (empty — pytest package marker)
```

---

### `tests/unit/test_puzzle/test_puzzle.py` (test, request-response) — CREATE

**Primary analogs:**
- `tests/unit/test_engine/test_types.py` — frozen dataclass validation tests (lines 1–88)
- `tests/unit/test_engine/test_rule_engine.py` — factory + state boundary tests (lines 1–136)
- `tests/unit/test_engine/test_seeding.py` — determinism + RNG discipline tests (lines 1–139)
- `tests/test_properties.py` — Hypothesis property tests (lines 1–116)

**Module docstring + imports pattern** (follow test_types.py lines 1–8 and test_rule_engine.py lines 1–14):
```python
"""Tests for cipherbench.puzzle — Puzzle dataclass, generate_puzzle, verify_puzzle, get_tier.

Covers:
  GEN-01: Same seed + difficulty always yields identical Puzzle (hash equality)
  GEN-02: verify_puzzle passes for fresh puzzle; raises ValueError on mutation
  GEN-03: EASY/MEDIUM/HARD are distinct configs; get_tier maps correctly;
          tiers produce measurably distinct complexity
  D-04/D-05: Puzzle.create_engine() returns fresh RuleEngine each call
  D-06: Public import path works as specified
  D-09: Puzzle is frozen; no leaking of engine private state through Puzzle
  D-12: get_tier returns 'custom' for unrecognized configs
"""
from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from cipherbench.types import DifficultyConfig
from cipherbench.puzzle import (
    Puzzle,
    generate_puzzle,
    verify_puzzle,
    get_tier,
    EASY,
    MEDIUM,
    HARD,
)
```

**GEN-01 — reproducibility tests** (follow test_seeding.py `test_fifty_sequential_runs_are_deterministic` pattern, lines 72–91):
```python
def test_generate_puzzle_reproducible():
    """GEN-01: Same seed + difficulty called twice produces identical puzzle_hash."""
    p1 = generate_puzzle(42)
    p2 = generate_puzzle(42)
    assert p1.puzzle_hash == p2.puzzle_hash


def test_same_seed_same_puzzle():
    """GEN-01: generate_puzzle with same seed and explicit difficulty is deterministic."""
    p1 = generate_puzzle(seed=42, difficulty=MEDIUM)
    p2 = generate_puzzle(seed=42, difficulty=MEDIUM)
    assert p1 == p2  # frozen dataclass __eq__ covers all fields
```

**GEN-02 — hash verification tests** (follow test_rule_engine.py `pytest.raises(ValueError)` pattern):
```python
def test_verify_puzzle_passes():
    """GEN-02: verify_puzzle does not raise for a freshly generated puzzle."""
    puzzle = generate_puzzle(seed=0)
    verify_puzzle(puzzle)  # must not raise


def test_verify_puzzle_detects_mutation():
    """GEN-02: verify_puzzle raises ValueError when puzzle_hash does not match re-derived hash."""
    puzzle = generate_puzzle(seed=1)
    # Construct a tampered puzzle with a different seed but same stored hash
    tampered = Puzzle(seed=999, difficulty=puzzle.difficulty, puzzle_hash=puzzle.puzzle_hash)
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_puzzle(tampered)
```

**GEN-03 — tier and complexity tests** (follow test_types.py `test_difficulty_config_defaults` pattern):
```python
def test_tier_constants_distinct():
    """GEN-03: EASY, MEDIUM, HARD are three distinct DifficultyConfig instances."""
    assert EASY != MEDIUM
    assert MEDIUM != HARD
    assert EASY != HARD


def test_get_tier():
    """GEN-03: get_tier maps each preset to the correct string label."""
    assert get_tier(EASY) == "easy"
    assert get_tier(MEDIUM) == "medium"
    assert get_tier(HARD) == "hard"


def test_get_tier_custom():
    """D-12: get_tier returns 'custom' for a config not matching any preset."""
    custom = DifficultyConfig(alphabet="ABCDE", output_length=5, state_change_rate=1.0, cross_char_depth=1)
    assert get_tier(custom) == "custom"


def test_difficulty_tiers_distinct_complexity():
    """GEN-03: EASY/MEDIUM/HARD generate structurally distinct puzzles over N seeds.

    Asserts that the set of puzzle_hash values differs across tiers for the same seeds,
    confirming that different parameters produce different derived states.
    """
    seeds = list(range(20))
    easy_hashes = {generate_puzzle(s, EASY).puzzle_hash for s in seeds}
    medium_hashes = {generate_puzzle(s, MEDIUM).puzzle_hash for s in seeds}
    hard_hashes = {generate_puzzle(s, HARD).puzzle_hash for s in seeds}
    assert easy_hashes.isdisjoint(medium_hashes), "EASY and MEDIUM share puzzle hashes"
    assert medium_hashes.isdisjoint(hard_hashes), "MEDIUM and HARD share puzzle hashes"
    assert easy_hashes.isdisjoint(hard_hashes), "EASY and HARD share puzzle hashes"
```

**D-04/D-05 — Puzzle.create_engine() tests** (follow test_rule_engine.py `test_factory_produces_fresh_instances` pattern, lines 81–88):
```python
def test_create_engine_returns_rule_engine():
    """D-05: Puzzle.create_engine() returns a RuleEngine instance."""
    from cipherbench.engine.rule_engine import RuleEngine
    puzzle = generate_puzzle(seed=42)
    engine = puzzle.create_engine()
    assert isinstance(engine, RuleEngine)


def test_create_engine_fresh_each_call():
    """D-05: Two calls to puzzle.create_engine() return independent engine instances."""
    puzzle = generate_puzzle(seed=42)
    engine_a = puzzle.create_engine()
    engine_b = puzzle.create_engine()
    # Each should be at round 1; advance engine_a and check engine_b is unaffected
    engine_a.score_attempt("AAAAA")
    result_b = engine_b.score_attempt("AAAAA")
    engine_c = puzzle.create_engine()
    result_c = engine_c.score_attempt("AAAAA")
    assert result_b == result_c, "engine_b and engine_c should both be at round 1"
```

**D-09 — Puzzle is frozen** (follow test_types.py `test_dataclasses_are_frozen_*` pattern, lines 62–75):
```python
def test_puzzle_is_frozen():
    """D-09: Mutating Puzzle fields after construction raises FrozenInstanceError."""
    puzzle = generate_puzzle(seed=42)
    with pytest.raises(FrozenInstanceError):
        puzzle.seed = 99  # type: ignore[misc]
```

**D-06 — import path test**:
```python
def test_public_import_path():
    """D-06: All public names importable from cipherbench.puzzle."""
    from cipherbench.puzzle import Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD
    assert Puzzle is not None
    assert callable(generate_puzzle)
    assert callable(verify_puzzle)
    assert callable(get_tier)
```

**Hypothesis property test** (follow test_properties.py `@given` + `@settings` pattern, lines 29–46):
```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=50)
def test_verify_puzzle_always_passes_for_fresh_puzzle(seed: int) -> None:
    """GEN-02 property: verify_puzzle(generate_puzzle(seed)) never raises for any seed."""
    puzzle = generate_puzzle(seed)
    verify_puzzle(puzzle)  # must not raise
```

---

## Shared Patterns

### Frozen Dataclass with `__post_init__` Validation
**Source:** `cipherbench/types.py` lines 12–36 (`DifficultyConfig`) and lines 39–69 (`AttemptScore`)
**Apply to:** `Puzzle` dataclass in `cipherbench/puzzle.py`

```python
@dataclass(frozen=True)
class SomeName:
    field: type = default

    def __post_init__(self) -> None:
        if <invalid condition>:
            raise ValueError("<descriptive message>")
```

### Factory Function Pattern
**Source:** `cipherbench/engine/rule_engine.py` lines 153–207 (`create_rule_engine`)
**Apply to:** `generate_puzzle()` in `cipherbench/puzzle.py`

```python
def create_or_generate(seed: int, config: DifficultyConfig = None) -> SomeType:
    if config is None:
        config = DifficultyConfig()
    # ... derive state from seed ...
    return SomeType(...)
```

### Explicit RNG Threading (D-11)
**Source:** `cipherbench/engine/rule_engine.py` lines 181–193
**Apply to:** No new RNG calls in `puzzle.py` — `generate_puzzle()` delegates to `create_rule_engine()` which owns the RNG. Never call `random.seed()` or `random.*()` module-level functions anywhere.

```python
rng = random.Random(seed)  # isolated instance — never touches global random state
```

### ValueError with Descriptive Messages (no cipher state leaked)
**Source:** `cipherbench/engine/rule_engine.py` lines 102–108 (score_attempt validation)
**Apply to:** `verify_puzzle()` in `cipherbench/puzzle.py`, `__post_init__` in all dataclasses

```python
raise ValueError(f"hash mismatch: expected {expected}, got {puzzle.puzzle_hash}")
```

### `from __future__ import annotations`
**Source:** `cipherbench/engine/rule_engine.py` line 36, `tests/unit/test_engine/test_rule_engine.py` line 3
**Apply to:** `cipherbench/puzzle.py` and `tests/unit/test_puzzle/test_puzzle.py`

Note: All new Python files must include `from __future__ import annotations` as the first import for forward reference compatibility (required because `pyproject.toml` targets Python 3.11 but the system runs 3.9.6; avoids `X | Y` union syntax).

### pytest.raises Pattern
**Source:** `tests/unit/test_engine/test_types.py` lines 19–29
**Apply to:** All negative-path tests in `test_puzzle.py`

```python
with pytest.raises(ValueError):
    <call that must raise>

# With message assertion:
with pytest.raises(ValueError, match="hash mismatch"):
    verify_puzzle(tampered)
```

### conftest.py Fixture Pattern
**Source:** `tests/conftest.py` lines 12–34
**Apply to:** `test_puzzle.py` — can add fixtures for `generate_puzzle(42)` if used across multiple tests (optional; inline `generate_puzzle(42)` calls in each test are fine for short tests)

```python
@pytest.fixture
def puzzle_seed_42():
    """Fresh Puzzle for seed 42 — canonical test seed."""
    return generate_puzzle(seed=42)
```

### Hypothesis `@given` + `@settings` Pattern
**Source:** `tests/test_properties.py` lines 29–46
**Apply to:** `test_verify_puzzle_always_passes_for_fresh_puzzle` in `test_puzzle.py`

```python
@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=50)
def test_something(seed: int) -> None:
    ...
```

---

## No Analog Found

All six files have direct analogs in the codebase. No entries in this section.

---

## Metadata

**Analog search scope:** `/Users/atipat/Desktop/superfinal/cipherbench/`, `/Users/atipat/Desktop/superfinal/tests/`
**Files scanned:** 10 Python files (all existing source and test files)
**Pattern extraction date:** 2026-05-29
