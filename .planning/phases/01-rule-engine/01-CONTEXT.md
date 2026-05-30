# Phase 1: Rule Engine - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the three-layer cipher rule engine with a locked-down information boundary. This phase delivers: the State layer (RULE-01), Cross-Character Interdependence layer (RULE-02), Hidden Feedback layer (RULE-03), the public-only `score_attempt()` interface (RULE-04), and the explicit RNG threading discipline (GEN-04).

The rule engine is the intellectual core of CipherBench. Every downstream phase depends on its correctness. Nothing else is built until this is solid and tested.

**Not in this phase:** puzzle seeding and hash verification (Phase 2), session recording, CLI, or model adapters.

</domain>

<decisions>
## Implementation Decisions

### Feedback Scoring Function (RULE-03)

- **D-01:** `AttemptScore` exposes **aggregate count only** — the number of characters in the correct position (Mastermind black-pegs only). No per-position breakdown. This is non-separable: a model cannot determine which specific positions are correct without cross-char context.
- **D-02:** Score scale = **length of the output string** (not normalized). E.g. for a 5-char output, score range is 0–5.
- **D-03:** Final answer evaluation is **exact match only (binary)**. No partial credit. Score = max (all 5 correct) or fail. Consistent with the binary success/fail scoring model.

### Cross-Character Interdependence (RULE-02)

- **D-04:** Mechanism: **index-based offset injection**. Character at input position `i` shifts the character at output position `(i + k) mod N`, where `k` is a puzzle-level parameter. Clean, tunable, mathematically well-defined.
- **D-05:** Alphabet: **configurable via difficulty parameter, defaulting to A–Z (26 chars, modulo 26)**. At higher difficulty tiers, the alphabet can expand (e.g., A–Z + 0–9). This satisfies GEN-03's configurable difficulty parameter requirement.
- **D-06:** Output string length: **fixed at 5 characters**. Matches the original design examples and creates clean symmetry with the 5-attempt limit. Consistent across all puzzles regardless of difficulty tier.

### State Evolution (RULE-01)

- **D-07:** State trigger: **round-number multiplier** applied to base shift values. Round N multiplies the base shift of each character position. E.g. if position 0 has base shift 2, round 3 applies shift 6. This matches the original `AAA → BCD` (shifts +1,+2,+3) / `BBB → DFH` (shifts +2,+4,+6) example exactly.
- **D-08:** The multiplier applies **only to base shift values**, not to the cross-char offset `k`. Separating the two layers keeps each independently testable and avoids making the combined behavior impossible to validate.

### Information Boundary (RULE-04)

- **D-09:** Enforcement mechanism: **wrapper class with private state**. `RuleEngine` class stores cipher state in private attributes (`_key`, `_shifts`, `_state`). The only public methods are `score_attempt(guess: str) -> AttemptScore` and nothing else. No `reset()`, no public key accessor.
- **D-10:** Session lifecycle: **fresh instance per session via factory function**. `create_rule_engine(seed: int, difficulty: DifficultyConfig) -> RuleEngine`. Never reuse an instance. This eliminates state-bleed risk at the architectural level (satisfies SESS-04's factory requirement as well).

### RNG Discipline (GEN-04)

- **D-11:** All generation sub-functions that need randomness **accept an explicit `rng: random.Random` parameter**. No `random.seed()` calls anywhere. The `rng` instance is constructed once at `create_rule_engine()` call time using the puzzle seed and threaded explicitly through all internal calls.

### Claude's Discretion

- The specific mathematical formula for round-multiplier state (whether it's `base_shift * round_number` or `base_shift * (round_number ** 2)` or another polynomial) is left to the planner/implementer. The constraint is that it must be deterministic given round number and produce meaningfully different outputs across rounds.
- Test strategy specifics (unit test depth, property-based test coverage, Hypothesis strategies) are left to the planner. The constraint is the 50-run determinism test (SESS-04) and that all three layers are independently testable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements

- `.planning/PROJECT.md` — Core value, constraints, key decisions (layered architecture, all-three-enhancements-in-v1)
- `.planning/REQUIREMENTS.md` — RULE-01 through RULE-04 and GEN-04 with acceptance criteria. Phase 1 traceability entries.

### Roadmap & Phase Goal

- `.planning/ROADMAP.md` §Phase 1 — Goal, success criteria, dependency note ("first phase, nothing depends on it being late")

### Research Findings

- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow, functional-core/OOP-shell pattern for rule engine, build order rationale
- `.planning/research/PITFALLS.md` — Session state bleeding (C-3), brute-force scanning via separable score (C-2), RNG non-determinism (C-4) — all must be addressed in this phase
- `.planning/research/STACK.md` — `random.Random(seed)` instance pattern, pytest + Hypothesis for combinatorial testing, Python 3.11+ target
- `.planning/research/SUMMARY.md` — Executive synthesis; critical invariants section

### No external ADRs yet — decisions fully captured above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

None — greenfield project. No existing code.

### Established Patterns

None yet. This phase establishes the foundational patterns all subsequent phases follow:
- Factory function pattern for stateful objects (`create_rule_engine()`)
- Explicit `rng: random.Random` threading (no global state)
- Private attributes with single public interface method

### Integration Points

- `score_attempt(guess: str) -> AttemptScore` is the **only** contract the Session Infrastructure (Phase 3) will call. Downstream phases depend on this signature being stable.
- `AttemptScore` dataclass fields (at minimum: `score: int`, `max_score: int`, `is_correct: bool`) will be referenced by the session recorder and scorer in later phases. Define the full dataclass here.
- `create_rule_engine(seed: int, difficulty: DifficultyConfig) -> RuleEngine` factory is the constructor contract. Phase 2 (Puzzle Generator) will call this; the `DifficultyConfig` type must be defined here.

</code_context>

<specifics>
## Specific Ideas

- The original design examples should serve as canonical test cases: `AAA → score reveals +1,+2,+3 base shifts at round 1` and `BBB → same seed, different probe → score consistent with round multiplier`. These examples are from the project brief and must pass as regression tests.
- The brute-force resistance property (non-separable aggregate score) must be verified empirically: given the 5-attempt limit, a naive alphabetic sweep strategy should NOT be able to determine full cipher state within 5 attempts. This should be a test case.
- The research identified an open question about the **minimum entropy per puzzle** needed to prevent brute-force within 5 attempts. The planner should include a task to do a quick mathematical analysis (or simulation) to validate that the chosen design (aggregate score only + cross-char mixing) achieves this before finalizing the implementation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Rule Engine*
*Context gathered: 2026-05-28*
