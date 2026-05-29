# Architecture Patterns

**Domain:** Stateful cipher puzzle LLM benchmark (CipherBench)
**Researched:** 2026-05-28
**Confidence:** MEDIUM-HIGH (based on training knowledge of lm-evaluation-harness, BIG-Bench, ARC-AGI, Wordle/Mastermind-style game engines; no live web access available during this session)

---

## How Open-Source Benchmarks Structure Their Codebases

### EleutherAI lm-evaluation-harness

The harness organizes around four primary boundaries:

| Module | Responsibility |
|--------|---------------|
| `lm_eval/tasks/` | Task definitions — each task is a YAML + optional Python class describing the prompt template, dataset source, and metric |
| `lm_eval/models/` | Provider adapters — one file per provider (HuggingFace, OpenAI, Anthropic, vLLM, etc.), all implementing a common `LM` abstract base class |
| `lm_eval/evaluator.py` | Orchestrator — loads tasks, routes requests to the model adapter, collects raw outputs |
| `lm_eval/metrics/` | Pure functions that score raw outputs against references; no model or I/O awareness |

Data flow: `CLI args → evaluator.py → task(s) → model adapter → raw completions → metrics → results dict → JSON output`.

The key design insight: tasks and models are completely decoupled. A task knows nothing about which model will run it; a model knows nothing about which task produced the prompts.

### BIG-Bench

BIG-Bench uses a task-as-a-package pattern:

- Each task lives in its own subdirectory with a `task.json` (metadata) and optional `task.py` (custom scoring logic).
- A thin `evaluator` shell routes tasks to a model API and collects completions.
- Scoring is done post-hoc against stored outputs, not inline.
- The canonical split is: **task definition** (what to ask + how to score) vs. **harness** (how to ask it and store results).

### ARC-AGI

ARC-AGI is simpler because it has a fixed dataset rather than procedural generation:

- `dataset/` holds puzzle JSON files (input/output grid pairs).
- An `evaluator` script iterates puzzles, calls the model (any interface), collects answers.
- Scoring is purely binary (exact match on output grids).
- No stateful session — each puzzle is independent.

**Key difference for CipherBench:** ARC-AGI has no session state between attempts. CipherBench's multi-attempt structure with hidden feedback is architecturally closer to an interactive game engine than a standard benchmark harness.

---

## Is the Evaluator Pipeline Standard?

The pipeline `puzzle generator → model runner → session recorder → scorer → reporter` maps well to what open-source benchmarks do, with one important nuance: **the standard pipeline is not stateful**, whereas CipherBench requires statefulness within a session.

Standard benchmarks:
```
dataset/generator → prompt builder → model call → metric(prompt, completion) → results
```

CipherBench (stateful variant):
```
puzzle generator → session loop {
    prompt builder (uses history) → model call → rule engine (scores attempt)
    → history recorder (appends to session state)
} × up to 5 → final scorer (uses full session) → reporter
```

This session loop is the architectural heart of CipherBench and has no direct equivalent in lm-evaluation-harness or BIG-Bench. The closest analogues are:

- **TextWorld / ScienceWorld** — game-loop benchmarks where the model interacts with an environment across multiple turns, maintaining state between turns.
- **InterCode** — iterative code execution benchmark where the model gets stdout feedback and refines its answer.
- **ALFWorld** — embodied task benchmark with environment state between agent steps.

All of these converge on the same pattern: an **environment object** that holds authoritative state and exposes a `step(action) → (observation, score, done)` interface. This is the pattern CipherBench should follow.

---

## Provider-Agnostic Model Runner Architecture

### The Standard Pattern: Abstract Base Class + Registry

lm-evaluation-harness uses this pattern directly. The core is:

```python
class LM(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompts: list[str], **kwargs) -> list[str]: ...

    @abc.abstractmethod
    def loglikelihood(self, requests: list[tuple]) -> list[float]: ...
```

Each provider subclasses `LM`:
- `OpenAIChat(LM)` — wraps `openai.ChatCompletion`
- `AnthropicLM(LM)` — wraps `anthropic.messages.create`
- `GoogleVertexLM(LM)` — wraps Vertex AI SDK

