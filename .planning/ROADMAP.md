# Roadmap: CipherBench

## Overview

CipherBench is built from the inside out: the rule engine (the core mechanic) is established first with its information boundary locked down, then puzzles are layered on top, then session infrastructure and model adapters are delivered together so the benchmark is immediately runnable end-to-end with real API calls, then scoring turns raw sessions into AGI proximity signals, and finally the session inspector closes the CLI surface. Each phase delivers a vertically complete, verifiable slice that the next phase depends on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Rule Engine** - Implement the three-layer cipher rule engine with enforced information boundary (completed 2026-05-28)
- [x] **Phase 2: Puzzle Generator** - Build reproducible, seeded puzzle generation with configurable difficulty (completed 2026-05-28)
- [ ] **Phase 3: Session Infrastructure & Model Adapters** - Make the benchmark runnable end-to-end with real model API calls
- [ ] **Phase 4: Scoring & Reporting** - Compute success rate, efficiency, AGI proximity, and difficulty breakdowns
- [ ] **Phase 5: Session Inspector** - Add CLI replay and inspection of stored session traces

## Phase Details

### Phase 1: Rule Engine
**Goal**: The three-layer cipher rule engine exists with a locked-down information boundary — all downstream code is forced to interact through `score_attempt()` only
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: RULE-01, RULE-02, RULE-03, RULE-04, GEN-04
**Success Criteria** (what must be TRUE):
  1. Submitting the same probe string in two different rounds of the same session produces two different encoded outputs (state layer is active)
  2. Changing one input character while holding all others fixed causes a change in a non-corresponding output position (cross-character interdependence is active)
  3. `score_attempt(guess)` returns only a correctness count — the cipher key and ground-truth ciphertext cannot be retrieved from any public interface
  4. All generation sub-functions accept an explicit `rng` parameter; a grep for `random.seed(` in the generation path returns zero matches
**Plans**: TBD

### Phase 2: Puzzle Generator
**Goal**: The generator produces reproducible, hash-verified puzzles from integer seeds and exposes configurable difficulty parameters
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: GEN-01, GEN-02, GEN-03
**Success Criteria** (what must be TRUE):
  1. Running the generator twice with the same seed yields identical puzzles in any environment (reproducibility holds across process restarts)
  2. Replaying the same seed asserts the same stored hash — a mutated seed produces a hash mismatch error
  3. Configuring different difficulty parameters (alphabet range, state-change rate, cross-char mixing depth) produces measurably distinct puzzle complexity levels
**Plans**: 3 plans

Plans:

**Wave 1**
- [x] 02-01-PLAN.md — Extend DifficultyConfig (state_change_rate, cross_char_depth) + add apply_cross_char_layer_multi to layers.py

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-02-PLAN.md — Update create_rule_engine and RuleEngine to consume new DifficultyConfig fields (k_list, state_change_rate)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-03-PLAN.md — Create cipherbench/puzzle.py (Puzzle, generate_puzzle, verify_puzzle, get_tier, EASY/MEDIUM/HARD) + test suite

**Cross-cutting constraints:**
- All 47 Phase 1 tests must pass at every wave boundary
- No global `random.seed()` calls anywhere in the generation path (GEN-04 discipline)

### Phase 3: Session Infrastructure & Model Adapters
**Goal**: The benchmark is runnable end-to-end with real model API calls — a model session and a human session can both be completed, recorded as JSON, and distinguished by outcome; the adapter layer connects any LiteLLM-supported provider without code changes
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: SESS-01, SESS-02, SESS-04, ADAPT-01, ADAPT-02, ADAPT-03, ADAPT-04
**Success Criteria** (what must be TRUE):
  1. `cipherbench run` feeds puzzles to a real model via LiteLLM, records each session as a JSON file containing model name, seed, all attempts with scores, final answer, and outcome
  2. `cipherbench play` presents the same puzzle to a human via CLI with identical prompt and feedback format as the model run, recording to the same JSON schema
  3. Running 50 sequential sessions from the same seed produces identical session outcomes (determinism test passes)
  4. A single `complete(messages) -> str` interface routes to Anthropic, OpenAI, and Google without adapter-specific code in the caller; a rate-limit response triggers exponential backoff with per-attempt checkpointing
  5. The adapter extracts a valid probe string from freeform model output using regex with fallback parsing — sessions do not fail due to minor formatting variation in model responses
**Plans**: 5 plans
**UI hint**: yes

Plans:

**Wave 0**
- [x] 03-01-PLAN.md — Environment setup: add litellm/typer/rich/tenacity dependencies + CLI entry point to pyproject.toml; create all Phase 3 test stubs

**Wave 1** *(blocked on Wave 0 completion)*
- [x] 03-02-PLAN.md — Adapter + extraction contracts: LiteLLMAdapter (complete, check_token_budget, tenacity retry), SessionRecord/AttemptEntry TypedDicts, extract_probe/extract_answer, build_system_prompt/build_user_turn

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 03-03-PLAN.md — Model session runner: SessionWriter (atomic checkpoint), ModelSessionRunner (probe loop, extraction, rate-limit, inline checkpoint), create_model_session factory

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 03-04-PLAN.md — Human runner + CLI: HumanSessionRunner (typer.prompt loop, Rich display, same JSON schema), cipherbench run/play Typer subcommands, human-verify checkpoint

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 03-05-PLAN.md — Determinism gate: SESS-04 50-run sequential determinism test, different-seeds test, global-random-non-pollution test

**Cross-cutting constraints:**
- All prior phase tests must pass at every wave boundary
- No global `random.seed()` calls anywhere in session or adapter code (D-11 discipline)
- Session JSON schema (D-08, D-11) locked — Phase 4 and Phase 5 depend on it

### Phase 4: Scoring & Reporting
**Goal**: Raw session JSON is turned into a full scoring report — success rate, efficiency score, AGI proximity score, and per-difficulty breakdowns are all computable
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: SCORE-01, SCORE-02, SCORE-03, SCORE-04
**Success Criteria** (what must be TRUE):
  1. Scorer reports the percentage of sessions in a run where the model produced the correct final answer (success rate across N sessions)
  2. Each session receives an efficiency score computed as `success × (max_attempts - attempts_used + 1) / max_attempts`
  3. Given at least one recorded human baseline session, the scorer produces an AGI proximity score that normalizes the model's composite score against the human composite score for the same puzzle set
  4. Score report breaks down all metrics by difficulty tier (easy / medium / hard) derived from puzzle config parameters
**Plans**: TBD

### Phase 5: Session Inspector
**Goal**: Any recorded session can be replayed and inspected in full via CLI — every probe, every score, and the final outcome are displayed in sequence
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: SESS-03
**Success Criteria** (what must be TRUE):
  1. `cipherbench inspect <session-id>` displays each probe attempt, the score returned for that attempt, and the final answer with pass/fail outcome in the order they occurred
  2. Inspecting a human session and a model session on the same puzzle produces equivalent trace formats — there is no schema divergence between the two session types
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Rule Engine | 3/3 | Complete    | 2026-05-28 |
| 2. Puzzle Generator | 3/3 | Complete    | 2026-05-28 |
| 3. Session Infrastructure & Model Adapters | 2/5 | In Progress|  |
| 4. Scoring & Reporting | 0/TBD | Not started | - |
| 5. Session Inspector | 0/TBD | Not started | - |
