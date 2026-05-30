# CipherBench — AGI Proximity Benchmark

## What This Is

CipherBench is a Python SDK and CLI benchmark that tests LLMs on a stateful, cross-character, feedback-hidden cipher challenge — designed to resist the pattern-recognition shortcuts that make current benchmarks too easy. Models probe a rule system with up to 5 attempts and must infer the cipher from scored feedback alone, then produce a correct final answer. Scores are compared against a human baseline (recorded via CLI play) to estimate relative AGI proximity.

## Core Value

A model that solves CipherBench has demonstrated genuine hypothesis-driven reasoning under uncertainty — not statistical pattern matching — making the gap to human performance a credible AGI distance signal.

## Current State (v1.0 — Shipped 2026-05-30)

- **5 phases, 17 plans, 149 tests** all green
- **CLI**: `cipherbench run`, `cipherbench play`, `cipherbench score`, `cipherbench inspect`
- **Providers**: Any LiteLLM-supported model (Anthropic, OpenAI, Google, 100+)
- **Storage**: Local JSON sessions + SQLite-ready schema
- **Encoding**: Option B symmetric encoding — random seeded ground truth, both guess and GT encoded through identical state+cross-char layers
- **Code quality**: Two full review passes completed, all findings resolved

## Requirements

### Validated (v1.0)

- ✓ Rule engine with three composable layers: State, Cross-Character Interdependence, Hidden Feedback — v1.0
- ✓ Information boundary enforced: all external interaction via `score_attempt()` only — v1.0
- ✓ Reproducibility: `create_rule_engine(seed)` produces identical score sequences — v1.0
- ✓ RNG discipline: no global `random.seed()` mutation; isolated `random.Random(seed)` per engine — v1.0
- ✓ Procedural puzzle generator: `generate_puzzle(seed)` with SHA-256 hash verification, EASY/MEDIUM/HARD tiers — v1.0
- ✓ Configurable difficulty: `state_change_rate` and `cross_char_depth` produce measurably distinct complexity — v1.0
- ✓ End-to-end model sessions: `cipherbench run` via LiteLLM, atomic checkpoint, rate-limit resume — v1.0
- ✓ Human baseline: `cipherbench play` records sessions in identical JSON schema — v1.0
- ✓ Scoring: success rate, efficiency score, AGI proximity vs. human baseline, per-difficulty breakdowns — v1.0
- ✓ Session inspector: `cipherbench inspect` replays stored traces with Rich display — v1.0

### Active (v2.0 targets)

- [ ] Fixed canonical puzzle set for reproducible cross-publication comparison (INTEG-01)
- [ ] Rule articulation component — model states inferred cipher rule post-solve (INTEG-02)
- [ ] Multiple cipher families to prevent meta-reasoning saturation (INTEG-03)
- [ ] `cipherbench compare` — side-by-side model vs. human sessions (EXT-01)

### Out of Scope

- Web UI / leaderboard — v1 is a personal research tool; public-facing interface deferred
- Elo / head-to-head ranking — v1 compares model to human baseline, not models to each other
- Training data export mode — benchmark is for evaluation only
- CoT scaffolding injection — would benchmark prompt engineering, not model reasoning

## Context

- Inspired by failure modes of ARC-AGI and traditional cipher benchmarks: LLMs solve them via linear pattern recognition, not structured reasoning
- The three enhancements target the three loopholes: State breaks stationarity, Cross-Char breaks position-symmetry, Hidden Feedback forces credit assignment
- Human baseline captured by same CLI that runs model sessions — same puzzle, same feedback format, same attempt limit — ensuring fair comparison
- Target models: Claude (Anthropic), GPT-4o / o1 (OpenAI), Gemini (Google), and any frontier API via LiteLLM

## Constraints

- **Tech stack**: Python — SDK-first, importable as a library and runnable as a CLI
- **Provider-agnostic**: Model runner must not bake in a single provider; use a pluggable adapter pattern
- **Reproducibility**: Every puzzle instance is seeded (RNG seed) so results are reproducible
- **No external DB**: Session data stored as local JSON files — no server infrastructure required
- **Attempt limit**: Fixed at 5 probe attempts per puzzle (a core mechanic, not configurable in v1)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| All three cipher layers in v1 | Each targets a distinct LLM shortcut; combining them is the benchmark's core thesis | Implemented (Phase 01) |
| Layered pure-function architecture | Composable layers in `engine/layers.py` let difficulty axes be tuned independently | Implemented (Phase 01) |
| Procedural generation over fixed set | Prevents memorization / dataset contamination; unlimited fresh puzzles | Implemented (Phase 02) |
| CLI for human baseline (not web UI) | Keeps v1 scope tight; human plays through same interface as model harness | Implemented (Phase 03) |
| Provider-agnostic runner (LiteLLM) | Researcher wants to test many frontier models; no provider lock-in | Implemented (Phase 03) |
| 3-module scoring split (scorer/reporter/report_writer) | scorer is pure computation; reporter handles Rich terminal; report_writer handles JSON | Implemented (Phase 04) |
| efficiency_score clamped to [0.0, 1.0] | Prevents >1.0 output for edge cases | Implemented (Phase 04) |
| Option B symmetric encoding | Random seeded GT + symmetric state+cross_char encoding; GT always scores is_correct=True on any round | Implemented (post-review fix) |
| RuleEngine enforces 5-attempt limit internally | Library callers using RuleEngine directly cannot silently exceed budget | Implemented (post-review fix) |
| SystemExit(1) from inspect_session | CLI use case only; library callers should wrap in try/except SystemExit | Accepted in Phase 05; deferred |

## Evolution

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope
2. Requirements validated? → Move to Validated
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check
3. Audit Out of Scope reasoning
4. Update Context with current state

---
*Last updated: 2026-05-30 — v1.0 milestone complete (5 phases, 17 plans, 149 tests)*
