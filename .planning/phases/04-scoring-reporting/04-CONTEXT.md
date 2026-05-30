# Phase 4: Scoring & Reporting - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn raw session JSON files into a full scoring report. This phase delivers: a `cipherbench/scoring/` package (scorer.py, reporter.py, report_writer.py) that computes success rate (SCORE-01), per-session efficiency score (SCORE-02), AGI proximity score normalized against human baseline (SCORE-03), and per-difficulty-tier breakdowns (SCORE-04); a standalone `cipherbench score` CLI subcommand; and a live summary line printed at the end of `cipherbench run`.

**Requirements in scope:** SCORE-01, SCORE-02, SCORE-03, SCORE-04

**Not in this phase:** session inspector CLI (Phase 5), changes to rule engine, puzzle generator, or session infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Score Command Surface

- **D-01:** Scoring exposed two ways: (1) standalone `cipherbench score` subcommand reads sessions after the fact, and (2) a summary line is printed at the end of `cipherbench run` after all sessions complete. Both surfaces are required.
- **D-02:** `cipherbench score` flags:
  - `--model TEXT` (required): LiteLLM model string to score; filters by `model` field in session JSON
  - `--sessions-dir PATH` (optional, default: `./sessions`): directory to read session files from
  - `--difficulty ENUM` (optional): narrow scoring to `easy` | `medium` | `hard`
  - `--output-file PATH` (optional): write score report as JSON to this path in addition to terminal output
  - `--human` (flag, optional): score human sessions instead of model sessions (uses `runner_type='human'` and filters by `player_name` matching `--model` value, or all human sessions if `--model` omitted)
- **D-03:** Live summary printed at end of `cipherbench run` is one line only: e.g., `"3/5 success (60%) | avg efficiency: 0.72 | AGI proximity: 0.85x"`. Keeps run output clean. Full breakdown available via `cipherbench score`.

### Session Selection & Grouping

- **D-04:** Session set for scoring = all terminal sessions in the sessions directory where `outcome` is `'success'` or `'failure'`, `runner_type='model'` (or `'human'` if `--human`), and `model` matches the `--model` flag. `in_progress` and `rate_limited` sessions are skipped (non-terminal, per Phase 3 D-09).
- **D-05:** If `--difficulty` is given, additionally filter by `difficulty` field matching the tier name string.
- **D-06:** `attempts_used` in the SCORE-02 efficiency formula = count of attempt entries where `extraction_failed=False`. Extraction failures are not counted as reasoning steps.
- **D-07:** Multiple sessions for the same seed (from `--runs-per-puzzle > 1`) all contribute individually to the aggregate pool. No deduplication. Average naturally handles repeated seeds.

### AGI Proximity (SCORE-03)

- **D-08:** Human baseline matching strategy: match by difficulty tier. All human sessions (`runner_type='human'`) for the same difficulty tier as the model sessions being scored form the baseline pool. Does not require exact seed overlap.
- **D-09:** Composite score for AGI proximity normalization = average efficiency score (mean of SCORE-02 values across all sessions in the pool). AGI proximity = `model_avg_efficiency / human_avg_efficiency`.
- **D-10:** When no human baseline sessions exist (or none for the matching difficulty): AGI proximity shows `N/A (no human baseline)` in both terminal output and JSON report. Include a hint: "Run `cipherbench play` to record a human baseline." No error, no exit — report continues with the metrics that are available.

### Report Output Format

- **D-11:** Terminal output: Rich Panel header showing model name and session count, then a Rich Table with rows per difficulty tier and a totals row. Columns: `Difficulty | Sessions | Success Rate | Avg Efficiency | AGI Proximity`. Matches the existing Rich + Typer stack (D-15 from Phase 3).
- **D-12:** JSON report (written when `--output-file` is given): flat structure mirroring the terminal table:
  ```json
  {
    "model": "anthropic/claude-opus-4-7",
    "sessions_scored": 15,
    "by_difficulty": {
      "easy": {"sessions": 5, "success_rate": 0.80, "avg_efficiency": 0.72, "agi_proximity": 0.85},
      "medium": {"sessions": 7, "success_rate": 0.57, "avg_efficiency": 0.48, "agi_proximity": "N/A"},
      "hard": {"sessions": 3, "success_rate": 0.33, "avg_efficiency": 0.27, "agi_proximity": "N/A"}
    },
    "totals": {"sessions": 15, "success_rate": 0.60, "avg_efficiency": 0.52, "agi_proximity": 0.85},
    "generated_at": "2026-05-29T14:30:22Z"
  }
  ```
- **D-13:** Scorer logic location: `cipherbench/scoring/` package. Three modules:
  - `scorer.py` — pure computation functions (success rate, efficiency, AGI proximity)
  - `reporter.py` — Rich terminal output (table + panel)
  - `report_writer.py` — JSON file writer
  Mirrors the `session/` package pattern from Phase 3. No business logic in `cli/app.py`.

