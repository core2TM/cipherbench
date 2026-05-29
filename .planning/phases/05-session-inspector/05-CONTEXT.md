# Phase 5: Session Inspector - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `cipherbench inspect <session-id>` CLI subcommand that replays a stored session trace, displaying each probe attempt with its score and the final answer with pass/fail outcome. This phase delivers: a `cipherbench/session/inspector.py` module (or similar) with session-lookup and display logic, and an `inspect` subcommand wired into `cipherbench/cli/app.py`.

**Requirements in scope:** SESS-03

**Not in this phase:** new session fields, changes to how sessions are written, scoring logic, or any changes to the rule engine, puzzle generator, or existing session runners.

</domain>

<decisions>
## Implementation Decisions

### Session-ID Resolution

- **D-01:** Prefix/substring match strategy — `inspect` searches `./sessions/*.json` (or `--sessions-dir`) and matches any file whose stem (filename without `.json`) contains the given `<session-id>` argument as a substring (case-insensitive).
- **D-02:** Exactly 1 match → load and display the session. 0 matches → error with list of all available session IDs. 2+ matches → error with "Ambiguous: matched N sessions" plus the list of matching IDs so the user can narrow down.

### Output Format

- **D-03:** Header: Rich Panel at the top showing: `session_id`, `runner_type` (model/human), `seed`, `difficulty`, `outcome`. Matches the visual language of `cipherbench score` and `cipherbench play`.
- **D-04:** Attempts body: Rich Table with columns — `Attempt | Probe | Score | Correct?`. One row per attempt entry in order of `attempt_num`.
- **D-05:** Extraction failures: shown in the table with `Probe = — (extraction failed)`, `Score = —`, `Correct? = ✗`. Not hidden — they are part of the session record.
- **D-06:** Footer: one line below the table showing the final answer and outcome — e.g., `Final answer: XYZAB — ✓ Success` or `Final answer: XYZAB — ✗ Failure`. If `final_answer` is null (e.g., session was rate-limited before reaching the answer step), show `Final answer: — (not reached)`.

### Sessions Directory

- **D-07:** `inspect` accepts `--sessions-dir PATH` (optional, default `./sessions`). Parity with `cipherbench score`. Path is resolved via `Path(...).resolve()` to prevent path traversal (consistent with T-04-06 discipline in `score` command).

### Error Handling

- **D-08:** Session not found: print `Session not found: '<session-id>'` and list all available session IDs in the directory (one per line). Exit code 1.
- **D-09:** Sessions directory missing: print `Sessions directory not found: <path>\nRun 'cipherbench run' or 'cipherbench play' to record sessions first.` Exit code 1.
- **D-10:** Sessions directory exists but is empty: print `No sessions found in: <path>` and exit 1.

### Claude's Discretion

- Exact Rich table column widths and color scheme — must feel consistent with the `score` command's Rich output but exact styling is planner's choice
- Whether to show `runner_type`-specific fields in the panel (e.g., `model` for model sessions, `player_name` for human sessions) or always show both (with `null` for the inapplicable one)
- Whether `inspector.py` lives in `cipherbench/session/` or `cipherbench/cli/` — planner picks the location that best matches existing patterns

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements

- `.planning/PROJECT.md` — Core value, constraints, key decisions (no external DB, 5-attempt limit fixed, provider-agnostic)
- `.planning/REQUIREMENTS.md` — SESS-03 acceptance criteria: inspect must display each probe attempt, the score, and the final answer with outcome; model and human sessions must produce equivalent trace formats

### Roadmap & Phase Goal

- `.planning/ROADMAP.md` §Phase 5 — Goal, success criteria (2 conditions), depends on Phase 3

### Prior Phase Context (locked decisions Phase 5 must honor)

- `.planning/phases/03-session-infrastructure-model-adapters/03-CONTEXT.md` — D-07: `runner_type` discriminator; D-08: `AttemptEntry` field definitions (attempt_num, probe, score, max_score, is_correct, raw_response, extraction_failed); D-11: full `SessionRecord` schema; D-06: session file naming convention
- `.planning/phases/04-scoring-reporting/04-CONTEXT.md` — confirms Phase 5 reads session files read-only; `score` command's `--sessions-dir` flag and `Path(...).resolve()` pattern to reuse

### Existing Code (must extend, not replace)

- `cipherbench/session/schema.py` — `SessionRecord` and `AttemptEntry` TypedDicts — the exact field names for display
- `cipherbench/cli/app.py` — existing `run`, `play`, `score` subcommands; `inspect` subcommand must be added here following the same Typer + `Annotated[]` pattern; no business logic in this file
- `cipherbench/__init__.py` — public API surface; if inspector is importable as a library function it should be exported here

### Tech Stack

- `CLAUDE.md` §Technology Stack — Typer `>=0.12` + Rich `>=13.0` for CLI and terminal output; JSON stdlib for session reading

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `cipherbench/cli/app.py` `score_command` — uses `Path(...).resolve()` for path traversal prevention; same pattern needed for `--sessions-dir` in `inspect`
- `cipherbench/cli/app.py` `Difficulty` enum — not needed directly by inspect, but the import pattern and Typer `Annotated[]` style must be matched
- `cipherbench/session/schema.py` `SessionRecord`, `AttemptEntry` — the TypedDicts that define the exact fields available for display

### Established Patterns

- **No business logic in CLI layer**: `cli/app.py` docstring enforces this. `inspect` wires flags and delegates to a module in `cipherbench/session/` or similar — no display/lookup logic in `app.py`.
- **Rich Panel + Rich Table visual language**: `cipherbench score` uses Rich Panel for the report header and Rich Table for per-difficulty rows. `inspect` should use the same components for visual consistency.
- **`glob('sessions/*.json')` session loading**: Phase 4 established this pattern for reading sessions. Inspector uses the same glob, then filters by session_id substring match.
- **`Path(...).resolve()` for user-supplied paths**: Used in `score_command` to prevent path traversal. Inspector must follow the same discipline.

### Integration Points

- **`cipherbench/cli/app.py`**: New `@app.command(name="inspect")` added in this file — same `app` instance, same Typer pattern
- **`sessions/` directory**: Inspector reads but never writes to session files (read-only access, same discipline as Phase 4)

</code_context>

<specifics>
## Specific Ideas

- **Substring matching for session-ID**: Because `session_id` is the filename stem (e.g., `20260529T143022-claude-opus`), there is no need to open every JSON file to match by `session_id` field — just `glob('sessions/*.json')` and match on the stem string. Fast and avoids deserializing all sessions.
- **Extraction failures in table**: The `extraction_failed` field in `AttemptEntry` is the authoritative flag. When `extraction_failed=True`, show `—` in the Probe column rather than showing `probe=null` literally. This keeps the table readable.
- **Format parity between model and human sessions (success criterion 2)**: The display logic must not branch on `runner_type` — both session types produce the same table layout. The only difference is `raw_response` (not displayed) and `player_name` vs `model` in the panel header.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-Session Inspector*
*Context gathered: 2026-05-29*