A registry maps string names to classes so they can be specified in config:

```python
MODEL_REGISTRY = {
    "openai-chat": OpenAIChat,
    "anthropic": AnthropicLM,
    ...
}
```

### For CipherBench

The harness only needs one method from the model runner: given a list of messages (conversation history), return the model's next message. The interface is intentionally minimal:

```python
class ModelAdapter(abc.ABC):
    @abc.abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Send conversation history, receive the model's next turn."""
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable model identifier for session metadata."""
        ...
```

Config-driven instantiation: the caller passes `{"provider": "anthropic", "model": "claude-opus-4-5", "temperature": 0}` and the runner resolves this to the correct adapter. No branching in the orchestrator.

Key: **the adapter layer must be the only place that knows about provider SDKs**. Everything above it (the session loop, scorer, reporter) speaks only `list[dict]` messages and `str` responses.

---

## Stateful Rule Engine Architecture

### The Three Layers and Their Interactions

CipherBench's rule engine has three composable layers as specified in PROJECT.md:

1. **State layer** — history-dependent transformation (what the cipher does depends on what inputs have been seen)
2. **Cross-character interdependence layer** — positional mixing (character at position N affects character at position M)
3. **Hidden feedback layer** — the engine returns a score, not the ground truth

This maps well to a **middleware/pipeline pattern** where each layer wraps the previous one:

```
PlaintextInput
    ↓
[Base cipher transform]
    ↓
[State modifier — applies history-dependent offset/transform]
    ↓
[Cross-char mixer — applies positional interdependencies]
    ↓
CiphertextOutput

then:

CiphertextOutput + GroundTruth → [Hidden feedback scorer] → Score (not ground truth)
```

### Functional vs. OOP

For CipherBench, a **functional-core, OOP-shell** approach is recommended:

- The **transforms themselves are pure functions**: `apply_state_layer(plaintext, cipher_params, history) -> ciphertext`. Easy to test, reproducible, no side effects.
- The **RuleEngine class** holds mutable session state (the history list) and calls the pure functions in sequence. This is the shell.
- The **PuzzleConfig dataclass** holds all parameters that define one puzzle instance (cipher key, seed, difficulty axes, RNG state). Serializable to/from JSON.

```python
@dataclass
class PuzzleConfig:
    seed: int
    cipher_key: dict
    state_depth: int          # how far back history affects encoding
    cross_char_radius: int    # how many positions interact
    # ... other difficulty axes

class RuleEngine:
    def __init__(self, config: PuzzleConfig): ...

    def encode(self, plaintext: str) -> str:
        """Apply all three layers in sequence."""
        ...

    def score_attempt(self, guess: str, target: str) -> AttemptScore:
        """Return score-only feedback (never reveals ciphertext directly)."""
        ...

    def record_attempt(self, plaintext: str, score: AttemptScore) -> None:
        """Update internal history for state layer."""
        ...
```

### State Machine Pattern for the Session

The session (one puzzle run) is a finite state machine with these states:

```
INITIALIZED → IN_PROGRESS → COMPLETE (success) 
                          → EXHAUSTED (5 attempts, no correct answer)
                          → ABANDONED (human exits early)
```

A `Session` object owns the state transitions. The harness drives it; the session enforces invariants (cannot make attempt 6, cannot answer after COMPLETE).

---

## Hidden Feedback vs. Ground-Truth Revelation: Architectural Difference

This is a critical design point for CipherBench.

### Ground-truth benchmarks (standard)

Most benchmarks reveal the reference answer after evaluation. The scorer has access to both `model_output` and `ground_truth` at the same time. There is no information hiding concern.

Architecture consequence: scorer is a pure function, runs post-hoc, can be computed offline.

### Hidden-feedback benchmarks (CipherBench, Wordle, Mastermind)

The rule engine must act as a **trusted oracle** — it knows the ground truth but must never leak it to the model. This creates a strict information boundary:

