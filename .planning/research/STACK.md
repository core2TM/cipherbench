# Technology Stack

**Project:** CipherBench — AGI Proximity Benchmark
**Researched:** 2026-05-28
**Confidence note:** Bash, WebSearch, and WebFetch tools were unavailable in this environment. All findings are drawn from training data (knowledge cutoff August 2025). Version numbers marked LOW confidence must be verified against PyPI before pinning in pyproject.toml.

---

## Recommended Stack

### CLI Interface

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Typer | `>=0.12` | Primary CLI framework | Type-annotated commands, auto-generates help text, built on Click so Click plugins still work. Zero boilerplate for subcommands. First-class support for `Annotated[]` param style introduced in 0.9+. |
| Rich | `>=13.0` | Terminal output formatting | Typer ships Rich integration; used for progress bars, session replay tables, colored feedback display. No extra wiring needed. |

**Why Typer over Click:** Click is the foundation both build on, but raw Click requires manual `@click.option` decorators with duplicated type annotations. Typer reads Python type hints directly — the function signature IS the CLI contract. For a project with subcommands (`run`, `play`, `inspect`, `compare`), Typer's `app.add_typer()` composition is cleaner than Click's `@group.command()` nesting. In 2025, Typer is the community consensus for new Python CLIs that also ship as importable SDKs.

**Why not argparse:** argparse is stdlib and zero-dependency, but its API is verbose and it produces no subcommand help improvements over 2015. Acceptable only for micro-scripts with one or two flags. Not appropriate here.

**Why not Click directly:** Nothing wrong with Click, but the type-annotation layer Typer adds reduces code volume by ~40% for the same CLI surface. Since CipherBench is also an importable SDK, having clean Python function signatures (which Typer requires) is doubly useful.

**Confidence:** MEDIUM — Typer 0.12 released early 2024, actively maintained by FastAPI author (Sebastián Ramírez). Version needs PyPI verification.

---

### Provider-Agnostic LLM Client

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| LiteLLM | `>=1.40` | Unified API across all frontier providers | Single `completion()` call works for Anthropic, OpenAI, Google Gemini, Mistral, Cohere, and 100+ others. Handles auth, retry, rate-limit, and response normalization. |

**Why LiteLLM over raw SDKs:** CipherBench explicitly requires provider-agnosticism. Without an abstraction layer, each new provider requires: a new SDK dependency, a new auth flow, a new response parser, and a new retry wrapper. LiteLLM collapses all of this to a provider string prefix (`"anthropic/claude-opus-4"`, `"openai/gpt-4o"`, `"gemini/gemini-2.0-flash"`). The benchmark harness stays identical across providers — only the model string changes.

**Why not `instructor`:** `instructor` is excellent for structured output extraction (forcing LLM responses to conform to Pydantic schemas), but it is a wrapper around SDKs for type-safe extraction, not a provider router. CipherBench doesn't need to parse LLM output into Pydantic models — it needs raw text responses that the rule engine evaluates. Using instructor would add a dependency that solves a problem CipherBench doesn't have.

**Why not direct Anthropic/OpenAI SDKs:** Hardcoding one SDK defeats the provider-agnostic constraint stated in PROJECT.md. Wrapping multiple SDKs yourself replicates what LiteLLM already does, with worse retry/backoff logic.

**LiteLLM integration pattern for CipherBench:**
```python
# providers/litellm_runner.py
from litellm import completion

def run_model(model: str, messages: list[dict], seed: int | None = None) -> str:
    response = completion(
        model=model,
        messages=messages,
        seed=seed,        # propagated to providers that support it (OpenAI, some Anthropic)
        temperature=0.0,  # determinism for benchmark runs
    )
    return response.choices[0].message.content
```

**Seed propagation note:** OpenAI's API accepts `seed` natively. Anthropic does not expose a seed parameter at the API level. For reproducibility across providers, fix `temperature=0.0` (which is sufficient for greedy decoding) and document that exact reproducibility on Anthropic models requires identical prompt + temperature, not a seed. See Reproducibility section below.

