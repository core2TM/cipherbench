# Phase 3: Session Infrastructure & Model Adapters - Research

**Researched:** 2026-05-29
**Domain:** Python CLI (Typer), LLM API integration (LiteLLM), session persistence (JSON + atomic writes), retry/backoff (tenacity), terminal UI (Rich)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Probe/Answer Format**
- D-01: Probe format `PROBE: ABCDE`. Primary regex: `r'PROBE:\s*([A-Z]{5})'` (alphabet adjusted at runtime)
- D-02: Final answer format `ANSWER: ABCDE`. Separate 6th model call, not a probe attempt. Regex: `r'ANSWER:\s*([A-Z]{5})'`
- D-03: Prompt is minimal — rules, format, attempt count, scoring mechanic only. No worked examples or strategy hints.
- D-04: Full attempt history in every message (running table of attempt N / probe / score M/5). No per-position breakdown.
- D-05: Fallback when no valid probe found: record `probe=null`, `score=null`, `is_correct=false`, `extraction_failed=true`; do NOT consume an attempt count; log raw response; continue. Human re-prompts on bad input.

**Session JSON Schema**
- D-06: File naming `{YYYYMMDD}T{HHMMSS}-{model-slug}.json` / `{YYYYMMDD}T{HHMMSS}-human-{player-name}.json`
- D-07: `runner_type` field: `'model'` | `'human'`
- D-08: Attempt entry has `attempt_num`, `probe`, `score`, `max_score`, `is_correct`, `raw_response`, `extraction_failed`
- D-09: Session `outcome`: `'success'` | `'failure'` | `'rate_limited'` | `'in_progress'`
- D-10: All sessions in flat `sessions/` directory at project root
- D-11: Top-level session schema with `session_id`, `runner_type`, `model`, `player_name`, `seed`, `difficulty`, `puzzle_hash`, `outcome`, `final_answer`, `attempts`, `created_at`, `completed_at`

**CLI Surface**
- D-12: `cipherbench run` flags: `--model` (required), `--seed`, `--num-puzzles`, `--runs-per-puzzle`, `--difficulty`, `--output-dir`, `--litellm-config`
- D-13: `cipherbench play` flags: `--player-name`, `--seed`, `--difficulty`, `--output-dir`
- D-14: API keys from provider env vars automatically (LiteLLM reads them). `--litellm-config` is escape hatch.
- D-15: `cipherbench play` uses Rich Panel (puzzle header), colored score line (green/yellow/red), Rich Table (attempt history)

