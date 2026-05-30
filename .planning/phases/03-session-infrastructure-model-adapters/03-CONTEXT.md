# Phase 3: Session Infrastructure & Model Adapters - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the first runnable end-to-end benchmark. This phase produces: the session runner (`cipherbench run`) that feeds puzzles to a model via LiteLLM and records each session as a JSON file; the human play command (`cipherbench play`) with identical prompt and feedback format; the LiteLLM adapter (`complete(messages) -> str`) with token budget check, exponential backoff, and per-attempt checkpointing; and the probe extraction layer (regex + fallback). A 50-run sequential determinism test (SESS-04) must pass.

**Requirements in scope:** SESS-01, SESS-02, SESS-04, ADAPT-01, ADAPT-02, ADAPT-03, ADAPT-04

**Not in this phase:** scoring or AGI proximity computation (Phase 4), session inspector CLI (Phase 5), or any changes to the rule engine or puzzle generator.

</domain>

<decisions>
## Implementation Decisions

### Probe Format & Prompt Template

- **D-01:** Probe submission format: `PROBE: ABCDE` — the model (and human) must prefix each attempt with the literal tag `PROBE:` followed by a space and exactly 5 characters matching the puzzle's alphabet. Primary regex: `r'PROBE:\s*([A-Z]{5})'` (adjusted for alphabet at runtime).
- **D-02:** Final answer format: `ANSWER: ABCDE` — after all 5 probe attempts are used, the model is prompted to submit a final answer using the `ANSWER:` tag. This is a separate 6th model call, not one of the probe attempts. Primary regex: `r'ANSWER:\s*([A-Z]{5})'`.
- **D-03:** Prompt content: minimal — tells the model the rules and format only. No worked examples, no strategy hints. Exact content: the number of attempts, the scoring mechanic (number of characters in the correct position, no per-position breakdown), the `PROBE: XXXXX` format, and the `ANSWER: XXXXX` format for the final answer. This tests pure model reasoning, not prompt engineering.
- **D-04:** Feedback presented back after each scored attempt: full attempt history in each message. Every message in the session's conversation includes a running table of all attempts and scores so far (attempt N, probe submitted, score M/5). No per-position breakdown is ever included — stays within RULE-03's information boundary.
- **D-05:** Fallback behavior when no valid `PROBE: XXXXX` is found in the model's response: mark the attempt as invalid (record in attempts list with `probe: null`, `score: null`, `is_correct: false`, `extraction_failed: true`), do NOT consume an attempt count, log the raw response, and continue. Human input validation: re-prompt if the string length or characters are invalid.

### Session JSON Schema

- **D-06:** Session file naming: `{YYYYMMDD}T{HHMMSS}-{model-slug}.json` (e.g., `20260529T143022-claude-opus.json`). The model slug is the model string with `/` and special characters replaced by `-`. Human sessions: `{YYYYMMDD}T{HHMMSS}-human-{player-name}.json` (e.g., `20260529T143022-human-alice.json`).
- **D-07:** `runner_type` field at session root: `'model'` | `'human'`. This is the canonical way Phase 4 (scoring) and Phase 5 (inspector) distinguish session types. Do not use null-model convention.
- **D-08:** Each attempt entry structure:
  ```json
  {
    "attempt_num": 1,
    "probe": "ABCDE",
    "score": 3,
    "max_score": 5,
    "is_correct": false,
    "raw_response": "...",
    "extraction_failed": false
  }
  ```
  `raw_response` is the full model text for model sessions; `null` for human sessions. `extraction_failed` is `true` if fallback triggered; `false` otherwise. `probe` is `null` if extraction completely failed.
- **D-09:** Session outcome field values: `'success'` | `'failure'` | `'rate_limited'` | `'in_progress'`. `in_progress` is written at session start and overwritten on terminal state. `rate_limited` is written when hybrid backoff is exhausted. Phase 4 scoring skips non-terminal states (`in_progress`, `rate_limited`).
- **D-10:** Session files are stored in a flat `sessions/` directory at the project root. All session types (model and human) coexist in the same directory. `glob('sessions/*.json')` loads all sessions.
- **D-11:** Top-level session schema:
  ```json
  {
    "session_id": "20260529T143022-claude-opus",
    "runner_type": "model",
    "model": "anthropic/claude-opus-4-7",
    "player_name": null,
    "seed": 42,
    "difficulty": "medium",
    "puzzle_hash": "abc123...",
    "outcome": "success",
    "final_answer": "XYZAB",
    "attempts": [...],
    "created_at": "2026-05-29T14:30:22Z",
    "completed_at": "2026-05-29T14:30:45Z"
  }
  ```
  `player_name` is `null` for model sessions, set for human sessions. `difficulty` stores the tier name (easy/medium/hard/custom). `puzzle_hash` is copied from the `Puzzle` object for integrity.

