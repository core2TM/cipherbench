<!-- GSD:project-start source:PROJECT.md -->
## Project

**CipherBench — AGI Proximity Benchmark**

CipherBench is a Python SDK and CLI benchmark that tests LLMs on a stateful, cross-character, feedback-hidden cipher challenge — designed to resist the pattern-recognition shortcuts that make current benchmarks too easy. Models probe a rule system with up to 5 attempts and must infer the cipher from scored feedback alone, then produce a correct final answer. Scores are compared against a human baseline (recorded via CLI play) to estimate relative AGI proximity.

**Core Value:** A model that solves CipherBench has demonstrated genuine hypothesis-driven reasoning under uncertainty — not statistical pattern matching — making the gap to human performance a credible AGI distance signal.

### Constraints

- **Tech stack**: Python — SDK-first, importable as a library and runnable as a CLI
- **Provider-agnostic**: Model runner must not bake in a single provider; use a pluggable adapter pattern
- **Reproducibility**: Every puzzle instance is seeded (RNG seed) so results are reproducible
- **No external DB**: Session data stored as local JSON/CSV files — no server infrastructure required
- **Attempt limit**: Fixed at 5 probe attempts per puzzle (a core mechanic, not configurable in v1)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### CLI Interface
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Typer | `>=0.12` | Primary CLI framework | Type-annotated commands, auto-generates help text, built on Click so Click plugins still work. Zero boilerplate for subcommands. First-class support for `Annotated[]` param style introduced in 0.9+. |
| Rich | `>=13.0` | Terminal output formatting | Typer ships Rich integration; used for progress bars, session replay tables, colored feedback display. No extra wiring needed. |
### Provider-Agnostic LLM Client
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| LiteLLM | `>=1.40` | Unified API across all frontier providers | Single `completion()` call works for Anthropic, OpenAI, Google Gemini, Mistral, Cohere, and 100+ others. Handles auth, retry, rate-limit, and response normalization. |
# providers/litellm_runner.py
### Local Session Storage
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| JSON files (stdlib) | n/a | Primary session storage format | Human-readable, grep-able, git-diffable, zero dependencies. One file per session. |
| SQLite (stdlib `sqlite3`) | n/a | Aggregate query index | Enables `SELECT AVG(efficiency_score) WHERE model='claude-opus-4'` without loading all JSON. Built into Python — no install. |
| `pathlib.Path` (stdlib) | n/a | File path management | Cross-platform path handling without string manipulation. |
### Python Packaging
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pyproject.toml` + `hatchling` | `>=1.21` build backend | Package definition and CLI entry point registration | PEP 517/518 compliant. hatchling is the modern build backend (used by FastAPI, Pydantic, Typer). No `setup.py`. |
| `uv` | `>=0.4` | Dependency management and virtual env | Replaces pip + pip-tools + venv. 10-100x faster installs. Lockfile support via `uv.lock`. The 2025 community standard. |
### Testing Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | `>=8.0` | Primary test runner | Industry standard. Fixture system maps naturally to CipherBench's stateful rule engine — fixtures initialize cipher state, tests verify transition behavior. |
| Hypothesis | `>=6.100` | Property-based testing for rule engine | Generates adversarial puzzle configurations automatically. Finds edge cases in the rule engine that hand-written tests miss. |
| pytest-asyncio | `>=0.23` | Async test support | LiteLLM calls are async-capable; if async model runner is used, this is needed. |
### Reproducibility and Seeding
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `random.Random(seed)` (stdlib) | n/a | Per-puzzle RNG instance | Instantiated fresh per puzzle; does not pollute global `random` state. |
| `numpy.random.default_rng(seed)` | `>=1.26` | If numeric sampling needed | NumPy's PCG64 generator is reproducible and statistically superior to Mersenne Twister. Only add if puzzle generation needs array-level sampling. |
# puzzle_generator.py
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
## Installation
# Project setup with uv (recommended)
# Or with pip (compatible)
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
## Version Verification Required
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
