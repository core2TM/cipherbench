# Phase 2: Puzzle Generator - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the puzzle generation layer on top of the Phase 1 rule engine. Deliverables: extend `DifficultyConfig` with two new difficulty axes, define the `Puzzle` frozen dataclass with a `create_engine()` method, implement `generate_puzzle(seed, difficulty) -> Puzzle`, compute and store a SHA-256 hash of the derived puzzle state (GEN-02), implement `verify_puzzle()` for hash assertion, and define named difficulty tier presets (EASY, MEDIUM, HARD) with a `get_tier()` lookup function.

**Requirements in scope:** GEN-01, GEN-02, GEN-03

**Not in this phase:** session recording, CLI, model adapters, scoring, or any changes to the `score_attempt()` interface.

</domain>

<decisions>
## Implementation Decisions

### DifficultyConfig Extension (GEN-03)

- **D-01:** Extend `DifficultyConfig` **in-place** in `cipherbench/types.py` — add two optional fields with defaults. The existing Phase 1 behavior is preserved: `DifficultyConfig()` with all defaults produces the same behavior as before. `create_rule_engine()` must be updated to read these fields instead of sampling them from the RNG.
- **D-02:** Add `state_change_rate: float = 1.0` to `DifficultyConfig`. Round multiplier formula changes from `base_shift * round_num` to `base_shift * (round_num * state_change_rate)`. Default `1.0` preserves current linear behavior exactly.
- **D-03:** Add `cross_char_depth: int = 1` to `DifficultyConfig`. Depth 1 = k in `[1, n-1]` (current single-offset behavior). Depth 2+ = multiple simultaneous cross-char offset links applied. The planner determines the exact multi-depth mechanism.

### Puzzle Object Shape

- **D-04:** `Puzzle` is a **frozen dataclass** in `cipherbench/puzzle.py` with fields: `seed: int`, `difficulty: DifficultyConfig`, `puzzle_hash: str`. Consistent with the frozen-dataclass-as-value-object pattern established by `DifficultyConfig` and `AttemptScore` in Phase 1.
- **D-05:** `Puzzle` has a `create_engine() -> RuleEngine` method that calls `create_rule_engine(self.seed, self.difficulty)`. Phase 3 Session Infrastructure calls `puzzle.create_engine()` per session — never reuses an engine across sessions (D-10 discipline from Phase 1 maintained).
- **D-06:** Both `Puzzle` and `generate_puzzle()` live in `cipherbench/puzzle.py`. Import path: `from cipherbench.puzzle import Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY, MEDIUM, HARD`.

### Hash Scope (GEN-02)

- **D-07:** The hash is computed from the **derived state**: `base_shifts` (list of ints) + `k` (int) + `ground_truth` (str) — the actual values produced by `create_rule_engine()` for the given seed + difficulty. This proves the RNG produced bit-for-bit identical output and catches any platform-specific RNG drift. Hashing the inputs (seed + config) would only prove round-trip, not derivation stability.
- **D-08:** Hash function: `hashlib.sha256().hexdigest()` — stdlib, no dependency, hex string is JSON-serializable and grep-able.
- **D-09:** Verification via standalone `verify_puzzle(puzzle: Puzzle) -> None` function that re-derives the hash from the puzzle's seed + difficulty and raises `ValueError('hash mismatch: expected {X}, got {Y}')` on mismatch. Caller decides whether to catch. Importable by test suites. `generate_puzzle()` stores the hash at creation; `verify_puzzle()` asserts it on replay.

### Difficulty Tier Definitions

- **D-10:** Define `EASY`, `MEDIUM`, `HARD` as module-level `DifficultyConfig` constants in `cipherbench/puzzle.py`. These are the canonical tier presets; Phase 3 session recording and Phase 4 scoring both import them.
- **D-11:** All three axes vary across tiers (alphabet size, `state_change_rate`, `cross_char_depth`). Planner picks specific parameter values that produce measurably distinct complexity levels (GEN-03 success criterion: "Configuring different difficulty parameters produces measurably distinct puzzle complexity levels"). Suggested ladder: EASY = small alphabet + rate 1.0 + depth 1; MEDIUM = A–Z + rate 1.5 + depth 2; HARD = A–Z+0–9 + rate 2.0 + depth 3.
- **D-12:** Tier is **not stored** in the `Puzzle` object. A standalone `get_tier(difficulty: DifficultyConfig) -> str` function matches the config against the three presets and returns `'easy'`/`'medium'`/`'hard'` (or `'custom'` if none match). Phase 4 calls this at score time. Puzzle stays a pure data object with no redundant fields.

### Claude's Discretion

- Exact parameter values for EASY/MEDIUM/HARD presets — the planner should simulate or analyze to ensure GEN-03's "measurably distinct complexity" is met.
- Exact mechanism for `cross_char_depth > 1` (multiple simultaneous offset links) — the planner determines the implementation, constrained by D-03.
- The canonical serialization format for hashing (e.g., how to deterministically serialize `base_shifts` list to bytes) — any stable canonical form is fine; JSON serialization with sorted keys is a reasonable starting point.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements

