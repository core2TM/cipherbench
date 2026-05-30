# Phase 1: Rule Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 1-Rule Engine
**Areas discussed:** Feedback scoring function, Cross-char mixing design, State evolution trigger, Information boundary enforcement

---

## Feedback Scoring Function

| Option | Description | Selected |
|--------|-------------|----------|
| Aggregate count only | "N correct" — Mastermind black-pegs only. Non-separable. | ✓ |
| Count + wrong-position count | Wordle-style: correct position + wrong position counts. More signal. | |
| Binary direction only | "Better/Worse/Same" than last attempt. Minimal leakage. | |

**User's choice:** Aggregate count only (Recommended)
**Notes:** Brute-force resistance is the primary motivation. Non-separable scoring prevents systematic position-by-position scanning.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Length of output string (0–5) | Score = chars in correct position. Scale varies with puzzle size. | ✓ |
| Fixed scale 0–10 | Normalized regardless of output length. | |
| Percentage (0.0–1.0) | Float — may leak precision. | |

**User's choice:** Length of output string
**Notes:** For 5-char output (fixed), score range is 0–5.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Exact match only (binary) | Score = max or fail. Clean signal. | ✓ |
| Score threshold (≥ 80% correct) | Partial success counts. | |
| You decide | Use exact match — consistent with requirements. | |

**User's choice:** Exact match only (binary)
**Notes:** Consistent with binary success/fail decision captured in REQUIREMENTS.md Out of Scope.

---

## Cross-Char Mixing Design

| Option | Description | Selected |
|--------|-------------|----------|
| Index-based offset injection | Char at pos i shifts output at pos (i+k) mod N. Tunable. | ✓ |
| Accumulator pattern | Sum all input chars into a global offset. All positions affected equally. | |
| Conditional trigger | Duplicate chars activate special mixing rule. Nonlinear. | |

**User's choice:** Index-based offset injection (Recommended)
**Notes:** Mathematically clean, tunable difficulty via `k` parameter.

---

| Option | Description | Selected |
|--------|-------------|----------|
| A–Z only (26 chars, modulo 26) | Simplest. Matches original design examples. | |
| A–Z + 0–9 (36 chars) | Larger alphabet increases entropy. | |
| Configurable via difficulty param (default A–Z) | GEN-03 difficulty knob covers this. | ✓ |

**User's choice:** Configurable via difficulty param (default A–Z)
**Notes:** Alphabet range is one of the GEN-03 configurable difficulty parameters.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed at 5 characters | Matches original examples and 5-attempt symmetry. | ✓ |
| Variable, set by difficulty param | Longer strings at harder difficulties. | |
| Fixed at 3 characters | Too easy — lower entropy. | |

**User's choice:** Fixed at 5 characters (Recommended)
**Notes:** 5-char output, 5-attempt limit — clean design symmetry.

---

## State Evolution Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Round number multiplier | Round N multiplies base shift values. Deterministic, matches original examples. | ✓ |
| Previous probe's content | Model's last probe determines next rules. Strongest temporal dependency. | |
| Pre-computed rule schedule | Seed-derived sequence of N rule sets. Deterministic, simple to test. | |

**User's choice:** Round number multiplier (Recommended)
**Notes:** Directly matches the original design: AAA→BCD (+1,+2,+3 at round 1), BBB→DFH (+2,+4,+6 at round 2).

---

| Option | Description | Selected |
|--------|-------------|----------|
| Base shift values | Round N multiplies each position's base shift. | ✓ |
| Cross-char offset k | k changes with round — combines two layers of change. | |
| Both shift and k | Maximum complexity — may be unsolvable. | |

**User's choice:** Base shift values only (Recommended)
**Notes:** Keeps state layer and cross-char layer independently testable.

---

## Information Boundary Enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Wrapper class with private state | Private `_key`, `_shifts`. Only `score_attempt()` public. | ✓ |
| `__all__` restriction on module | Convention-based. Key still accessible via introspection. | |
| Separate internal module | `_engine` module vs. `engine` public module. Strongest boundary. | |

**User's choice:** Wrapper class with private state (Recommended)
**Notes:** Cleanest Python enforcement. Structural, not convention-based.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Fresh instance every time | Factory function `create_rule_engine()`. No reset(). | ✓ |
| reset() method | Allows replaying without re-instantiation. | |

**User's choice:** Fresh instance every time (Recommended)
**Notes:** Eliminates state-bleed risk at the architectural level.

---

## Claude's Discretion

- Exact polynomial formula for round multiplier (e.g. `shift * round` vs. `shift * round^2`)
- Unit test depth and Hypothesis strategy specifics
- Whether to include an entropy/brute-force-resistance mathematical analysis as a task (recommended by research)

## Deferred Ideas

None — discussion stayed within phase scope.