### Claude's Discretion

- Exact Rich table styling (column widths, color scheme, border style) — must match the visual quality of the Phase 3 human play display but exact colors are planner's choice
- How `--human` flag resolves "which human" when multiple players exist — planner may add `--player-name TEXT` if needed, or aggregate all human sessions
- Whether `agi_proximity` in JSON is a float or the string `"N/A"` — planner picks a clean representation (e.g., `null` vs string)
- Session count shown in the terminal header (total sessions found vs sessions that passed filtering)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements

- `.planning/PROJECT.md` — Core value, constraints, key decisions (no external DB, 5-attempt limit fixed, provider-agnostic)
- `.planning/REQUIREMENTS.md` — SCORE-01, SCORE-02, SCORE-03, SCORE-04 with exact formulas and acceptance criteria; Phase 4 traceability entries

### Roadmap & Phase Goal

- `.planning/ROADMAP.md` §Phase 4 — Goal (raw session JSON → scoring report), success criteria (4 conditions), requirements list

### Prior Phase Context (locked decisions Phase 4 must honor)

- `.planning/phases/03-session-infrastructure-model-adapters/03-CONTEXT.md` — D-07: `runner_type` discriminator; D-08: `AttemptEntry` fields including `extraction_failed`; D-09: outcome literals; D-10: flat `sessions/` directory; D-11: full `SessionRecord` schema; phase notes that Phase 4 skips non-terminal states

### Existing Code (must extend, not replace)

- `cipherbench/session/schema.py` — `SessionRecord` and `AttemptEntry` TypedDicts — the exact field names scorer must read
- `cipherbench/cli/app.py` — existing `run` and `play` subcommands; `score` subcommand must be added here following the same Typer + Annotated[] pattern; no business logic in this file
- `cipherbench/__init__.py` — public API surface; any new public symbols from scoring package should be exported here

### Tech Stack

- `CLAUDE.md` §Technology Stack — Typer `>=0.12` + Rich `>=13.0` for CLI and terminal output; JSON stdlib for session reading and report writing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `cipherbench/session/schema.py` — `SessionRecord.attempts` (list of `AttemptEntry`), `SessionRecord.outcome`, `SessionRecord.runner_type`, `SessionRecord.difficulty`, `SessionRecord.model` — the exact fields scorer iterates over
- `cipherbench/session/writer.py` `slugify_model()` — model slug sanitization already implemented; scorer may use it when matching `--model` input to `model` field in session JSON
- `cipherbench/cli/app.py` `_difficulty_to_config()` + `Difficulty` enum — difficulty tier enum already defined; `cipherbench score` should reuse the same `Difficulty` enum for `--difficulty` flag

### Established Patterns

- **No business logic in CLI layer**: `cli/app.py` docstring explicitly states this. `scorer.py` holds computation; `reporter.py` holds display; `cli/app.py` only wires flags and delegates.
- **`session/` package structure as template**: `scorer.py` (compute) + `reporter.py` (display) + `report_writer.py` (file I/O) mirrors `model_runner.py` / `human_runner.py` / `writer.py` separation from Phase 3.
- **glob sessions/\*.json**: All session loading via `glob('sessions/*.json')` — no SQLite index is needed for Phase 4 scope (flat directory, all JSON).
- **Rich terminal output**: Phase 3 human play (`D-15`) uses Rich Panel + Rich Table. Phase 4 terminal report uses the same components — consistent visual language.

### Integration Points

- **`cipherbench run` live summary**: After the outer `for puzzle_idx / for run_idx` loop in `cli/app.py`, call scoring functions on the sessions just written and print the one-line summary.
- **`cipherbench score` subcommand**: New `@app.command(name="score")` in `cli/app.py` — same file, same Typer app instance, same `Difficulty` enum.
- **Phase 5 (Session Inspector)**: Phase 5 reads `session_id` and `attempts` from session JSON. Phase 4 must not modify the session files — read-only access only.

</code_context>

<specifics>
## Specific Ideas

- **Efficiency formula from REQUIREMENTS.md (SCORE-02):** `success × (max_attempts - attempts_used + 1) / max_attempts` where `max_attempts = 5` (fixed, per project constraint). `success` is 1 if `outcome='success'`, 0 otherwise. `attempts_used` = count of attempts where `extraction_failed=False`.
- **AGI proximity interpretation:** A score of 1.0 means the model matches human performance; >1.0 means it outperforms the human baseline; <1.0 means it underperforms. This framing (model/human ratio) is the "AGI distance signal" from PROJECT.md core value.
- **`--human` flag for scoring human sessions:** Useful for researchers who want to see how well different human players performed, or to inspect the baseline itself before comparing to models.
- **`N/A` for AGI proximity in JSON:** Use `null` (JSON null) rather than the string `"N/A"` — cleaner for downstream scripts. Terminal display shows the string `"N/A"`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-Scoring & Reporting*
*Context gathered: 2026-05-29*