### CLI Surface

- **D-12:** `cipherbench run` flags:
  - `--model TEXT` (required): LiteLLM model string, e.g. `anthropic/claude-opus-4-7`, `openai/gpt-4o`
  - `--seed INT` (optional, default: random): RNG seed for the puzzle
  - `--num-puzzles INT` (optional, default: 1): number of distinct puzzles to run
  - `--runs-per-puzzle INT` (optional, default: 1): number of independent sessions per puzzle (for statistical reliability)
  - `--difficulty ENUM` (optional, default: medium): easy | medium | hard
  - `--output-dir PATH` (optional, default: `./sessions`): where to write session JSON files
  - `--litellm-config PATH` (optional): path to a LiteLLM config.yaml for advanced routing

- **D-13:** `cipherbench play` flags:
  - `--player-name TEXT` (optional, default: `'human'`): stored in session JSON
  - `--seed INT` (optional, default: random): RNG seed for the puzzle
  - `--difficulty ENUM` (optional, default: medium): easy | medium | hard
  - `--output-dir PATH` (optional, default: `./sessions`)

- **D-14:** API key configuration: LiteLLM reads standard provider env vars automatically (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). No additional wiring needed for the common case. `--litellm-config` is the escape hatch for proxies and custom endpoints.

- **D-15:** `cipherbench play` human feedback display: Rich terminal output — Rich Panel for puzzle header/prompt, colored score line (green for max score, yellow for partial, red for 0), and a Rich Table showing all attempts and scores so far after each submission. Matches the Typer + Rich stack.

### Rate-Limit Checkpoint Strategy