- `.planning/PROJECT.md` — Core value, constraints, key decisions (layered architecture, procedural generation over fixed set)
- `.planning/REQUIREMENTS.md` — GEN-01, GEN-02, GEN-03 with acceptance criteria; GEN-04 (already complete); Phase 2 traceability entries

### Roadmap & Phase Goal

- `.planning/ROADMAP.md` §Phase 2 — Goal ("generator produces reproducible, hash-verified puzzles from integer seeds"), success criteria (3 conditions), dependency on Phase 1

### Phase 1 Context (locked decisions that Phase 2 must not break)

- `.planning/phases/01-rule-engine/01-CONTEXT.md` — All Phase 1 decisions: D-05 (alphabet), D-06 (output_length=5), D-09 (frozen dataclass), D-10 (factory pattern), D-11 (explicit RNG threading). Phase 2 extends Phase 1 types — these constraints are inherited.

### Phase 1 Research (pitfalls and architecture still apply)

- `.planning/research/ARCHITECTURE.md` — Component boundaries, functional-core/OOP-shell pattern, build order
- `.planning/research/PITFALLS.md` — C-3 (session state bleeding), C-4 (RNG non-determinism) — still relevant for generator design
- `.planning/research/STACK.md` — `random.Random(seed)` instance pattern, pytest + Hypothesis for property tests

### Existing Code (must extend, not replace)

- `cipherbench/types.py` — `DifficultyConfig` (to be extended in D-01 to D-03) and `AttemptScore` (unchanged)
- `cipherbench/engine/rule_engine.py` — `create_rule_engine()` factory (must be updated to consume new `DifficultyConfig` fields D-02/D-03 instead of sampling from RNG)
- `cipherbench/engine/layers.py` — `apply_state_layer()` and `apply_cross_char_layer()` (may need signature updates to accept rate/depth params)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `create_rule_engine(seed, difficulty) -> RuleEngine` (`cipherbench/engine/rule_engine.py`) — `generate_puzzle()` calls this internally to derive `base_shifts`, `k`, and `ground_truth` for hashing. The factory is the single source of truth for puzzle derivation.
- `DifficultyConfig` frozen dataclass (`cipherbench/types.py`) — Phase 2 extends this in-place with `state_change_rate` and `cross_char_depth`. `__post_init__` validation pattern is already established; add validation for new fields there.
- `AttemptScore` and `DifficultyConfig` frozen dataclass pattern — `Puzzle` follows the same pattern: `@dataclass(frozen=True)` with `__post_init__` validation.

### Established Patterns

- **Factory function pattern:** `create_rule_engine()` is the authorized constructor. `generate_puzzle()` follows the same pattern — it's the only authorized way to construct a `Puzzle`.
- **Explicit RNG threading (D-11 from Phase 1):** All random draws go through an explicit `rng: random.Random` instance. `generate_puzzle()` must not call `random.seed()` globally.
- **Private attributes (D-09 from Phase 1):** Internal derived state (base_shifts, k) is accessed from the RuleEngine's private attributes for hashing purposes — acceptable since `generate_puzzle()` is a trusted factory function.
- **Frozen dataclass as value object:** `Puzzle(seed=42, difficulty=MEDIUM, puzzle_hash='...')` is a complete, immutable identity. Two puzzles with the same seed + difficulty are the same puzzle.

### Integration Points

- **Phase 3 (Session Infrastructure):** Receives a `Puzzle` object, calls `puzzle.create_engine()` to get a fresh `RuleEngine` per session. The `generate_puzzle()` API is the integration contract — Phase 3 must not call `create_rule_engine()` directly.
- **Phase 4 (Scoring):** Calls `get_tier(puzzle.difficulty) -> str` to classify sessions for SCORE-04 difficulty breakdown. Imports `EASY`, `MEDIUM`, `HARD` presets.
- **`create_rule_engine()` update:** Must consume `difficulty.state_change_rate` and `difficulty.cross_char_depth` instead of sampling these from RNG. This is a breaking change to the internal generation logic — ensure existing tests still pass with default config.

</code_context>

<specifics>
## Specific Ideas

- **Hash derivation order matters for stability:** When serializing `base_shifts` + `k` + `ground_truth` to bytes for hashing, use a deterministic canonical form. A simple approach: `json.dumps({"base_shifts": base_shifts, "k": k, "ground_truth": ground_truth}, sort_keys=True).encode()`. Avoids any platform-specific `repr()` or `str()` formatting.
- **verify_puzzle() is test-friendly by design:** The choice of a standalone function (vs. a method or assertion in generate_puzzle) means test suites can easily call `verify_puzzle(puzzle)` as a self-contained check after any serialization/deserialization round-trip.
- **GEN-03 validation test:** Success criterion 3 requires "measurably distinct complexity levels" — the planner should include a task to verify empirically (via simulation or analysis) that EASY/MEDIUM/HARD produce distinct score distributions with a test model.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Puzzle Generator*
*Context gathered: 2026-05-29*
