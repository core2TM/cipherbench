# Phase 3: Session Infrastructure & Model Adapters - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 3-session-infrastructure-model-adapters
**Areas discussed:** Probe format & prompt template, Session JSON schema, CLI surface: run & play flags, Rate-limit checkpoint strategy

---

## Probe Format & Prompt Template

### Q1: What format should the model (and human) submit a probe in?

| Option | Description | Selected |
|--------|-------------|----------|
| Exact 5-char string only | Prompt asks for bare string like ABCDE — simplest regex. | |
| Tagged format: PROBE: ABCDE | Prompt asks for PROBE: prefix — unambiguous extraction even in verbose responses. | ✓ |
| JSON: {"probe": "ABCDE"} | Structured JSON — explicit but adds formatting overhead. | |

**User's choice:** Tagged format: PROBE: ABCDE

---

### Q2: What information does the initial prompt give the model?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal — just the rules and format | Rules + format only, no examples, no strategy hints. Tests pure reasoning. | ✓ |
| Rules + example round | Explain scoring with a worked example. | |
| Rules + example + strategy hint | Closest to human instruction; may inflate scores via prompt engineering. | |

**User's choice:** Minimal — just the rules and format

---

### Q3: What does the fallback parser do on failed PROBE: extraction?

| Option | Description | Selected |
|--------|-------------|----------|
| Scan for any 5-char alphabetic substring | Permissive regex fallback. | |
| Ask the model to reformat (one retry) | Follow-up message, same attempt slot. | |
| Mark attempt as invalid, skip it | Record extraction_failed=true, no attempt consumed. | ✓ |

**User's choice:** Mark attempt as invalid, skip it

---

### Q4: How is feedback presented back to the model?

| Option | Description | Selected |
|--------|-------------|----------|
| Score line only: 'Score: 3/5' | Minimal — model tracks its own history. | |
| Score + attempt history in each message | Running table of all attempts + scores. Reduces model memory burden. | ✓ |
| Score line + attempt echo: 'PROBE: ABCDE → 3/5' | Echo + score, no history table. | |

**User's choice:** Score + attempt history in each message

---

## Session JSON Schema

### Q1: Session ID and file naming format?

| Option | Description | Selected |
|--------|-------------|----------|
| UUID (random) | Globally unique, no info encoded. | |
| Timestamp + model slug | Human-readable, sortable by time. | ✓ |
| Seed + model + counter | Encodes puzzle seed in filename. | |

**User's choice:** Timestamp + model slug: `20260529T143022-claude-opus.json`

---

### Q2: How to distinguish human vs model sessions?

| Option | Description | Selected |
|--------|-------------|----------|
| runner_type field: 'model' or 'human' | Explicit enum at top level. Queryable by Phase 4 and 5. | ✓ |
| model field is null for human | Same schema, null-check convention. | |
| Separate subdirectory | Physical separation by directory. | |

**User's choice:** `runner_type` field: `'model'` | `'human'`

---

### Q3: Attempt entry structure?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: {attempt_num, probe, score, max_score, is_correct} | Just the facts. | |
| Minimal + raw_response for model sessions | Adds full model text for debugging. null for human. | ✓ |
| Full: minimal + raw_response + timestamp + extraction_method | Maximum traceability. | |

**User's choice:** Minimal + `raw_response` for model sessions (null for human)

---

### Q4: Where do session files go?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat: sessions/ directory | All files together. Simple glob. | ✓ |
| sessions/{model-slug}/ per model | Automatic grouping by model. | |
| sessions/{YYYY-MM-DD}/ date-partitioned | Chronological. | |

**User's choice:** Flat `sessions/` directory

---

## CLI Surface: Run & Play Flags

### Q1: `cipherbench run` flags?

| Option | Description | Selected |
|--------|-------------|----------|
| --model, --seed, --num-puzzles, --difficulty | Minimal useful surface. | |
| Above + --runs-per-puzzle | Adds repeated trials per puzzle for statistical reliability. | ✓ |
| Above + --seed-range START END | Adds batch seed range. | |

**User's choice:** `--model` (required), `--seed`, `--num-puzzles`, `--difficulty`, `--output-dir`, `--runs-per-puzzle`

---

### Q2: `cipherbench play` player identification?

| Option | Description | Selected |
|--------|-------------|----------|
| No ID — anonymous | All human sessions labeled 'human'. | |
| --player-name optional flag | Optional label, default 'human'. Multi-player friendly. | ✓ |
| Prompt for player name at start | Interactive prompt. | |

**User's choice:** `--player-name TEXT` (optional, default `'human'`)

---

### Q3: Human feedback display?

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text only | Simple print statements. | |
| Rich: colored score, attempt table | Rich Panel, colored score, attempt history table. | ✓ |
| Rich — score display only | Just color the score output. | |

**User's choice:** Rich — colored score + full attempt table

---

### Q4: API key / LiteLLM config source?

| Option | Description | Selected |
|--------|-------------|----------|
| Environment variables only | LiteLLM reads provider env vars automatically. | |
| Env vars + optional --litellm-config flag | Default: env vars. --litellm-config for advanced routing. | ✓ |
| cipherbench.toml config file | Project-level config. | |

**User's choice:** Env vars + optional `--litellm-config PATH`

---

## Rate-Limit Checkpoint Strategy

### Q1: Rate-limit error handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-retry with exponential backoff | Stays in session, no user action needed. | |
| Checkpoint + abort, resume with --resume | Explicit but requires user action. | |
| Hybrid: auto-retry N times, then checkpoint + abort | Best of both. Auto-retry first, then graceful abort with resume detection. | ✓ |

**User's choice:** Hybrid — auto-retry N times, then checkpoint + abort

---

### Q2: Checkpoint file location?

| Option | Description | Selected |
|--------|-------------|----------|
| Same sessions/ dir with .checkpoint suffix | Lives next to session file. | |
| sessions/.checkpoints/ subdirectory | Keeps sessions/ tidy. | |
| Inline: partial session file (no separate file) | Session JSON written at init with outcome='in_progress', overwritten on completion. | ✓ |

**User's choice:** Inline partial session file — no separate checkpoint file

---

### Q3: Session outcome values?

| Option | Description | Selected |
|--------|-------------|----------|
| 'success' \| 'failure' \| 'rate_limited' \| 'in_progress' | Four states, maximum granularity. | ✓ |
| 'success' \| 'failure' \| 'incomplete' | Simplified — collapse non-terminal states. | |

**User's choice:** `'success'` | `'failure'` | `'rate_limited'` | `'in_progress'`

---

### Q4: How does the model submit a final answer?

| Option | Description | Selected |
|--------|-------------|----------|
| ANSWER: XXXXX tag (after all probes used) | Distinct tag, separate 6th model call. | ✓ |
| Last PROBE: is also the final answer | 5th probe = final answer. Simpler but imprecise. | |
| Separate final step with free-text + ANSWER: tag | Richer log but extra model call. | |

**User's choice:** `ANSWER: XXXXX` tag — separate 6th model call after all 5 probe attempts

---

## Claude's Discretion

- Max retry count (N) for exponential backoff — suggested 5
- Exact backoff formula (e.g., `2^n` seconds with jitter cap)
- Exact prompt template text (minimal per D-03)
- Regex patterns for `PROBE:` and `ANSWER:` extraction
- Token budget threshold for ADAPT-02 warning
- Session file name slug sanitization rules
- Rich table column layout and color scheme

## Deferred Ideas

None — discussion stayed within phase scope.