- **D-16:** Hybrid rate-limit handling in the LiteLLM adapter: auto-retry with exponential backoff up to N attempts (N = Claude's discretion, suggested: 5). If still rate-limited after N retries, write checkpoint (partial session with `outcome='rate_limited'`) and abort the current session. Resume detection: on re-run, if a session file with `outcome='rate_limited'` exists for the same model + seed combination, offer to resume from the last completed attempt.
- **D-17:** Checkpoint strategy: inline partial session file — the session JSON is written at initialization with `outcome='in_progress'` and overwritten with each completed attempt. On session success, overwritten with `outcome='success'`. No separate `.checkpoint` file. A single glob for `sessions/*.json` with `outcome` filter handles all cases.
- **D-18:** Resume behavior: `cipherbench run` detects paused sessions (`outcome='rate_limited'`) for the same model+seed and automatically resumes from the last completed attempt without a separate `--resume` flag. The resumed session file is updated in-place.

### Claude's Discretion

- Max retry count (N) for exponential backoff — suggested 5; planner picks a sensible value
- Exact backoff formula (e.g., `2^n` seconds with jitter cap) — any standard exponential backoff is fine
- Exact prompt template text — must be minimal per D-03; planner writes the actual wording
- Regex patterns for `PROBE:` and `ANSWER:` extraction — primary + fallback per D-01/D-02
- Token budget threshold for ADAPT-02 warning (e.g., warn if projected session > 80% of context window)
- Session file name slug sanitization rules (e.g., how `anthropic/claude-opus-4-7` maps to `claude-opus-4-7`)
- Rich table column layout and color scheme for the attempt history display

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements

- `.planning/PROJECT.md` — Core value, constraints, key decisions (provider-agnostic, no external DB, 5-attempt limit fixed)
- `.planning/REQUIREMENTS.md` — SESS-01, SESS-02, SESS-04, ADAPT-01, ADAPT-02, ADAPT-03, ADAPT-04 with acceptance criteria; Phase 3 traceability entries

### Roadmap & Phase Goal

- `.planning/ROADMAP.md` §Phase 3 — Goal (benchmark runnable end-to-end), success criteria (5 conditions), UI hint

### Prior Phase Context (locked decisions that Phase 3 must not break)

- `.planning/phases/02-puzzle-generator/02-CONTEXT.md` — D-04/D-05: `puzzle.create_engine()` is the only authorized way to get a `RuleEngine`; never call `create_rule_engine()` directly from session code. D-10/D-12: `get_tier()` and tier presets for difficulty.
- `.planning/phases/01-rule-engine/01-CONTEXT.md` — D-09: `RuleEngine` class private state; D-10: fresh instance per session via factory; D-11: explicit RNG threading (no global `random.seed()`); ADAPT-01 `complete(messages) -> str` boundary

### Existing Code (must extend, not replace)

- `cipherbench/__init__.py` — public API surface; Phase 3 imports `Puzzle`, `generate_puzzle`, `EASY`, `MEDIUM`, `HARD` from here
- `cipherbench/puzzle.py` — `Puzzle.create_engine()` — Phase 3 calls this per session (never reuse)
- `cipherbench/types.py` — `AttemptScore` fields: `score`, `max_score`, `is_correct` — these map to attempt entry fields in the session JSON (D-08)

### Tech Stack

- `CLAUDE.md` §Technology Stack — LiteLLM `>=1.40` for `complete()`, Typer `>=0.12` + Rich `>=13.0` for CLI, JSON stdlib for session storage

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `Puzzle.create_engine() -> RuleEngine` (`cipherbench/puzzle.py`) — Phase 3 calls this at session initialization to get a fresh engine. Never cache or reuse across sessions.
- `generate_puzzle(seed, difficulty) -> Puzzle` (`cipherbench/puzzle.py`) — the only authorized puzzle constructor; session runner calls this with the configured seed and difficulty.
- `EASY`, `MEDIUM`, `HARD` (`cipherbench/puzzle.py`) — imported by the session runner to map `--difficulty` CLI flags to `DifficultyConfig` instances.
- `get_tier(difficulty) -> str` (`cipherbench/puzzle.py`) — called at session record time to store the tier name in the session JSON.
- `AttemptScore` (`cipherbench/types.py`) — `score`, `max_score`, `is_correct` fields map directly to attempt entry fields in the session JSON (D-08).

### Established Patterns

- **Factory function pattern:** `generate_puzzle()` and `create_rule_engine()` are the authorized constructors. Phase 3 must follow the same pattern for session creation — a factory function that returns a fresh, configured session object.
- **Explicit RNG threading (D-11 from Phase 1):** Session infrastructure must not call `random.seed()` globally. Any RNG usage (e.g., random seed generation for `--num-puzzles`) must use `random.Random()` instances.
- **Frozen dataclass as value object:** `Puzzle`, `AttemptScore`, `DifficultyConfig` are all frozen. Session code must not mutate these objects.
- **Private state enforcement (D-09):** `RuleEngine` has no public attribute access. All interaction is via `score_attempt(guess: str) -> AttemptScore`.

### Integration Points

- **Phase 4 (Scoring):** Reads session JSON files from `sessions/`. Filters by `runner_type`, `outcome`, `difficulty`. Schema decisions here (D-06 through D-11) are locked constraints for Phase 4.
- **Phase 5 (Session Inspector):** `cipherbench inspect <session-id>` resolves by matching `session_id` field in the JSON (or filename prefix). Attempt history structure (D-08) is the display source.
- **LiteLLM adapter (ADAPT-01):** `complete(messages: list[dict]) -> str` interface. The adapter is a thin wrapper around `litellm.completion()`. Session runner calls it per probe attempt and for the final answer step.

</code_context>

<specifics>
## Specific Ideas

- **Inline checkpoint pattern (D-17):** Writing the session JSON at initialization with `outcome='in_progress'` and updating it after each attempt means the file is always present and parseable. If the process is killed mid-session, the partial session is recoverable. This avoids a separate `.checkpoint` file and keeps the `sessions/` directory clean.
- **`runs-per-puzzle` for statistical reliability:** A single model run on a single puzzle is noisy. `--runs-per-puzzle 5` generates 5 independent session files for the same seed — Phase 4 averages across them for a reliable success rate. This is how the benchmark is meant to be used for publication-quality results.
- **SESS-04 determinism test:** 50 sequential sessions from the same seed + model must produce identical outcomes. This test validates the combined RNG discipline across the entire stack (puzzle generator + rule engine + session infrastructure). The test must use a mock adapter (not a real API call) to control model responses, but the full session + puzzle + engine stack must be real.
- **`difficulty` stored as tier name string:** `get_tier(puzzle.difficulty)` returns `'easy'`/`'medium'`/`'hard'`/`'custom'` — this string is stored in the session JSON. Phase 4 groups sessions by this field for SCORE-04 breakdown. Do not store the full `DifficultyConfig` object in the JSON (too verbose).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-Session Infrastructure & Model Adapters*
*Context gathered: 2026-05-29*