**Confidence:** MEDIUM — LiteLLM is the dominant choice in the LLM tooling ecosystem as of 2025; version needs PyPI verification.

---

### Local Session Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| JSON files (stdlib) | n/a | Primary session storage format | Human-readable, grep-able, git-diffable, zero dependencies. One file per session. |
| SQLite (stdlib `sqlite3`) | n/a | Aggregate query index | Enables `SELECT AVG(efficiency_score) WHERE model='claude-opus-4'` without loading all JSON. Built into Python — no install. |
| `pathlib.Path` (stdlib) | n/a | File path management | Cross-platform path handling without string manipulation. |

**Storage architecture (two-layer):**

```
~/.cipherbench/
  sessions/
    {session_id}.json       # full session trace (one file per run)
  index.db                  # SQLite index: session_id, model, puzzle_seed, score, timestamp
```

**Why JSON as the primary store:** SESSION traces are the authoritative record. They contain the full prompt/response sequence, per-attempt feedback, final answer, and metadata. JSON preserves this structure naturally. Each session is a self-contained document — you can inspect, share, and replay any session by reading one file. This matches how lm-evaluation-harness, EleutherAI's benchmark suite, and BIG-bench all store results.

**Why SQLite as the index:** JSON is terrible for aggregation queries ("average score across all Claude runs on difficulty=hard"). SQLite solves this without a server. The index contains denormalized scalar fields only — the full trace stays in JSON. This is the pattern used by mlflow's file-based backend and by pytest-benchmark.

**Why not CSV:** CSV loses nested structure. CipherBench sessions have nested arrays (attempt sequence, per-character feedback). Flattening to CSV requires either denormalization (one row per attempt, repeated session metadata) or JSON columns inside CSV — at which point you've just invented a worse JSON. CSV is appropriate only for final aggregated scores exported for spreadsheet analysis, not for the canonical session store.

**Why not a "real" database (PostgreSQL, MongoDB):** PROJECT.md explicitly states "No external DB — session data stored as local JSON/CSV files — no server infrastructure required." This is a hard constraint. The JSON + SQLite pattern satisfies it completely while providing queryability.

**Confidence:** HIGH — stdlib-only for the storage layer is the correct call given the constraint. JSON + SQLite for this exact use case is a well-established pattern in Python benchmarking tooling.

---

### Python Packaging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pyproject.toml` + `hatchling` | `>=1.21` build backend | Package definition and CLI entry point registration | PEP 517/518 compliant. hatchling is the modern build backend (used by FastAPI, Pydantic, Typer). No `setup.py`. |
| `uv` | `>=0.4` | Dependency management and virtual env | Replaces pip + pip-tools + venv. 10-100x faster installs. Lockfile support via `uv.lock`. The 2025 community standard. |

**pyproject.toml CLI entry point pattern:**
```toml
[project]
name = "cipherbench"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "rich>=13.0",
    "litellm>=1.40",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "hypothesis>=6.100",
    "pytest-asyncio>=0.23",
]

[project.scripts]
cipherbench = "cipherbench.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Why `[project.scripts]` over `console_scripts` in `setup.py`:** `[project.scripts]` is the PEP 621 standard. It installs a `cipherbench` binary that calls `cipherbench.cli:app` (the Typer app object). After `pip install -e .` or `uv pip install -e .`, the CLI is available as `cipherbench run`, `cipherbench play`, `cipherbench inspect`.

**Why hatchling over setuptools:** setuptools still works but requires more configuration. hatchling has zero-config src layout support, is faster, and is the build backend used by the FastAPI/Typer ecosystem — the same tools CipherBench depends on.

**Why uv over pip + venv:** uv resolves and installs dependencies from a lockfile in seconds, not minutes. For a research tool that researchers will clone and run, fast setup matters. uv is now the de-facto standard for new Python projects in 2025.

**Why Python >=3.11:** `tomllib` (stdlib TOML parsing), `match` statement for pattern dispatch in the rule engine, better error messages. Pydantic v2 and LiteLLM both require 3.9+ but 3.11 gives meaningful runtime performance improvements. 3.12 is stable but 3.11 remains the safer minimum for broad compatibility with CI runners.

**Confidence:** HIGH for pyproject.toml structure (PEP 621, stable). MEDIUM for hatchling and uv version numbers (verify against PyPI).

---

### Testing Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | `>=8.0` | Primary test runner | Industry standard. Fixture system maps naturally to CipherBench's stateful rule engine — fixtures initialize cipher state, tests verify transition behavior. |
| Hypothesis | `>=6.100` | Property-based testing for rule engine | Generates adversarial puzzle configurations automatically. Finds edge cases in the rule engine that hand-written tests miss. |
| pytest-asyncio | `>=0.23` | Async test support | LiteLLM calls are async-capable; if async model runner is used, this is needed. |

**Why Hypothesis for the rule engine specifically:** CipherBench's rule engine has three composable layers (State, Cross-Character, Hidden Feedback) that interact in combinatorial ways. Writing exhaustive unit tests for all layer combinations is intractable. Hypothesis generates random puzzle configs and attempt sequences, then shrinks failures to minimal reproducible cases. This is precisely the use case property-based testing was designed for.

**Hypothesis strategy sketch for the rule engine:**
```python
from hypothesis import given, settings
from hypothesis import strategies as st
from cipherbench.engine import RuleEngine, CipherConfig