```
┌────────────────────────────────┐
│         Rule Engine            │  ← TRUSTED ZONE: knows cipher key + ground truth
│  encode() / score_attempt()    │
└──────────┬─────────────────────┘
           │ AttemptScore only (not ciphertext, not key)
           ▼
┌────────────────────────────────┐
│      Session / Harness         │  ← UNTRUSTED ZONE: sees only what the model sees
│  prompt builder / recorder     │
└──────────┬─────────────────────┘
           │ messages (score history only)
           ▼
┌────────────────────────────────┐
│       Model Adapter            │  ← EXTERNAL: the model
└────────────────────────────────┘
```

Architectural consequence: **the rule engine is a black box to the rest of the system**. The session/harness layer must never reach into the rule engine to read `cipher_key` or `ground_truth` directly. The only interface is `score_attempt(guess) → AttemptScore`.

This boundary also protects the human baseline: when a human plays, they go through the same interface — the CLI feeds their guess to `score_attempt()` and shows them only the score. There is no code path that reveals the key during play.

For replay/inspection (the session inspector feature), the full session log (including the key) is stored encrypted or separately in the session JSON and revealed only during post-hoc replay, not during the session itself.

---

## Component Boundaries and Communication Map

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
│  `run`, `play`, `inspect`, `compare` commands               │
│  Thin: parses args, delegates to BenchmarkRunner            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   BenchmarkRunner                           │
│  Orchestrates N puzzle runs for one model/human             │
│  Aggregates per-session scores into overall results         │
│  Writes final results JSON                                  │
└──────┬────────────────────────────────────┬─────────────────┘
       │ creates N sessions                 │ reads config
┌──────▼──────────┐               ┌─────────▼──────────┐
│  SessionRunner  │               │  PuzzleGenerator   │
│  Drives one     │               │  Produces fresh    │
│  puzzle attempt │               │  PuzzleConfig from │
│  loop (≤5 tries)│               │  seed + difficulty │
└──┬──────────┬───┘               └────────────────────┘
   │          │
   │  guess   │  AttemptScore
   │          │
┌──▼──┐  ┌───▼──────────┐
│Model│  │  RuleEngine  │   ← owns cipher key, hidden state
│Adapt│  │  encode()    │
│er   │  │  score()     │
└──┬──┘  │  record()    │
   │     └──────────────┘
   │
┌──▼──────────────┐
│  SessionRecorder│   ← append-only log of every attempt
│  (in-memory +   │     plaintext, score, attempt_num, timestamp
│   JSON writer)  │
└─────────────────┘
       │
┌──────▼──────────┐
│  Scorer         │   ← pure functions
│  per-puzzle:    │     success_rate, efficiency_score
│  per-run:       │     aggregate stats, human comparison delta
└──────▼──────────┘
┌──────▼──────────┐
│  Reporter       │   ← formats output (console table, JSON file)
└─────────────────┘
```

### What Talks to What (strict rules)

| Caller | Callee | What Is Passed |
|--------|--------|---------------|
| CLI | BenchmarkRunner | run config (model, n_puzzles, seed, difficulty) |
| BenchmarkRunner | PuzzleGenerator | seed, difficulty params |
| BenchmarkRunner | SessionRunner | PuzzleConfig, ModelAdapter |
| SessionRunner | ModelAdapter | conversation messages (list[dict]) |
| SessionRunner | RuleEngine | `score_attempt(guess: str)` → AttemptScore |
| SessionRunner | SessionRecorder | AttemptRecord (guess, score, attempt_num) |
| BenchmarkRunner | Scorer | list[SessionRecord] |
| BenchmarkRunner | Reporter | ScorerOutput |

**Invariants:**
- SessionRunner never reads `cipher_key` from RuleEngine directly.
- ModelAdapter never receives AttemptScore directly; it is wrapped into a message by SessionRunner's prompt builder.
- Scorer never calls ModelAdapter.
- Reporter never calls RuleEngine.

---

## Data Flow: Puzzle State, Model Inputs, and Scores

```
PuzzleConfig (seed, key, difficulty)
    ↓
RuleEngine.__init__(config)               ← engine holds ground truth privately

--- Session loop (attempt 1..5) ---

Prompt builder assembles:
  system_prompt (rules description)
  + conversation_history (previous guesses + scores)
  + current_turn_request ("provide your next guess")
    ↓
ModelAdapter.complete(messages) → guess_str
    ↓
