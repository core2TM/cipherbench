# CipherBench

A Python benchmark that tests LLMs on a stateful cipher challenge — designed to resist the pattern-recognition shortcuts that make current benchmarks too easy.

Models probe a hidden rule system with up to 5 attempts and must infer the cipher from scored feedback alone, then produce a correct final answer. Scores are compared against a human baseline to estimate relative AGI proximity.

**A model that solves CipherBench has demonstrated genuine hypothesis-driven reasoning under uncertainty — not statistical pattern matching.**

---

## Installation

Requires Python 3.11+.

```bash
# Clone the repo
git clone https://github.com/core2TM/cipherbench.git
cd cipherbench

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

Set your API key for whichever provider you want to benchmark:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
# etc. — LiteLLM reads standard provider env vars automatically
```

---

## Usage

### Play a puzzle yourself (builds human baseline)

```bash
cipherbench play --player-name yourname --difficulty medium
```

### Run a model

```bash
cipherbench run --model anthropic/claude-opus-4-7 --difficulty medium
cipherbench run --model openai/gpt-4o --seed 42 --num-puzzles 5
```

### Score results

```bash
cipherbench score --model anthropic/claude-opus-4-7
cipherbench score --human    # score your own play sessions
```

### Replay a session

```bash
cipherbench inspect <session-id>
```

---

## All Commands

### `cipherbench run`

```
--model             LiteLLM model string, e.g. anthropic/claude-opus-4-7  (required)
--seed              RNG seed for reproducibility (default: random)
--num-puzzles       Number of distinct puzzles to run (default: 1)
--runs-per-puzzle   Independent sessions per puzzle (default: 1)
--difficulty        easy | medium | hard (default: medium)
--output-dir        Where to write session JSON files (default: ./sessions)
--api-base          Base URL for a LiteLLM proxy server (optional)
```

### `cipherbench play`

```
--player-name       Name stored in session JSON (default: human)
--seed              RNG seed (default: random)
--difficulty        easy | medium | hard (default: medium)
--output-dir        Where to write session JSON files (default: ./sessions)
```

### `cipherbench score`

```
--model             Filter by model string (optional)
--sessions-dir      Where to read session files (default: ./sessions)
--difficulty        Filter by difficulty (optional)
--output-file       Write JSON report to this path (optional)
--human             Score human sessions instead of model sessions
```

### `cipherbench inspect`

```
<session-id>        Session ID or substring to match (required)
--sessions-dir      Where to read session files (default: ./sessions)
```

---

## Typical Workflow

1. Play a few puzzles yourself to build a human baseline
2. Run a model against the same difficulty
3. Score the model vs. your baseline
4. Inspect interesting sessions to see where the model went wrong

---

## Reproducibility

Pass `--seed` to pin the puzzle RNG. The same seed always produces the same puzzle, so you can compare different models on identical inputs:

```bash
cipherbench run --model anthropic/claude-opus-4-7 --seed 42
cipherbench run --model openai/gpt-4o --seed 42
cipherbench score
```

---

## Supported Providers

Any provider supported by [LiteLLM](https://docs.litellm.ai/docs/providers) works out of the box — Anthropic, OpenAI, Google Gemini, Mistral, Cohere, and 100+ others.

---

## Development

```bash
uv sync --extra dev
pytest
```