@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    difficulty=st.sampled_from(["easy", "medium", "hard"]),
    attempts=st.lists(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=5, max_size=5), max_size=5),
)
def test_engine_never_reveals_hidden_state(seed, difficulty, attempts):
    engine = RuleEngine(CipherConfig(seed=seed, difficulty=difficulty))
    for attempt in attempts:
        feedback = engine.score(attempt)
        # Feedback must never include the actual cipher key
        assert engine.cipher_key not in str(feedback)
```

**Why pytest over unittest:** unittest is stdlib but its class-based structure is verbose. pytest's function-based tests and fixture injection are more readable and produce better failure output. The entire Python testing community has converged on pytest.

**Confidence:** HIGH for pytest and Hypothesis — both are stable, widely used, and version ranges are safe. MEDIUM for exact version numbers.

---

### Reproducibility and Seeding

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `random.Random(seed)` (stdlib) | n/a | Per-puzzle RNG instance | Instantiated fresh per puzzle; does not pollute global `random` state. |
| `numpy.random.default_rng(seed)` | `>=1.26` | If numeric sampling needed | NumPy's PCG64 generator is reproducible and statistically superior to Mersenne Twister. Only add if puzzle generation needs array-level sampling. |

**Seeding pattern — the right approach:**
```python
# puzzle_generator.py
import random

class PuzzleGenerator:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)   # isolated instance, not random.seed()
    
    def generate(self) -> Puzzle:
        # All randomness goes through self.rng, never through random.randint() directly
        cipher_key = self.rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5)
        ...
```

**Why `random.Random(seed)` over `random.seed(seed)`:** `random.seed()` mutates global state. If any library (including LiteLLM internals, test fixtures, etc.) also calls `random`, the sequence diverges unpredictably. A `random.Random(seed)` instance is a self-contained generator — its sequence is determined solely by the seed and the calls made to that instance. This is the only safe pattern for reproducible procedural generation in a library.

**Why seed stored in session JSON:** Every session file records `puzzle_seed` so any session can be replayed exactly: load the seed, reconstruct the puzzle, replay the attempt sequence, verify the scores match. This enables the `cipherbench inspect` command and future regression testing of the rule engine.

**Confidence:** HIGH — stdlib `random.Random` instance pattern is well-established. The concern about global state pollution is a documented pitfall in Python.

---

## What NOT to Use

| Category | Rejected Option | Reason |
|----------|-----------------|--------|
| CLI | argparse | Verbose, no auto-help for subcommands, no type inference. Acceptable for one-file scripts, not for a multi-command SDK. |
| CLI | Click (direct) | Typer wraps Click and adds type-annotation ergonomics. No reason to use raw Click unless you need Click plugin ecosystem specifically. |
| LLM client | `instructor` | Structured output extraction tool, not a provider router. Wrong abstraction for this use case. |
| LLM client | Raw provider SDKs | Lock-in. Adding a second provider requires duplicating auth, retry, and response-parsing code. |
| Storage | CSV primary store | Loses nested structure. Round-trip fidelity not guaranteed for complex objects. |
| Storage | PostgreSQL / MongoDB | Violates PROJECT.md constraint. Server infrastructure required. |
| Storage | DuckDB | Powerful but overkill for local benchmark storage. SQLite covers all aggregate query needs. |
| Testing | unittest | Class-based boilerplate. No fixture injection. Inferior output. Pytest is the standard. |
| Packaging | setup.py | Deprecated approach. pyproject.toml is the PEP 517/518 standard. |
| Packaging | Poetry | Valid choice but heavier than needed. uv + hatchling achieves the same with less abstraction. |
| RNG | `random.seed()` (global) | Global state mutation. Breaks reproducibility when any other code touches `random`. |
| RNG | `secrets` module | Cryptographically secure but explicitly non-reproducible. Wrong for benchmark seeding. |

---

## Installation

```bash
# Project setup with uv (recommended)
uv init cipherbench
uv add typer rich litellm
uv add --dev pytest hypothesis pytest-asyncio