RuleEngine.score_attempt(guess_str) → AttemptScore
  AttemptScore: {
    attempt_num: int,
    correct: bool,
    score: float,       # normalized 0..1 similarity metric
    feedback: str       # e.g. "3/5 characters correct position"
    # notably: NOT the ciphertext, NOT the key
  }
    ↓
SessionRecorder.append(AttemptRecord)
    ↓
if AttemptScore.correct or attempt_num == 5: break

--- Post-session ---

SessionRecord: {
  puzzle_config: PuzzleConfig,       # includes key — for post-hoc inspection
  model_id: str,
  attempts: list[AttemptRecord],
  outcome: "success" | "exhausted",
  timestamp: str
}
    ↓
Scorer(sessions) → {
  success_rate: float,
  mean_attempts_on_success: float,
  efficiency_score: float,           # 1.0 = solved on attempt 1, 0.2 = solved on attempt 5
  human_delta: float | None          # if human baseline exists for same puzzles
}
    ↓
Reporter → console table + results/run_{id}.json
```

The `PuzzleConfig` (including the cipher key) travels in the session record for post-hoc replay but is never surfaced to the model or the prompt builder during the live session.

---

## Suggested Build Order

The dependency graph drives the build order. Components that are depended on by everything else must be built first.

### Layer 0 — Core Data Contracts (no dependencies)

Build these first because every other component imports them.

1. **Data types / schemas** — `PuzzleConfig`, `AttemptRecord`, `SessionRecord`, `AttemptScore`, `ScorerOutput`. These are pure dataclasses with no logic. Define them in `cipherbench/types.py`.

Rationale: Every other module imports these types. If they change after other modules are built, you get cascading refactors.

### Layer 1 — Rule Engine (depends on: data types only)

2. **Base cipher + state + cross-char transform** — The pure encoding functions first (no session state).
3. **RuleEngine class** — wraps the pure functions, holds history, implements `score_attempt()`.
4. **Hidden feedback scorer** — the function that converts `(guess, encoded_target)` into an `AttemptScore` without revealing the target.

Rationale: This is the intellectual core of CipherBench and the highest-risk component. Build and test it in isolation before anything else touches it. A bug here invalidates all benchmark results.

### Layer 2 — Puzzle Generator (depends on: data types, rule engine)

5. **PuzzleGenerator** — given a seed and difficulty config, produces a `PuzzleConfig`. Must be able to reconstruct the same puzzle from the same seed (reproducibility requirement).

Rationale: Needed by both the session runner and the human baseline CLI. Build once, shared.

### Layer 3 — Session Infrastructure (depends on: data types, rule engine, puzzle generator)

6. **SessionRecorder** — append-only log, serializes to JSON. Pure I/O, no logic.
7. **SessionRunner** — the attempt loop. Calls rule engine, records attempts, enforces attempt limit, manages `INITIALIZED → IN_PROGRESS → COMPLETE/EXHAUSTED` transitions.

Rationale: SessionRunner is where everything connects. Build it only after its dependencies (rule engine, recorder) are solid.

### Layer 4 — Model Adapter (depends on: data types only)

8. **ModelAdapter ABC** — the abstract base class with `complete(messages) → str`.
9. **Concrete adapters** — `AnthropicAdapter`, `OpenAIAdapter`, `GoogleAdapter`. Build the one you'll test with first; others follow the same pattern.

Note: This layer can be built in parallel with Layer 2-3 because it only depends on Layer 0 data types. The SessionRunner connects them.

### Layer 5 — Scoring and Reporting (depends on: data types, session infrastructure)

10. **Scorer** — pure functions over `list[SessionRecord]`. No I/O.
11. **Human baseline comparison** — reads stored human sessions, computes delta. Extension of Scorer.
12. **Reporter** — formats ScorerOutput to console and JSON file.

### Layer 6 — Orchestration and CLI (depends on: everything)

13. **BenchmarkRunner** — orchestrates N sessions, calls generator + session runner + scorer + reporter.
14. **CLI commands** — `run`, `play` (human baseline), `inspect` (session replay).

### Build Order Summary

```
Layer 0: types.py
Layer 1: rule_engine/ (cipher, state, cross_char, feedback)
Layer 2: generator.py
Layer 3: recorder.py, session_runner.py       ← can parallel with Layer 4
Layer 4: adapters/ (ABC + concrete)           ← can parallel with Layer 3
Layer 5: scorer.py, reporter.py
Layer 6: runner.py, cli.py
```

**Critical path:** types → rule engine → session runner → CLI. Everything else branches off this spine.

---

## Architecture Anti-Patterns to Avoid

### Anti-Pattern 1: Leaking Ground Truth Through the Session Layer
**What goes wrong:** SessionRunner or prompt builder reads `rule_engine.cipher_key` to construct a "helpful" context message.
**Why bad:** Invalidates the benchmark — model gets information it shouldn't have.
**Prevention:** RuleEngine exposes no public attribute for `cipher_key`. Access is only through `score_attempt()`.

### Anti-Pattern 2: Baking Provider Logic into the Session Runner
**What goes wrong:** `SessionRunner` has `if provider == "anthropic": ... elif provider == "openai": ...` branching.
**Why bad:** Adding a new provider requires modifying core session logic. Tests break. Untestable in isolation.
**Prevention:** `SessionRunner` accepts a `ModelAdapter` instance. Provider selection happens at the CLI/config layer before `SessionRunner` is instantiated.

### Anti-Pattern 3: Stateful Scorer
**What goes wrong:** Scorer accumulates state across calls; results from run A affect run B.
**Why bad:** Non-reproducible results. Order-dependent behavior.
**Prevention:** Scorer is a module of pure functions: `score_sessions(sessions: list[SessionRecord]) -> ScorerOutput`. No class, no state.

### Anti-Pattern 4: Monolithic Session Record with Inline Scoring
**What goes wrong:** `score_attempt()` both records the attempt AND computes final metrics.
**Why bad:** Cannot re-score sessions with a different metric without re-running the model. Cannot replay sessions.
**Prevention:** Record raw data (`guess`, `AttemptScore`) separately from final metrics. Scorer runs over the stored record.

### Anti-Pattern 5: Fixed Prompt Template in SessionRunner
**What goes wrong:** The prompt string is hardcoded in `session_runner.py`.
**Why bad:** Changing the prompt format (a common research iteration) requires touching core session logic.
**Prevention:** `PromptBuilder` is a separate, injectable component. `SessionRunner` calls `prompt_builder.build(history)` and passes the result to the adapter.

---

## Scalability Considerations

CipherBench v1 is a personal research tool — the primary concern is correctness and reproducibility, not throughput. That said:

| Concern | At 10 puzzles (v1) | At 1000 puzzles (future) | At 10K puzzles |
|---------|-------------------|--------------------------|----------------|
| Session storage | JSON files per run | JSON + JSONL per run | SQLite or DuckDB |
| API rate limits | Sequential is fine | Add `asyncio` + rate limiter | Async + batching |
| Parallelism | Single-threaded | `ThreadPoolExecutor` per session | Async model calls |
| Result analysis | In-memory Scorer | In-memory still fine | Pandas/DuckDB query |

For v1: keep everything synchronous and single-threaded. Design the `SessionRunner` interface so it is straightforward to wrap in `asyncio.gather` later without changing its internal logic.

---

## Sources

- Training knowledge of EleutherAI/lm-evaluation-harness (v0.4.x architecture, verified through public GitHub and papers)
- Training knowledge of BIG-Bench task-as-package structure (google/BIG-bench)
- Training knowledge of ARC-AGI evaluation design (fchollet/ARC-AGI)
- TextWorld/InterCode/ALFWorld as precedents for interactive multi-turn benchmark environments
- Wordle/Mastermind as precedents for hidden-feedback game-loop architecture
- PROJECT.md requirements (layered rule engine, 5-attempt limit, provider-agnostic runner, local JSON storage)

**Confidence notes:**
- Component boundaries and data flow: HIGH (derived from PROJECT.md requirements + well-established patterns)
- lm-evaluation-harness module structure: MEDIUM (training knowledge, no live verification available)
- Build order: HIGH (derived from dependency analysis, not from external sources)
- Hidden-feedback architecture: HIGH (well-established from Wordle-class systems)
