# Requirements: CipherBench

**Defined:** 2026-05-28
**Core Value:** A model that solves CipherBench has demonstrated genuine hypothesis-driven reasoning under uncertainty — not statistical pattern matching — making the gap to human performance a credible AGI distance signal.

## v1 Requirements

### Rule Engine

- [ ] **RULE-01**: System applies a state layer so that submitting the same probe string in a different round produces a different encoded output (history-dependent rules)
- [ ] **RULE-02**: System applies a cross-character interdependence layer so that the shift applied to one output character depends on the value of a different input character (positional mixing defeats position-symmetric attacks)
- [ ] **RULE-03**: System applies a hidden feedback layer that returns only a correctness score (e.g. number of correctly-placed characters) — the actual encoded output is never revealed mid-session
- [ ] **RULE-04**: Rule engine exposes only `score_attempt(guess) -> AttemptScore` to the rest of the system — cipher key and ground-truth ciphertext are never accessible from outside the engine boundary

### Puzzle Generation

- [ ] **GEN-01**: Generator produces a reproducible puzzle from an integer seed — same seed always yields the same puzzle regardless of environment
- [ ] **GEN-02**: Generator computes and stores a hash of the fully-rendered puzzle at creation; replaying the same seed asserts the same hash (reproducibility proof)
- [ ] **GEN-03**: Generator exposes configurable difficulty parameters that control puzzle complexity (e.g. alphabet range, state-change rate, cross-char mixing depth)
- [ ] **GEN-04**: All generator sub-functions accept an explicit `rng: random.Random` parameter — no global `random.seed()` calls anywhere in the generation path

### Session & CLI

- [ ] **SESS-01**: `cipherbench run` command feeds a set of puzzles to a specified model via LiteLLM and records each session as a JSON file (model name, seed, all attempts + scores, final answer, outcome)
- [ ] **SESS-02**: `cipherbench play` command presents puzzles to a human via CLI with identical prompt and feedback format as the model run — records sessions to the same JSON schema
- [ ] **SESS-03**: `cipherbench inspect <session-id>` command replays a stored session trace, displaying each probe attempt, the score returned, and the final answer with outcome
- [ ] **SESS-04**: Session state is constructed fresh per session via a factory function — no shared mutable state between sessions; a 50-run sequential determinism test must pass

### Model Adapters

- [ ] **ADAPT-01**: LiteLLM adapter provides a single `complete(messages) -> str` interface that routes to any LiteLLM-supported provider (Anthropic, OpenAI, Google, etc.) via a config-supplied model string
- [ ] **ADAPT-02**: Adapter checks token budget at session initialization — warns and aborts if the projected session length exceeds the model's context window, preventing silent truncation
- [ ] **ADAPT-03**: Adapter handles rate-limit responses with exponential backoff and retry; session status is checkpointed per attempt so a rate-limited session can resume or be marked as `rate_limited` rather than lost
- [ ] **ADAPT-04**: Adapter extracts a valid probe string from the model's freeform response using regex + fallback parsing — structured output is never assumed

### Scoring & Reporting

- [ ] **SCORE-01**: Scorer computes success rate (% of sessions where the model produced the correct final answer) across all sessions for a given run config
- [ ] **SCORE-02**: Scorer computes efficiency score per session: `success × (max_attempts - attempts_used + 1) / max_attempts` — rewards solving in fewer probes; reported alongside raw success rate
- [ ] **SCORE-03**: Scorer computes an AGI proximity score: model composite score normalized by human baseline composite score for the same puzzle set (requires at least one recorded human baseline)
- [ ] **SCORE-04**: Reporter breaks down all scores by difficulty tier (easy / medium / hard) derived from puzzle config parameters

## v2 Requirements

### Benchmark Integrity

- **INTEG-01**: Fixed canonical puzzle set (hand-verified) for reproducible cross-run and cross-publication comparison
- **INTEG-02**: Rule articulation component — after solving, model is asked to state the inferred cipher rule; response is scored to detect meta-reasoning vs. genuine induction
- **INTEG-03**: Multiple cipher families to prevent meta-reasoning saturation (Caesar-family monoculture identified as a contamination risk)

### Extensibility

- **EXT-01**: `cipherbench compare` command shows model vs. human sessions side-by-side on the same puzzles
- **EXT-02**: Elo / head-to-head ranking across multiple model runs
- **EXT-03**: Web UI for remote human players contributing to the baseline pool

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI / leaderboard | v1 is a personal research tool; public-facing interface deferred to future milestone |
| Multiple cipher families | Adds generator complexity; single well-designed family is sufficient to validate the benchmark mechanics |
| Composable layer toggle (difficulty axes) | All three layers are always active in v1; toggleability deferred until mechanics are validated |
| Partial credit on final answers | Blurs the reasoning signal; binary success/fail is cleaner for AGI proximity framing |
| CoT scaffolding injection | Would benchmark prompt engineering, not model reasoning; explicitly excluded from runner |
| Training data export mode | Benchmark is for evaluation only; exporting would accelerate benchmark saturation |
| Elo / head-to-head ranking | v1 compares model to human baseline, not models to each other |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RULE-01 | Phase 1 | Pending |
| RULE-02 | Phase 1 | Pending |
| RULE-03 | Phase 1 | Pending |
| RULE-04 | Phase 1 | Pending |
| GEN-04 | Phase 1 | Pending |
| GEN-01 | Phase 2 | Pending |
| GEN-02 | Phase 2 | Pending |
| GEN-03 | Phase 2 | Pending |
| SESS-01 | Phase 3 | Pending |
| SESS-02 | Phase 3 | Pending |
| SESS-04 | Phase 3 | Pending |
| ADAPT-01 | Phase 3 | Pending |
| ADAPT-02 | Phase 3 | Pending |
| ADAPT-03 | Phase 3 | Pending |
| ADAPT-04 | Phase 3 | Pending |
| SCORE-01 | Phase 4 | Pending |
| SCORE-02 | Phase 4 | Pending |
| SCORE-03 | Phase 4 | Pending |
| SCORE-04 | Phase 4 | Pending |
| SESS-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 — Phase 3 and Phase 4 merged; old Phase 5 renumbered to Phase 4; old Phase 6 renumbered to Phase 5*
