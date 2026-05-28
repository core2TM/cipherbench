# CipherBench — AGI Proximity Benchmark

## What This Is

CipherBench is a Python SDK and CLI benchmark that tests LLMs on a stateful, cross-character, feedback-hidden cipher challenge — designed to resist the pattern-recognition shortcuts that make current benchmarks too easy. Models probe a rule system with up to 5 attempts and must infer the cipher from scored feedback alone, then produce a correct final answer. Scores are compared against a human baseline (recorded via CLI play) to estimate relative AGI proximity.

## Core Value

A model that solves CipherBench has demonstrated genuine hypothesis-driven reasoning under uncertainty — not statistical pattern matching — making the gap to human performance a credible AGI distance signal.

## Requirements

### Validated

- [x] Rule engine with three composable layers: State (history-dependent rules), Cross-Character Interdependence (positional mixing), and Hidden Feedback (score-only output) — Validated in Phase 01: Rule Engine
- [x] Information boundary enforced: all external interaction via `score_attempt()` only; cipher internals not accessible — Validated in Phase 01: Rule Engine
- [x] Reproducibility: `create_rule_engine(seed)` produces identical score sequences across independent instances — Validated in Phase 01: Rule Engine
- [x] RNG discipline: no global `random.seed()` mutation; isolated `random.Random(seed)` per engine — Validated in Phase 01: Rule Engine

### Active

- [ ] Rule engine with three composable layers: State (history-dependent rules), Cross-Character Interdependence (positional mixing), and Hidden Feedback (score-only output like Wordle/Mastermind)
- [ ] Procedural puzzle generator that creates unlimited fresh puzzles with configurable difficulty axes
- [ ] CLI interface for both model runs (automated) and human play (manual baseline recording)
- [ ] Provider-agnostic model runner supporting multiple frontier APIs (Anthropic, OpenAI, Google, etc.)
- [ ] Scoring: success rate + efficiency score (attempts used) per puzzle, aggregated across N runs
- [ ] Human baseline storage — records human sessions alongside model sessions for comparison
- [ ] Session inspector — CLI command to replay and inspect a session trace (inputs, feedback, final answer)

### Out of Scope

- Web UI / leaderboard — v1 is a personal research tool; public-facing interface is a future phase
- Fixed/curated canonical puzzle set — v1 uses procedural generation only; a canonical set is a future milestone
- Elo / head-to-head ranking — v1 compares models against human baseline, not each other
- Training data generation — benchmark is for evaluation only, not for generating fine-tuning data

## Context

- Inspired by the failure modes of ARC-AGI and traditional cipher benchmarks: LLMs solve them via linear pattern recognition, not structured reasoning
- The three enhancements directly target the three loopholes: State breaks stationarity, Cross-Char breaks position-symmetry, Hidden Feedback forces credit assignment
- Human baseline is captured by the same CLI that runs model sessions — same puzzle, same feedback format, same attempt limit — ensuring fair comparison
- Target models: Claude (Anthropic), GPT-4o / o1 (OpenAI), Gemini (Google), and any other frontier API the researcher wants to plug in

## Constraints

- **Tech stack**: Python — SDK-first, importable as a library and runnable as a CLI
- **Provider-agnostic**: Model runner must not bake in a single provider; use a pluggable adapter pattern
- **Reproducibility**: Every puzzle instance is seeded (RNG seed) so results are reproducible
- **No external DB**: Session data stored as local JSON/CSV files — no server infrastructure required
- **Attempt limit**: Fixed at 5 probe attempts per puzzle (a core mechanic, not configurable in v1)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| All three enhancements in v1 | User identified each loophole independently; combining them is the point of the benchmark | Implemented (Phase 01) |
| Layered architecture for rule engine | Composable layers (base cipher + state modifier + cross-char transform + feedback mode) let difficulty axes be tuned independently | Implemented as pure functions in `engine/layers.py` (Phase 01) |
| Procedural generation over fixed set | Prevents memorization / dataset contamination; unlimited fresh puzzles | — Pending |
| CLI for human baseline (not web UI) | Keeps v1 scope tight; human plays through same interface as model harness | — Pending |
| Provider-agnostic runner | Researcher wants to test many frontier models; hardcoding one provider would require forking | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-28 — Phase 01 complete (Rule Engine)*