**Rate-Limit / Checkpoint Strategy**
- D-16: Auto-retry with exponential backoff up to N retries (N at Claude's discretion, suggested ~5). If exhausted, write `outcome='rate_limited'` and abort.
- D-17: Inline partial session — written at init with `outcome='in_progress'`, overwritten after each attempt; single glob handles all states.
- D-18: On re-run, auto-detect `outcome='rate_limited'` sessions for same model+seed and resume from last completed attempt.

### Claude's Discretion
- Max retry count N for exponential backoff (suggested 5)
- Exact backoff formula (any standard exponential backoff with jitter)
- Exact prompt template wording (minimal per D-03)
- Regex primary + fallback patterns for PROBE:/ANSWER: extraction
- Token budget warning threshold (e.g., 80% of context window)
- Session file name slug sanitization rules
- Rich table column layout and color scheme

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SESS-01 | `cipherbench run` feeds puzzles to model via LiteLLM, records each session as JSON | LiteLLM `completion()` API; atomic JSON write pattern; Typer subcommand pattern |
| SESS-02 | `cipherbench play` presents puzzles to human, identical format, same JSON schema | Typer `CliRunner` / `typer.prompt()`; Rich Panel + Table for terminal UX |
| SESS-04 | 50-run sequential determinism test passes; fresh session factory per session | `litellm.completion(mock_response=...)` for test isolation; existing RNG discipline from Phase 1/2 |
| ADAPT-01 | `complete(messages) -> str` interface routes to any LiteLLM-supported provider | `litellm.completion(model, messages)` call; no adapter-specific code in caller |
| ADAPT-02 | Token budget check at session init — warn and abort if projected session > context window | `litellm.get_max_tokens(model)` and `litellm.token_counter(model, messages)` |
| ADAPT-03 | Rate-limit responses handled with exponential backoff + per-attempt checkpointing | `tenacity` with `retry_if_exception_type(litellm.RateLimitError)` + `wait_random_exponential` |
| ADAPT-04 | Regex + fallback extraction of valid probe string from freeform model output | `re.search(r'PROBE:\s*([A-Z]{5})', text)` primary; looser fallback pattern |
</phase_requirements>

---

## Summary

Phase 3 delivers the first runnable end-to-end benchmark. The work divides into four sub-systems: (1) the LiteLLM adapter (`complete(messages) -> str`) that routes any provider call through a single interface with token-budget checking and tenacity-based exponential backoff; (2) the session runner that drives the probe-attempt loop, builds the conversation history, extracts probes with regex, and writes the inline checkpoint JSON; (3) the human runner that presents the same prompt and feedback via Typer prompts and Rich terminal output; and (4) the CLI entry point that wires `cipherbench run` and `cipherbench play` as Typer subcommands.

The existing codebase provides `generate_puzzle(seed, difficulty) -> Puzzle`, `Puzzle.create_engine() -> RuleEngine`, and `score_attempt(guess) -> AttemptScore` — all already tested and frozen. Phase 3 adds only the session orchestration and I/O layers on top; it must not touch any Phase 1/2 code. The inline checkpoint pattern (D-17) — write `in_progress` at init, overwrite after each attempt — is the critical design that makes rate-limit resume safe without a separate checkpoint file.

The SESS-04 determinism test is the principal correctness gate: 50 sequential sessions from the same seed with a mock adapter must produce identical outcomes, proving the RNG discipline holds across the entire stack.

**Primary recommendation:** Implement a thin `LiteLLMAdapter` class wrapping `litellm.completion()`, inject it as a dependency into `ModelSessionRunner`; use `litellm.completion(mock_response=...)` for all determinism and unit tests — no real API calls in tests.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM API call routing | Adapter layer (`cipherbench/adapters/`) | — | Provider-agnostic boundary. All caller code uses `complete(messages) -> str`; adapter owns provider specifics |
| Token budget check | Adapter layer | — | `get_max_tokens` and `token_counter` are LiteLLM utilities; natural co-location with `complete()` |
| Rate-limit retry + backoff | Adapter layer | — | Retry decorates the `complete()` call; caller receives either a response or a `RateLimitError` after exhaustion |
| Probe/answer extraction | Session runner (`cipherbench/session/`) | — | Regex parsing is a concern of the session orchestration, not the adapter |
| Attempt loop + history building | Session runner | — | Owns the 5-attempt loop, conversation list construction, and AttemptScore → attempt entry conversion |
| Inline JSON checkpoint | Session runner | stdlib `json` + `pathlib` + `os.replace` | Session runner writes/updates the file; adapter has no knowledge of storage |
| Prompt template rendering | Prompt builder (`cipherbench/session/prompt.py`) | — | Isolated in its own module so it can be tested without running a session |
| CLI entry point wiring | CLI module (`cipherbench/cli/`) | — | Typer app with `app.add_typer()` subcommands; no business logic here |
| Human interactive I/O | Human runner (`cipherbench/session/human_runner.py`) | Rich terminal | Uses `typer.prompt()` for input; Rich Panel + Table for output |
| Session file storage | `sessions/` flat directory | — | Flat structure decided by D-10; no sub-directories, no database |

---

## Standard Stack

### Core

| Library | Version (PyPI verified) | Purpose | Why Standard |
|---------|------------------------|---------|--------------|
| `litellm` | `>=1.40` (latest: 1.83.9) | `complete(messages) -> str` adapter; token counting; model info | Single `completion()` call covers Anthropic, OpenAI, Google, etc. `RateLimitError` is importable directly. [VERIFIED: PyPI registry] |
| `typer` | `>=0.12` (latest: 0.23.2) | CLI subcommands `run` and `play`; `Annotated[]` param style | Type-annotated commands; auto-help; ships Rich integration. [VERIFIED: PyPI registry] |
| `rich` | `>=13.0` (latest: 15.0.0) | `Panel`, `Table`, colored output for `cipherbench play` | Typer dependency; zero wiring needed; `Console`, `Table`, `Panel` cover all UX requirements. [VERIFIED: PyPI registry] |
| `tenacity` | `>=8.0` (latest: 9.1.2) | Exponential backoff retry decorator for `complete()` | `retry_if_exception_type` + `wait_random_exponential` + `stop_after_attempt` compose cleanly; standard in the LLM client ecosystem. [VERIFIED: PyPI registry] |

### Supporting (stdlib — no install)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| `json` (stdlib) | Session file read/write | Primary session storage (D-10) |
| `pathlib.Path` (stdlib) | Cross-platform path handling | Output dir creation, file naming |
| `os.replace` (stdlib) | Atomic file swap after temp-write | Safe inline checkpoint update |
| `re` (stdlib) | Probe/answer regex extraction | ADAPT-04 regex patterns |
| `datetime` (stdlib) | `created_at`/`completed_at` ISO timestamps | Session schema D-11 |
| `tempfile.NamedTemporaryFile` (stdlib) | Write-then-rename atomic pattern | Checkpoint write safety |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tenacity` | manual `time.sleep` loop | Tenacity handles jitter, stop conditions, exception filtering, and logging — no reason to hand-roll |
| `tenacity` | `litellm` built-in `num_retries` | LiteLLM's `num_retries` is a simple count with no jitter control or per-attempt callback — cannot checkpoint after each attempt |
| `os.replace` | `pathlib.Path.write_text` | `write_text` is not atomic — partial write visible to concurrent readers |

**Installation** (new dependencies only):

```bash
uv add litellm>=1.40 typer>=0.12 rich>=13.0 tenacity>=8.0
# or
pip install litellm>=1.40 "typer[all]>=0.12" "rich>=13.0" tenacity>=8.0
```

Note: `typer[all]` installs Rich automatically. If Rich is listed separately in dependencies, either form works.

---

## Package Legitimacy Audit

slopcheck was not available at research time. All packages below are tagged `[ASSUMED]` based on PyPI registry verification and training knowledge. The planner must gate each install behind a `checkpoint:human-verify` step if required by project policy.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `litellm` | PyPI | ~3 yrs | Very high (frontier LLM ecosystem standard) | github.com/BerriAI/litellm | N/A | [ASSUMED] — approved by CLAUDE.md |
| `typer` | PyPI | ~5 yrs | Very high (tiangolo/typer) | github.com/tiangolo/typer | N/A | [ASSUMED] — approved by CLAUDE.md |
| `rich` | PyPI | ~5 yrs | Very high (textualize/rich) | github.com/Textualize/rich | N/A | [ASSUMED] — approved by CLAUDE.md |
| `tenacity` | PyPI | ~8 yrs | High (jd/tenacity) | github.com/jd/tenacity | N/A | [ASSUMED] — approved, well-known retry library |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck unavailable at research time — all packages tagged `[ASSUMED]`. All four are listed in CLAUDE.md's recommended or approved stack, which is treated as the authoritative approval source for this project.*

---

## Architecture Patterns

### System Architecture Diagram

```
CLI entry point (cipherbench/cli/app.py)
  ├── cipherbench run
  │     │ reads flags (--model, --seed, --difficulty, ...)
  │     └── ModelSessionRunner
  │           ├── generate_puzzle(seed, difficulty)  [Phase 2]
  │           ├── puzzle.create_engine()             [Phase 2]
  │           ├── PromptBuilder.build_system()
  │           ├── [for each attempt 1..5]
  │           │     ├── PromptBuilder.build_user(history)
  │           │     ├── LiteLLMAdapter.complete(messages)
  │           │     │     ├── litellm.completion(model, messages)
  │           │     │     └── [tenacity retry on RateLimitError]
  │           │     ├── ProbeExtractor.extract(raw_response)
  │           │     ├── engine.score_attempt(probe)  [Phase 1]
  │           │     └── SessionWriter.write_checkpoint(session)
  │           ├── LiteLLMAdapter.complete(messages)  [6th call: ANSWER]
  │           └── SessionWriter.finalize(session, outcome)
  │
  └── cipherbench play
        │ reads flags (--player-name, --seed, --difficulty, ...)
        └── HumanSessionRunner
              ├── generate_puzzle(seed, difficulty)  [Phase 2]
              ├── puzzle.create_engine()             [Phase 2]
              ├── RichDisplay.show_puzzle_header()
              ├── [for each attempt 1..5]
              │     ├── typer.prompt() → raw input
              │     ├── HumanInputValidator.validate(raw)
              │     ├── engine.score_attempt(probe)  [Phase 1]
              │     ├── RichDisplay.show_score(score)
              │     └── SessionWriter.write_checkpoint(session)
              ├── typer.prompt() → final answer
              └── SessionWriter.finalize(session, outcome)

sessions/
  20260529T143022-claude-opus.json
  20260529T143022-human-alice.json
```

### Recommended Project Structure

```
cipherbench/
├── __init__.py           # existing — no changes
├── types.py              # existing — no changes
├── puzzle.py             # existing — no changes
├── engine/               # existing — no changes
│   ├── layers.py
│   └── rule_engine.py
├── adapters/
│   └── litellm_adapter.py  # LiteLLMAdapter class: complete(), token_budget_check()
├── session/
│   ├── __init__.py
│   ├── model_runner.py   # ModelSessionRunner: drives probe loop for LLM sessions
│   ├── human_runner.py   # HumanSessionRunner: drives probe loop for human sessions
│   ├── prompt.py         # PromptBuilder: system prompt + user turn templates
│   ├── extractor.py      # ProbeExtractor / AnswerExtractor: regex + fallback
│   ├── writer.py         # SessionWriter: atomic checkpoint writes + finalize
│   └── schema.py         # SessionRecord dataclass or TypedDict for type safety
└── cli/
    ├── __init__.py
    └── app.py            # typer.Typer() app with add_typer(run_app) + add_typer(play_app)

tests/
├── conftest.py           # existing + new fixtures for mock adapter
├── test_properties.py    # existing
├── unit/
│   ├── test_engine/      # existing
│   ├── test_puzzle/      # existing
│   ├── test_adapters/
│   │   └── test_litellm_adapter.py  # unit tests for complete(), budget check, retry
│   ├── test_session/
│   │   ├── test_model_runner.py     # probe loop, extraction, checkpoint
│   │   ├── test_human_runner.py     # human input validation, display
│   │   ├── test_prompt.py           # prompt template output
│   │   ├── test_extractor.py        # regex extraction + fallback cases
│   │   └── test_writer.py           # atomic write, in_progress → success transition
│   └── test_cli/
│       └── test_commands.py         # Typer CliRunner tests for run + play
└── integration/
    └── test_determinism.py          # SESS-04: 50-run sequential determinism test

sessions/                 # runtime output — created by runner, not in source
```

### Pattern 1: LiteLLM Adapter — `complete(messages) -> str`

**What:** Thin class wrapping `litellm.completion()`. Owns retry logic via tenacity. Returns the content string only; callers never touch `litellm.ModelResponse`.

**When to use:** Every LLM call in the session runner goes through this adapter. The adapter is constructed once per CLI invocation and injected into the session runner.

```python
# Source: docs.litellm.ai/docs/completion/input + tenacity.readthedocs.io
import litellm
from tenacity import retry, retry_if_exception_type, wait_random_exponential, stop_after_attempt

MAX_RETRIES = 5

class LiteLLMAdapter:
    def __init__(self, model: str, litellm_config_path: str | None = None):
        self.model = model
        if litellm_config_path:
            litellm.config_path = litellm_config_path  # [ASSUMED] config_path attr

    @retry(
        retry=retry_if_exception_type(litellm.RateLimitError),
        wait=wait_random_exponential(multiplier=1, max=60),
        stop=stop_after_attempt(MAX_RETRIES),
        reraise=True,  # re-raises after exhaustion for caller to detect
    )
    def complete(self, messages: list[dict]) -> str:
        response = litellm.completion(model=self.model, messages=messages)
        return response.choices[0].message.content  # [VERIFIED: docs.litellm.ai]

    def check_token_budget(self, messages: list[dict]) -> tuple[int, int]:
        """Returns (used_tokens, max_tokens). Caller warns if used > threshold * max."""
        used = litellm.token_counter(model=self.model, messages=messages)  # [CITED: docs.litellm.ai/docs/count_tokens]
        max_tokens = litellm.get_max_tokens(self.model)  # [CITED: docs.litellm.ai/docs/completion/token_usage]
        return used, max_tokens
```

### Pattern 2: Atomic Checkpoint Write

**What:** Write session JSON to a temp file in the same directory, then `os.replace()` to atomically swap. If the process is killed mid-write, the old file (or no file) is intact.

**When to use:** Every call to `SessionWriter.write_checkpoint()` and `SessionWriter.finalize()`.

```python
# Source: Python stdlib docs — os.replace(), tempfile, pathlib
import json
import os
import tempfile
from pathlib import Path

def _atomic_write_json(path: Path, data: dict) -> None:
    """Write data to path atomically using write-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)  # atomic on POSIX and Windows (same filesystem)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### Pattern 3: Typer Subcommand Structure

**What:** `cipherbench run` and `cipherbench play` are separate Typer apps merged into one root app.

**When to use:** The CLI entry point in `cli/app.py`.

```python
# Source: typer.tiangolo.com/tutorial/subcommands/add-typer/
from typing import Annotated
from enum import Enum
import typer

class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

run_app = typer.Typer()
play_app = typer.Typer()
app = typer.Typer()
app.add_typer(run_app, name="run")
app.add_typer(play_app, name="play")

@run_app.command()
def run_command(
    model: Annotated[str, typer.Option(help="LiteLLM model string, e.g. anthropic/claude-opus-4-7")],
    seed: Annotated[int | None, typer.Option(help="RNG seed (default: random)")] = None,
    difficulty: Annotated[Difficulty, typer.Option(case_sensitive=False)] = Difficulty.medium,
    num_puzzles: Annotated[int, typer.Option("--num-puzzles")] = 1,
    runs_per_puzzle: Annotated[int, typer.Option("--runs-per-puzzle")] = 1,
    output_dir: Annotated[str, typer.Option("--output-dir")] = "./sessions",
    litellm_config: Annotated[str | None, typer.Option("--litellm-config")] = None,
) -> None: ...

# pyproject.toml entry point:
# [project.scripts]
# cipherbench = "cipherbench.cli.app:app"
```

### Pattern 4: Rich Terminal Display for `cipherbench play`

**What:** Rich Panel for puzzle header, Rich Table for attempt history, styled score lines.

**When to use:** HumanSessionRunner after each probe attempt and at session start.

```python
# Source: rich.readthedocs.io/en/latest/panel.html + rich.readthedocs.io/en/latest/tables.html
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def show_puzzle_header(seed: int, difficulty_name: str, alphabet: str) -> None:
    console.print(Panel(
        f"Seed: [bold]{seed}[/bold]  Difficulty: [bold]{difficulty_name}[/bold]\n"
        f"Alphabet: [cyan]{alphabet}[/cyan]\n\n"
        "Submit each probe as: [bold yellow]PROBE: XXXXX[/bold yellow]\n"
        "Final answer as:       [bold yellow]ANSWER: XXXXX[/bold yellow]",
        title="[bold]CipherBench[/bold]",
    ))

def show_attempt_history(attempts: list[dict], max_score: int) -> None:
    table = Table(title="Attempt History", show_lines=True)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Probe", style="cyan")
    table.add_column("Score", justify="center")
    for a in attempts:
        score_str = f"{a['score']}/{max_score}"
        style = "green" if a["is_correct"] else ("yellow" if a["score"] > 0 else "red")
        table.add_row(str(a["attempt_num"]), a["probe"] or "INVALID", f"[{style}]{score_str}[/{style}]")
    console.print(table)
```

### Pattern 5: LiteLLM Mock for Determinism Tests (SESS-04)

**What:** Use `litellm.completion(mock_response=...)` to produce deterministic responses without a real API call.

**When to use:** SESS-04 determinism test and all unit tests for session runner.

```python
# Source: docs.litellm.ai/docs/completion/mock_requests
import litellm
from unittest.mock import patch

# Option A: LiteLLM built-in mock_response parameter
def mock_complete(messages: list[dict]) -> str:
    response = litellm.completion(
        model="gpt-3.5-turbo",
        messages=messages,
        mock_response="PROBE: AAAAA",  # deterministic fixed string
    )
    return response.choices[0].message.content

# Option B: inject a mock adapter class (preferred for SESS-04)
class FixedResponseAdapter:
    """Adapter that returns a fixed probe string — used in SESS-04 determinism test."""
    def __init__(self, response: str = "PROBE: AAAAA"):
        self.response = response
    def complete(self, messages: list[dict]) -> str:
        return self.response

# SESS-04 test pattern
def test_50_run_determinism():
    adapter = FixedResponseAdapter("PROBE: AAAAA")
    outcomes = []
    for _ in range(50):
        # ModelSessionRunner accepts adapter as injected dependency
        runner = ModelSessionRunner(seed=42, difficulty=MEDIUM, adapter=adapter, output_dir=tmp_path)
        session = runner.run()
        outcomes.append(session["outcome"])
    assert len(set(outcomes)) == 1, "All 50 sessions must have identical outcome"
```

### Pattern 6: Regex Probe Extraction with Fallback

**What:** Primary regex matches strict format; fallback is a looser pattern; if both fail, mark attempt as `extraction_failed`.

**When to use:** `ProbeExtractor.extract(raw_response, alphabet)` called after every `complete()` call.

```python
import re

def extract_probe(text: str, alphabet: str) -> str | None:
    """Extract probe string from model freeform response.
    Primary: r'PROBE:\s*([{alphabet}]{{5}})' — strict alphabet match.
    Fallback: any 5-character sequence from the alphabet in the response.
    Returns None if extraction fails (caller sets extraction_failed=True).
    """
    pattern_chars = re.escape(alphabet)
    # Primary: explicit PROBE: tag
    primary = re.search(rf'PROBE:\s*([{pattern_chars}]{{5}})', text)
    if primary:
        return primary.group(1)
    # Fallback: any 5-char run from the alphabet
    fallback = re.search(rf'([{pattern_chars}]{{5}})', text)
    if fallback:
        return fallback.group(1)
    return None

def extract_answer(text: str, alphabet: str) -> str | None:
    pattern_chars = re.escape(alphabet)
    primary = re.search(rf'ANSWER:\s*([{pattern_chars}]{{5}})', text)
    if primary:
        return primary.group(1)
    return None
```

### Anti-Patterns to Avoid

- **Reusing a `RuleEngine` across sessions:** `puzzle.create_engine()` must be called once per session. Reuse causes state bleed — SESS-04 will fail.
- **Calling `random.seed()` globally:** Any random seed generation for `--num-puzzles` or `--seed` defaults must use `random.Random()` instances, never global seeding (D-11 Phase 1 discipline).
- **Writing session JSON with `Path.write_text()`:** Not atomic — a crash mid-write produces a corrupt file that blocks resume. Always use the write-then-rename pattern.
- **Catching `Exception` around `complete()`:** Only catch `litellm.RateLimitError` for backoff. Let `AuthenticationError`, `BadRequestError`, and others propagate to the caller.
- **Putting retry logic in the session runner:** Retry belongs in the adapter. The session runner only sees either a successful string or a `RateLimitError` after exhaustion.
- **Using `litellm.completion` with `num_retries=N`:** LiteLLM's built-in retry has no jitter and no per-attempt callback — cannot implement inline checkpointing. Use tenacity.
- **Storing `DifficultyConfig` object in session JSON:** Too verbose. Store `get_tier(puzzle.difficulty)` string only (D-11 decision, `difficulty` field in session schema).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-provider LLM routing | Custom per-provider HTTP clients | `litellm.completion()` | Handles auth, retry normalization, response parsing for 100+ providers |
| Exponential backoff with jitter | `while True: time.sleep(2**n)` | `tenacity.wait_random_exponential` | Thread-safe, handles stop conditions, supports logging hooks |
| Context window size lookup | Hard-coded dict of model limits | `litellm.get_max_tokens(model)` | Kept current with new models; avoids stale values |
| Token counting | Character-count heuristics | `litellm.token_counter(model, messages)` | Uses model-specific tokenizer; falls back to tiktoken |
| Atomic file write | `open(path, 'w')` then truncate | `tempfile` + `os.replace()` | `os.replace()` is atomic on POSIX/Windows within same filesystem |
| CLI argument parsing | `argparse` or manual `sys.argv` | `typer` with `Annotated[]` | Auto-help, type coercion, Enum validation, zero boilerplate |

**Key insight:** The entire session persistence requirement (D-10 through D-17) is satisfiable with stdlib only (`json`, `pathlib`, `os`, `tempfile`). The only non-stdlib adds are LiteLLM, Typer, Rich, and Tenacity — all already approved in CLAUDE.md.

---

## Common Pitfalls

### Pitfall 1: Attempt Count Drift on Extraction Failure

**What goes wrong:** Extraction failure consumes an attempt count, burning through the 5-attempt budget on invalid model responses.

**Why it happens:** The probe loop increments a counter on every iteration regardless of extraction success.

**How to avoid:** Per D-05, `extraction_failed=True` attempts are recorded but do NOT increment the attempt count used toward the 5-attempt limit. The attempt list grows, but `len([a for a in attempts if not a['extraction_failed']])` determines when the limit is reached.

**Warning signs:** In tests, 5 extraction failures produce a session with 5 attempts but `outcome='failure'` without any valid probes ever submitted to the engine.

### Pitfall 2: Tenacity Retry Hides `RateLimitError` from Checkpoint Code

**What goes wrong:** After N retries are exhausted, tenacity re-raises `RateLimitError`, but the checkpoint write happens in a `finally` block that has already been skipped because the exception propagated past it.

**Why it happens:** The `reraise=True` on the tenacity decorator means the exception propagates out of `complete()`. If the session runner doesn't catch it before writing the checkpoint, the `rate_limited` outcome is never written.

**How to avoid:** In the session runner's attempt loop:

```python
try:
    raw = self.adapter.complete(messages)
except litellm.RateLimitError:
    session_data["outcome"] = "rate_limited"
    session_data["completed_at"] = datetime.utcnow().isoformat() + "Z"
    _atomic_write_json(session_path, session_data)
    return session_data
```

**Warning signs:** Process crashes during rate-limit scenario leave an `in_progress` file instead of `rate_limited`.

### Pitfall 3: Non-Determinism from `datetime.utcnow()` in Session ID

**What goes wrong:** Session ID includes a timestamp (`{YYYYMMDD}T{HHMMSS}`). Two sessions started within the same second produce the same filename, causing a collision.

**Why it happens:** File naming decision D-06 uses second-level precision.

**How to avoid:** Before writing, check if `{timestamp}-{model-slug}.json` already exists in the output directory. If it does, append a suffix (`-2`, `-3`, etc.) to the slug. Log the collision.

**Warning signs:** `--runs-per-puzzle 5` on a fast machine produces 4 sessions instead of 5 because files silently overwrite each other.

### Pitfall 4: `get_max_tokens()` Returns `None` for Unknown Models

**What goes wrong:** `litellm.get_max_tokens("custom-model")` returns `None` for models not in LiteLLM's model database, causing a `TypeError` in the budget check comparison.

**Why it happens:** LiteLLM's model database doesn't include every possible model string.

**How to avoid:** Always guard: `if max_tokens is None: return  # skip check, log warning`. The budget check should be advisory (warn) not fatal (abort) for unknown models.

**Warning signs:** `TypeError: '>' not supported between instances of 'int' and 'NoneType'` in the adapter.

### Pitfall 5: Conversation History Growth Exceeds Context Window

**What goes wrong:** Each probe attempt appends the full attempt history to the conversation. By attempt 5, the conversation is 5x larger than attempt 1. This can silently truncate early context on models with small windows.

**Why it happens:** D-04 mandates full history in every message, but token budget check only runs at session init.

**How to avoid:** Run `token_counter` at each attempt turn, not only at init. Alternatively, the init check must project the worst-case size (5 attempts × estimated max response length). Document this in the budget check implementation.

**Warning signs:** Model responses at attempt 4-5 become incoherent, as if context was lost.

### Pitfall 6: Resume Logic Silently Replays Old Attempt Data

**What goes wrong:** When resuming a `rate_limited` session, the runner reads the existing attempt list and resumes from `len(existing_attempts) + 1`. If the existing file has corrupted attempt data, the resume produces wrong results without error.

**Why it happens:** `json.load()` succeeds on a file that's structurally valid JSON but has stale or wrong probe/score data.

**How to avoid:** On resume, verify that each resumed attempt's `score` field is consistent with `is_correct` (the same validation `AttemptScore.__post_init__` performs). Log an error and abort if validation fails.

---

## Code Examples

### Full `complete()` call with tenacity

```python
# Source: docs.litellm.ai/docs/completion/input + tenacity.readthedocs.io/en/latest/
from tenacity import retry, retry_if_exception_type, wait_random_exponential, stop_after_attempt
import litellm

@retry(
    retry=retry_if_exception_type(litellm.RateLimitError),
    wait=wait_random_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _call_litellm(model: str, messages: list[dict]) -> str:
    response = litellm.completion(model=model, messages=messages)
    return response.choices[0].message.content
```

### Typer CliRunner in tests

```python
# Source: typer.tiangolo.com/tutorial/testing/
from typer.testing import CliRunner
from cipherbench.cli.app import app

runner = CliRunner()

def test_run_command_help():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.output

def test_play_command_help():
    result = runner.invoke(app, ["play", "--help"])
    assert result.exit_code == 0
```

### Exception hierarchy for catch order

```python
# Source: docs.litellm.ai/docs/exception_mapping
# Order matters — more specific first
import litellm

try:
    raw = adapter.complete(messages)
except litellm.ContextWindowExceededError:
    # token budget exceeded — abort session, distinct from rate limit
    raise
except litellm.RateLimitError:
    # after N retries exhausted by tenacity reraise=True
    session_data["outcome"] = "rate_limited"
    ...
except litellm.AuthenticationError:
    # bad API key — fatal, propagate
    raise
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-provider SDK (`anthropic`, `openai`, `google-generativeai`) | `litellm.completion(model, messages)` unified | LiteLLM ~2023+ | Single call works for all providers; retry/auth handled once |
| `@app.command()` with `Optional[str]` type hints | `Annotated[str, typer.Option()]` style | Typer 0.9+ | Preferred style; keeps type and Typer metadata separate |
| `wait_exponential` (fixed) | `wait_random_exponential` (with jitter) | Tenacity 5+ | Jitter prevents thundering herd against rate-limited APIs |
| `Path.write_text()` for JSON | `tempfile` + `os.replace()` | N/A (always correct) | Atomic swap avoids corrupt partial writes |

**Deprecated/outdated:**
- `litellm.completion` with `num_retries` parameter: Works for simple retry but has no jitter, no per-attempt callback, and no checkpoint hook. Do not use for this phase's checkpoint requirements.
- `typer.Option()` without `Annotated[]`: Still works but is the old style per Typer docs; prefer `Annotated[]` for new code.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `litellm.config_path` is a settable attribute that enables loading a LiteLLM config.yaml | Pattern 1 (LiteLLMAdapter) | D-14 escape hatch (`--litellm-config`) would need a different wiring approach; low priority for v1 |
| A2 | `litellm.get_max_tokens(model)` returns `None` for unknown models | Pitfall 4 | If it raises instead of returning None, guard code needs `try/except` not `if None` check |
| A3 | `litellm.token_counter(model, messages)` signature accepts keyword `messages` | Pattern 1 (check_token_budget) | PyPI registry confirms function exists; exact signature is training knowledge |
| A4 | `response.choices[0].message.content` is the correct path to extract text from `litellm.completion` response | Pattern 1, Code Examples | This matches OpenAI response format which LiteLLM normalizes to; high confidence but not verified via live call |

---

## Open Questions

1. **`litellm.config_path` attribute for `--litellm-config`**
   - What we know: LiteLLM supports a config.yaml for proxy routing. The CLI escape hatch (D-14) requires loading it.
   - What's unclear: The exact Python SDK API to load a config from a file path (vs. the LiteLLM proxy server config).
   - Recommendation: Implement D-14 minimally for v1 — pass `api_base` or other kwargs extracted from the config. If complex, defer to a follow-up task. The core `complete()` call works without it.

2. **Attempt count semantics when `extraction_failed=True`**
   - What we know: D-05 says extraction failures do NOT consume an attempt count.
   - What's unclear: What is the maximum number of extraction failures allowed per session before aborting? An adversarial model that never produces a valid PROBE could loop forever.
   - Recommendation: Add a hard cap of `2 * MAX_ATTEMPTS` total iterations (valid + invalid combined) to prevent infinite loops. Document in schema.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Phase 3 code (`pyproject.toml` requires `>=3.11`) | Partial | 3.9.6 on host system | Use `uv` / virtualenv with Python 3.11; project targets 3.11+ |
| `pytest>=8.0` | All tests | Yes | 8.4.2 | — |
| `pytest-asyncio>=0.23` | Async tests (if any) | Yes | 0.23.8 | — |
| `litellm>=1.40` | ADAPT-01/02/03 | Not installed in project env yet | Latest: 1.83.9 | — |
| `typer>=0.12` | SESS-01/02 CLI | Not installed in project env yet | Latest: 0.23.2 | — |
| `rich>=13.0` | D-15 terminal output | Not installed in project env yet | Latest: 15.0.0 | — |
| `tenacity>=8.0` | ADAPT-03 backoff | Not installed in project env yet | Latest: 9.1.2 | — |
| `uv` | Recommended dep manager | Not found on host | — | Use `pip install` — all packages available via pip |

**Missing dependencies with no fallback:**
- Python 3.11+: The host Python is 3.9.6. `pyproject.toml` requires `>=3.11`. The project must be run inside a virtual environment with Python 3.11+. The planner should include a Wave 0 task to install project dependencies via `pip install -e ".[dev]"` (or `uv sync`).

**Missing dependencies with fallback:**
- `uv` not found: Use `pip install` for all packages. All packages in the standard stack are available via pip.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths = ["tests"], addopts = "-v --tb=short") |
| Quick run command | `pytest tests/unit/test_session/ tests/unit/test_adapters/ -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SESS-01 | `cipherbench run` writes JSON session file | integration | `pytest tests/unit/test_session/test_model_runner.py -x` | No — Wave 0 |
| SESS-02 | `cipherbench play` records human session to same schema | unit + CliRunner | `pytest tests/unit/test_cli/test_commands.py -x` | No — Wave 0 |
| SESS-04 | 50 sequential sessions from same seed → identical outcomes | integration | `pytest tests/integration/test_determinism.py -x` | No — Wave 0 |
| ADAPT-01 | `complete(messages) -> str` routes to any provider | unit (mock) | `pytest tests/unit/test_adapters/test_litellm_adapter.py -x` | No — Wave 0 |
| ADAPT-02 | Token budget check warns on excess | unit | `pytest tests/unit/test_adapters/test_litellm_adapter.py::test_budget_check -x` | No — Wave 0 |
| ADAPT-03 | Rate-limit triggers backoff; exhaustion writes `rate_limited` | unit (mock RateLimitError) | `pytest tests/unit/test_adapters/test_litellm_adapter.py::test_rate_limit_retry -x` | No — Wave 0 |
| ADAPT-04 | Regex extracts probe; fallback on loose match; None on failure | unit | `pytest tests/unit/test_session/test_extractor.py -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/ -x`
- **Per wave merge:** `pytest tests/ -x` (full suite including all prior phases)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_adapters/__init__.py` — package file
- [ ] `tests/unit/test_adapters/test_litellm_adapter.py` — covers ADAPT-01, ADAPT-02, ADAPT-03
- [ ] `tests/unit/test_session/__init__.py` — package file
- [ ] `tests/unit/test_session/test_model_runner.py` — covers SESS-01, SESS-04
- [ ] `tests/unit/test_session/test_human_runner.py` — covers SESS-02
- [ ] `tests/unit/test_session/test_extractor.py` — covers ADAPT-04
- [ ] `tests/unit/test_session/test_writer.py` — covers atomic write, in_progress/success transition
- [ ] `tests/unit/test_session/test_prompt.py` — covers D-03/D-04 prompt structure
- [ ] `tests/unit/test_cli/__init__.py` — package file
- [ ] `tests/unit/test_cli/test_commands.py` — Typer CliRunner for run + play help/flags
- [ ] `tests/integration/__init__.py` — package file
- [ ] `tests/integration/test_determinism.py` — SESS-04 50-run test
- [ ] `tests/conftest.py` — add `MockAdapter` fixture and `tmp_sessions_dir` fixture

---

## Security Domain

Security enforcement is enabled (`security_enforcement: true`, `security_asvs_level: 1`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | API keys are provider-managed; LiteLLM reads from env vars |
| V3 Session Management | No | No user sessions in this phase — benchmark sessions are not auth sessions |
| V4 Access Control | No | CLI tool run by the researcher; no multi-user access control |
| V5 Input Validation | Yes | Probe/answer extraction via regex; human input length + alphabet validation |
| V6 Cryptography | No | No crypto operations in this phase; session JSON is plaintext by design |

### Known Threat Patterns for Python CLI / LLM Integration

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage in session JSON | Information Disclosure | Never write API key values to session JSON; keys come from env vars only |
| Prompt injection via puzzle content | Tampering | CipherBench puzzles are generated procedurally — no user-supplied content in the system prompt |
| Path traversal in `--output-dir` | Tampering | Validate that `--output-dir` is a local path; do not allow `..` to escape the project root (low risk for a researcher CLI, document as known) |
| Regex ReDoS | Denial of Service | Use bounded quantifiers (`{5}`) and anchored patterns — already done in D-01/D-02 patterns. Avoid `(.+)` backtracking |
| Corrupt JSON in checkpoint resume | Tampering / DoS | Validate JSON structure before resuming; abort with error on schema mismatch |

---

## Sources

### Primary (HIGH confidence)
- `docs.litellm.ai/docs/completion/input` — `litellm.completion()` call signature and message format
- `docs.litellm.ai/docs/exception_mapping` — LiteLLM exception types, `RateLimitError` inherits from `openai.RateLimitError`
- `docs.litellm.ai/docs/completion/mock_requests` — `mock_response` parameter for test isolation
- `docs.litellm.ai/docs/count_tokens` — `token_counter()` and `get_max_tokens()` API
- `tenacity.readthedocs.io/en/latest/` — `retry_if_exception_type`, `wait_random_exponential`, `stop_after_attempt` patterns
- `typer.tiangolo.com/tutorial/subcommands/add-typer/` — `app.add_typer()` subcommand pattern
- `typer.tiangolo.com/tutorial/testing/` — `CliRunner` pattern for Typer test
- `rich.readthedocs.io/en/latest/tables.html` — `Table` API
- `rich.readthedocs.io/en/latest/panel.html` — `Panel` API
- PyPI registry — version verification for litellm (1.83.9), typer (0.23.2), rich (15.0.0), tenacity (9.1.2)

### Secondary (MEDIUM confidence)
- `packaging.python.org/en/latest/guides/creating-command-line-tools/` — `[project.scripts]` entry point pattern in pyproject.toml
- `docs.litellm.ai/docs/completion/reliable_completions` — LiteLLM fallback patterns; note: built-in `num_retries` lacks per-attempt callback, confirmed tenacity is the right choice

### Tertiary (LOW confidence)
- `litellm.config_path` attribute for file-based config — not verified via official LiteLLM SDK docs (A1 in Assumptions Log)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all packages verified at PyPI; APIs confirmed via official documentation
- Architecture: HIGH — LiteLLM adapter pattern, Typer subcommand pattern, atomic write pattern all verified; module structure follows existing project conventions
- Pitfalls: MEDIUM-HIGH — extraction failure count semantics (Pitfall 1) and retry/checkpoint interaction (Pitfall 2) are based on design analysis; remainder verified via official sources or project decisions

**Research date:** 2026-05-29
**Valid until:** 2026-06-28 (LiteLLM moves fast — re-verify `get_max_tokens` / `token_counter` signatures if more than 30 days elapse)