# Or with pip (compatible)
pip install -e ".[dev]"
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI | Typer | Click | Typer adds type-annotation layer over Click with no functionality loss |
| CLI | Typer | argparse | argparse is stdlib but verbose and produces worse help text |
| LLM Router | LiteLLM | Raw SDKs per provider | Defeats provider-agnostic constraint, duplicates retry/auth logic |
| LLM Router | LiteLLM | instructor | Wrong abstraction — extraction tool, not router |
| Storage | JSON + SQLite | DuckDB | SQLite covers all needs with zero install; DuckDB is overkill |
| Storage | JSON + SQLite | CSV | Loses nested structure; round-trip lossy |
| Build | hatchling | setuptools | setuptools works but requires more config; hatchling zero-config for src layout |
| Dep mgmt | uv | Poetry | Both valid; uv is faster and lighter; Poetry adds its own lockfile format |
| RNG | `random.Random(seed)` | `random.seed()` | Global state mutation breaks reproducibility under any concurrent or library use |

---

## Version Verification Required

The following versions are from training data and must be verified against PyPI before pinning:

| Library | Training-data version | Verify at |
|---------|----------------------|-----------|
| typer | 0.12.x | https://pypi.org/project/typer/ |
| click | 8.1.x | https://pypi.org/project/click/ |
| rich | 13.x | https://pypi.org/project/rich/ |
| litellm | 1.40+ | https://pypi.org/project/litellm/ |
| pytest | 8.x | https://pypi.org/project/pytest/ |
| hypothesis | 6.100+ | https://pypi.org/project/hypothesis/ |
| pytest-asyncio | 0.23+ | https://pypi.org/project/pytest-asyncio/ |
| hatchling | 1.21+ | https://pypi.org/project/hatchling/ |
| uv | 0.4+ | https://docs.astral.sh/uv/ |
| numpy | 1.26+ (optional) | https://pypi.org/project/numpy/ |

---

## Sources

- Typer documentation: https://typer.tiangolo.com (MEDIUM confidence — training data)
- Click documentation: https://click.palletsprojects.com (MEDIUM confidence — training data)
- LiteLLM documentation: https://docs.litellm.ai (MEDIUM confidence — training data)
- Hypothesis documentation: https://hypothesis.readthedocs.io (HIGH confidence — stable library)
- pytest documentation: https://docs.pytest.org (HIGH confidence — stable library)
- PEP 517/518/621 — pyproject.toml standard: https://peps.python.org/pep-0621/ (HIGH confidence — ratified standard)
- uv documentation: https://docs.astral.sh/uv/ (MEDIUM confidence — rapidly evolving tool)
- Python `random.Random` isolation pattern: https://docs.python.org/3/library/random.html (HIGH confidence — stdlib)
- Note: External verification tools (Bash, WebSearch, WebFetch) were unavailable during this research session. All version numbers require PyPI verification before use.
