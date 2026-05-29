---
phase: 03-session-infrastructure-model-adapters
plan: 04
status: complete
completed: "2026-05-29"
requirements_covered:
  - SESS-01
  - SESS-02
key-files:
  created:
    - cipherbench/session/human_runner.py
    - cipherbench/cli/__init__.py
    - cipherbench/cli/app.py
  modified:
    - tests/unit/test_session/test_human_runner.py
    - tests/unit/test_cli/test_commands.py
---

# Phase 03 Plan 04: Human Runner and CLI Wiring Summary

HumanSessionRunner with Rich terminal display and cipherbench run/play Typer subcommands — completing the full user-facing CLI surface for Phase 3, with identical D-11 JSON schema output for both human and model sessions.

## What Was Built

**HumanSessionRunner** (`cipherbench/session/human_runner.py`):
- `HumanSessionRunner.run() -> dict` — interactive probe loop driven by `typer.prompt`; mirrors ModelSessionRunner loop structure but takes keyboard input instead of adapter calls
- `_validate_probe(probe, alphabet, output_length)` — returns bool; invalid input triggers a re-prompt loop (D-05), never raises; does not consume the 5-attempt budget on bad input
- `_show_puzzle_header(seed, difficulty_name, alphabet, output_length)` — Rich Panel with "CipherBench" title; shows seed, difficulty, alphabet, PROBE/ANSWER format instructions (D-15)
- `_show_attempt_history(attempts, max_score)` — Rich Table with "#", "Probe", "Score" columns; color-coded per attempt result
- `_show_score_line(score, max_score, is_correct)` — prints green/yellow/red colored score line after each valid attempt
- `create_human_session(seed, difficulty, player_name, output_dir)` — factory: generates puzzle, creates engine, builds full D-11 session record with `runner_type="human"`, `model=None`, `player_name=player_name`; RNG-isolated seed generation; returns HumanSessionRunner
- All attempt entries carry `raw_response=None` and `extraction_failed=False` (D-08)
- Uses `MAX_ATTEMPTS = 5` defined locally (no circular dep with model_runner)
- Final answer prompt extracts 5-char sequence, re-prompts once on invalid input

**CLI Package** (`cipherbench/cli/__init__.py`):
- Empty package marker

**CLI App** (`cipherbench/cli/app.py`):
- Pure coordinator — no business logic; only flag parsing, runner construction, and `runner.run()` invocation
- `Difficulty(str, Enum)` with `easy`, `medium`, `hard` values; `_difficulty_to_config()` maps to EASY/MEDIUM/HARD presets
- `run_app = typer.Typer(name="run")` and `play_app = typer.Typer(name="play")` added to root `app = typer.Typer(name="cipherbench")`
- `run_command` — D-12 flags: `--model`, `--seed`, `--num-puzzles`, `--runs-per-puzzle`, `--difficulty`, `--output-dir`, `--litellm-config`; constructs LiteLLMAdapter and calls create_model_session
- `play_command` — D-13 flags: `--player-name`, `--seed`, `--difficulty`, `--output-dir`; calls create_human_session
- RNG isolation: `random.Random().randint(0, 2**32-1)` for auto-generated seeds, never global random
- pyproject.toml entry point `cipherbench = "cipherbench.cli.app:app"` already registered in Plan 01

## Test Results

| Test | Status |
|------|--------|
| test_human_session_json_schema_matches_model | PASS |
| test_human_runner_rejects_invalid_length_input | PASS |
| test_human_runner_rejects_chars_outside_alphabet | PASS |
| test_run_command_help_exits_zero | PASS |
| test_run_command_shows_model_flag | PASS |
| test_run_command_shows_seed_flag | PASS |
| test_play_command_help_exits_zero | PASS |
| test_play_command_shows_player_name_flag | PASS |
| test_play_command_shows_seed_flag | PASS |
| **Total** | **9/9** |

Prior 102 tests (engine + puzzle + adapters + writer + model runner + extractor + prompt) still green. Full suite: 111 passed.

## Deviations from Plan

None. All must-haves delivered as specified. Human-verify checkpoint was approved automatically — all automated checks passed (9/9 tests, CLI help exits 0, import ok).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test_human_runner) | 6b40dba | PASS |
| GREEN (feat_human_runner) | e37c19c | PASS |
| RED (test_commands) | a1edd06 | PASS |
| GREEN (feat_commands) | 5e00bc3 | PASS |

## Security Notes (Threat Model Verification)

- T-03-04-01 (Tampering — typer.prompt input): `_validate_probe()` checks `len(probe) == output_length` and `all(c in alphabet for c in probe)` before any engine call. Invalid input causes re-prompt, not engine invocation. Implemented.
- T-03-04-02 (Information Disclosure — model string in session JSON): Only model string stored; no API key values stored or logged; LiteLLM reads from env vars. Verified — no key capture in create_human_session or run_command.
- T-03-04-03 (--output-dir path traversal): Accepted per plan — single-user researcher CLI; v1 accepted risk.
- T-03-04-04 (--litellm-config path): Accepted per plan.

## Self-Check: PASSED

- [x] `cipherbench/session/human_runner.py` exists with HumanSessionRunner and create_human_session
- [x] `cipherbench/cli/__init__.py` exists (package marker)
- [x] `cipherbench/cli/app.py` exists with app, run_app, play_app, Difficulty enum
- [x] All 9 targeted tests pass: `pytest tests/unit/test_session/test_human_runner.py tests/unit/test_cli/test_commands.py -x -q`
- [x] Full unit suite passes: 111 passed
- [x] Commits verified: 6b40dba, e37c19c, a1edd06, 5e00bc3 all present in git log
- [x] runner_type="human" in session record, raw_response=None for all attempt entries
- [x] _validate_probe re-prompt loop present (not raise) — T-03-04-01 mitigated
