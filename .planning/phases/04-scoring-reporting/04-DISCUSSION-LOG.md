# Phase 4: Scoring & Reporting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 4-Scoring & Reporting
**Areas discussed:** Score command surface, Session selection & grouping, AGI proximity matching, Report output format

---

## Score Command Surface

### Q1: Standalone vs embedded vs both?

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone `cipherbench score` | Separate command, reads sessions after the fact | |
| Auto-report at end of `cipherbench run` | Prints summary when run finishes | |
| Both | run prints live summary; score also available standalone | ✓ |

**User's choice:** Both
**Notes:** Keeps the post-hoc analysis capability via `cipherbench score` while still giving immediate feedback at the end of a run.

---

### Q2: Primary filter flag for `cipherbench score`?

| Option | Description | Selected |
|--------|-------------|----------|
| `--model TEXT` | Filter by LiteLLM model string | ✓ |
| `--sessions-dir PATH` only | No model filter — score everything | |
| `--model` + `--difficulty` filter | Score by model AND narrow to difficulty | |

**User's choice:** `--model TEXT` (recommended)
**Notes:** Primary discriminator is the model string, consistent with runner_type from Phase 3.

---

### Q3: Additional flags for `cipherbench score`?

| Option | Description | Selected |
|--------|-------------|----------|
| `--sessions-dir PATH` | Override default ./sessions | ✓ |
| `--difficulty ENUM` | Narrow to specific difficulty tier | ✓ |
| `--output-file PATH` | Write JSON report to disk | ✓ |
| `--human` flag | Score human sessions instead of model sessions | ✓ |

**User's choice:** All four flags selected
**Notes:** Full flag surface — all options selected.

---

### Q4: Live summary detail level at end of `cipherbench run`?

| Option | Description | Selected |
|--------|-------------|----------|
| Summary line only | One line: success rate + avg efficiency + AGI proximity | ✓ |
| Per-difficulty breakdown | Rich table with easy/medium/hard rows | |
| You decide | Leave exact format to planner | |

**User's choice:** Summary line only (recommended)
**Notes:** Keeps run output clean; full breakdown available via `cipherbench score`.

---

## Session Selection & Grouping

### Q1: What defines the session set for aggregation?

| Option | Description | Selected |
|--------|-------------|----------|
| All terminal sessions matching model | Outcome in (success, failure), model matches | ✓ |
| Time window (--since / --until) | Filter by date range | |
| Explicit session list (--session-ids) | User provides list of IDs | |

**User's choice:** All terminal sessions matching model (recommended)
**Notes:** Simple, no extra metadata needed. `--difficulty` narrows further.

---

### Q2: `attempts_used` for efficiency formula?

| Option | Description | Selected |
|--------|-------------|----------|
| Valid attempts only (extraction_failed=False) | Excludes parsing failures | ✓ |
| All attempts including extraction failures | Count every entry | |
| You decide | Leave to planner | |

**User's choice:** Valid attempts only (recommended)
**Notes:** Extraction failures are noise, not reasoning steps. Matches the intent of SCORE-02.

---

### Q3: Multiple runs for same seed (--runs-per-puzzle > 1)?

| Option | Description | Selected |
|--------|-------------|----------|
| Average across all runs for that seed | All N sessions contribute individually | ✓ |
| Deduplicate — most recent run per seed | Only last session per seed counts | |
| Show per-seed and aggregate | Break down per-seed AND totals | |

**User's choice:** Average across all runs for that seed (recommended)
**Notes:** Natural handling — all sessions in the aggregate pool; `--runs-per-puzzle` just adds more data points.

---

## AGI Proximity Matching

### Q1: How are model sessions matched to human baseline sessions?

| Option | Description | Selected |
|--------|-------------|----------|
| Same difficulty tier | Match all sessions of same difficulty | ✓ |
| Same seeds exactly | Only compare sessions sharing exact seed | |
| All sessions regardless of seed or difficulty | Aggregate everything | |

**User's choice:** Same difficulty tier (recommended)
**Notes:** Doesn't require exact seed overlap — works even when human played different seeds. Aligns with SCORE-04 tier breakdowns.

---

### Q2: What is the "composite score" for AGI proximity?

| Option | Description | Selected |
|--------|-------------|----------|
| Average efficiency score | Mean of SCORE-02 values | ✓ |
| Success rate only | % sessions correct | |
| Weighted blend (0.7 × success + 0.3 × efficiency) | Tunable blended metric | |

**User's choice:** Average efficiency score (recommended)
**Notes:** Captures both success AND speed. Rewards genuine competence, not just binary pass/fail.

---

### Q3: No human baseline exists?

| Option | Description | Selected |
|--------|-------------|----------|
| Show N/A, no error | AGI proximity = "N/A (no human baseline)" + hint | ✓ |
| Error / exit | Fail with message | |
| Omit proximity from output | Silently skip the section | |

**User's choice:** Show N/A for proximity, no error (recommended)
**Notes:** Doesn't block first-time users from seeing their model's raw performance. Hint to run `cipherbench play`.

---

## Report Output Format

### Q1: Terminal output format?

| Option | Description | Selected |
|--------|-------------|----------|
| Rich table: one row per difficulty tier | Rich Panel + Rich Table with totals row | ✓ |
| Plain text summary | Simple key: value lines | |
| Rich panel summary + --verbose for table | Two modes | |

**User's choice:** Rich table (recommended)
**Notes:** Consistent with the Rich stack from Phase 3 (D-15 human play display).

---

### Q2: JSON report structure?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat structure matching the table | { model, by_difficulty, totals, generated_at } | ✓ |
| Nested with raw session IDs | Include contributing session_ids | |
| You decide | Leave structure to planner | |

**User's choice:** Flat structure matching the table (recommended)
**Notes:** Easy for downstream scripts to parse. Mirrors terminal table exactly.

---

### Q3: Where does scorer logic live?

| Option | Description | Selected |
|--------|-------------|----------|
| New `cipherbench/scoring/` package | scorer.py + reporter.py + report_writer.py | ✓ |
| Single `cipherbench/scoring.py` module | Everything in one file | |
| Inline in `cli/app.py` | No new module | |

**User's choice:** New `cipherbench/scoring/` package (recommended)
**Notes:** Mirrors `session/` package pattern from Phase 3. Keeps CLI layer clean per existing convention.

---

## Claude's Discretion

- Exact Rich table styling (column widths, colors, border style)
- How `--human` resolves "which human" when multiple players exist (may add `--player-name` or aggregate all)
- Whether `agi_proximity` in JSON is `null` or the string `"N/A"` (planner decides — `null` is cleaner for scripts)
- Session count label in terminal header (total found vs filtered)

## Deferred Ideas

None — discussion stayed within phase scope.
