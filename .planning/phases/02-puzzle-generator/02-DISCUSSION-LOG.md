# Phase 2: Puzzle Generator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 2-Puzzle Generator
**Areas discussed:** DifficultyConfig extension, Puzzle object shape, Hash scope for GEN-02, Difficulty tier definitions

---

## DifficultyConfig Extension

**Question 1: How should the new difficulty axes be exposed?**

| Option | Description | Selected |
|--------|-------------|----------|
| Extend DifficultyConfig in-place | Add optional fields with defaults to existing frozen dataclass in types.py. create_rule_engine() reads them. Phase 1 default behavior preserved. | ✓ |
| New PuzzleConfig wrapper type | Keep DifficultyConfig as-is; introduce PuzzleConfig with extra fields. Two types, cleaner separation, more abstraction. | |
| You decide | Leave extension strategy to planner/implementer. | |

**User's choice:** Extend DifficultyConfig in-place

---

**Question 2: State-change rate parameterization**

| Option | Description | Selected |
|--------|-------------|----------|
| Step size float (state_change_rate) | Add state_change_rate: float = 1.0. Round multiplier = base_shift * (round_num * rate). | ✓ |
| Growth function enum | StateGrowth enum: LINEAR, QUADRATIC, EXPONENTIAL. More expressive, more complexity. | |
| You decide | Lock as planner detail. | |

**User's choice:** Step size float — `state_change_rate: float = 1.0`

---

**Question 3: Cross-char mixing depth parameterization**

| Option | Description | Selected |
|--------|-------------|----------|
| cross_char_depth field | Add cross_char_depth: int = 1. Depth 1 = k in [1, n-1]; Depth 2+ = multiple simultaneous offset links. | ✓ |
| Constrain k to a bounded range | Add cross_char_min_k and cross_char_max_k fields. Simpler to reason about. | |
| You decide | Constraint: higher depth = harder puzzle. Leave to planner. | |

**User's choice:** `cross_char_depth: int = 1`

---

## Puzzle Object Shape

**Question 1: What should a Puzzle object contain?**

| Option | Description | Selected |
|--------|-------------|----------|
| Thin metadata + create_engine() method | seed + difficulty + puzzle_hash. create_engine() -> RuleEngine method. Phase 3 calls puzzle.create_engine() per session. | ✓ |
| Bundled with live RuleEngine | seed + difficulty + puzzle_hash + pre-constructed RuleEngine. One Puzzle = one session. | |
| Pure data (seed + difficulty + hash only) | No methods. Phase 3 manually calls create_rule_engine(). Cleanest but Phase 3 must know the import. | |

**User's choice:** Thin metadata + `create_engine()` method

---

**Question 2: Where should Puzzle type and generate_puzzle() live?**

| Option | Description | Selected |
|--------|-------------|----------|
| cipherbench/puzzle.py | Single flat module. Consistent with Phase 1's flat layout. | ✓ |
| cipherbench/generator/ package | Subpackage with puzzle.py, types.py, etc. More extensible, more nesting. | |
| Puzzle in types.py, function in generator.py | Types module is shared contract layer; function in separate module. | |

**User's choice:** `cipherbench/puzzle.py`

---

**Question 3: Frozen or regular dataclass?**

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen dataclass | Consistent with DifficultyConfig and AttemptScore. Puzzle is a value object. | ✓ |
| Regular dataclass | Allows computed fields after construction. Less disciplined. | |

**User's choice:** Frozen dataclass

---

## Hash Scope for GEN-02

**Question 1: What gets hashed?**

| Option | Description | Selected |
|--------|-------------|----------|
| Derived state (base_shifts + k + ground_truth) | Proves RNG produced bit-for-bit identical output. Catches platform-specific RNG drift. | ✓ |
| Serialized puzzle metadata (seed + difficulty config) | Simpler. Only proves inputs round-trip, not that derivation is stable. | |
| Full puzzle JSON blob | Most comprehensive; requires serializing full derived state. | |

**User's choice:** Derived state hash (base_shifts + k + ground_truth)

---

**Question 2: Hash function and format**

| Option | Description | Selected |
|--------|-------------|----------|
| hashlib.sha256, hex digest | stdlib, no dependency, hex string is JSON-serializable and grep-able. | ✓ |
| hashlib.md5, hex digest | Faster, shorter. Collision resistance weaker but irrelevant for reproducibility. | |
| You decide | Any stdlib hash function works. | |

**User's choice:** `hashlib.sha256().hexdigest()`

---

**Question 3: When is hash mismatch detected?**

| Option | Description | Selected |
|--------|-------------|----------|
| verify_puzzle(puzzle) raises ValueError | Standalone function. Caller decides whether to catch. Puzzle construction always-valid. Test-friendly. | ✓ |
| Assert in generate_puzzle() before returning | Self-check on every generation call. Overhead but guarantees no wrong-hash Puzzle ever created. | |
| No auto-verification — test-only | Hash stored but never checked at runtime. Tests handle it. | |

**User's choice:** Standalone `verify_puzzle(puzzle)` function

---

## Difficulty Tier Definitions

**Question 1: Should Phase 2 define named tier presets?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — define EASY, MEDIUM, HARD presets in puzzle.py | Named DifficultyConfig constants. Phase 4 imports and matches. | ✓ |
| classify_difficulty(config) function | No hard-coded presets. Dynamic classification based on parameter ranges. Fuzzy boundaries. | |
| Defer to Phase 4 | Phase 2 only defines parameters. Phase 4 defines tiers. Less coupling but no session-time tagging. | |

**User's choice:** Define EASY, MEDIUM, HARD as module-level constants in `cipherbench/puzzle.py`

---

**Question 2: Which parameters vary across tiers?**

| Option | Description | Selected |
|--------|-------------|----------|
| All three axes vary | Alphabet size + state_change_rate + cross_char_depth all scale across tiers. | ✓ |
| Only alphabet and state_change_rate | cross_char_depth stays at 1 across all tiers. Simpler. | |
| You decide values | Lock the pattern (all three vary); planner picks specific values. | |

**User's choice:** All three axes vary. Planner picks specific values.

---

**Question 3: How is tier associated with a Puzzle?**

| Option | Description | Selected |
|--------|-------------|----------|
| Derive tier at query time via get_tier() | Puzzle stores only seed + difficulty + hash. get_tier(puzzle.difficulty) matches against presets. | ✓ |
| Store tier: str in Puzzle | generate_puzzle() stores tier name. Session JSON includes tier directly. | |

**User's choice:** `get_tier(difficulty: DifficultyConfig) -> str` at query time. No tier field in Puzzle.

---

## Claude's Discretion

- Exact parameter values for EASY/MEDIUM/HARD presets — planner should validate empirically that they produce measurably distinct complexity levels (GEN-03 success criterion)
- Exact mechanism for `cross_char_depth > 1` (multiple simultaneous offset links)
- Canonical serialization format for hashing (suggested: `json.dumps({...}, sort_keys=True).encode()`)

## Deferred Ideas

None — discussion stayed within phase scope.
