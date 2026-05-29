"""Unit tests for HumanSessionRunner — SESS-02."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Guard: skip entire module if human_runner not yet implemented
pytest.importorskip("cipherbench.session.human_runner")

from cipherbench.session.human_runner import HumanSessionRunner, create_human_session  # noqa: E402
from cipherbench.puzzle import EASY  # noqa: E402


# ---------------------------------------------------------------------------
# SESS-02: human session runner — JSON schema matches model runner (D-11)
# ---------------------------------------------------------------------------


def test_human_session_json_schema_matches_model(tmp_sessions_dir):
    """SESS-02: Human session JSON uses the same top-level schema as model sessions (D-11).

    Patches typer.prompt to supply 5 valid EASY probes then a final answer.
    Asserts runner_type='human', model=None, player_name='alice', and that all
    D-11 top-level fields are present in the written JSON file.
    """
    # EASY alphabet is "ABCDEFGHIJ", output_length=5
    # Supply 5 valid probes + final answer prompt
    probe_responses = ["ABCDE", "BCDEF", "CDEFG", "DEFGH", "EFGHI", "ABCDE"]
    with patch("typer.prompt", side_effect=probe_responses):
        runner = create_human_session(
            seed=42,
            difficulty=EASY,
            player_name="alice",
            output_dir=tmp_sessions_dir,
        )
        session_record = runner.run()

    # D-11 top-level fields
    assert session_record["runner_type"] == "human"
    assert session_record["model"] is None
    assert session_record["player_name"] == "alice"
    assert session_record["seed"] == 42
    assert "difficulty" in session_record
    assert "puzzle_hash" in session_record
    assert "outcome" in session_record
    assert "final_answer" in session_record
    assert "attempts" in session_record
    assert "created_at" in session_record
    assert "completed_at" in session_record

    # D-08: all attempts have raw_response=None and extraction_failed=False
    for attempt in session_record["attempts"]:
        assert attempt["raw_response"] is None
        assert attempt["extraction_failed"] is False

    # Verify session JSON was written to disk
    session_files = list(tmp_sessions_dir.glob("*.json"))
    assert len(session_files) == 1
    with session_files[0].open(encoding="utf-8") as f:
        disk_record = json.load(f)
    assert disk_record["runner_type"] == "human"


# ---------------------------------------------------------------------------
# SESS-02: input validation — re-prompt on invalid length (D-05)
# ---------------------------------------------------------------------------


def test_human_runner_rejects_invalid_length_input(tmp_sessions_dir):
    """SESS-02: HumanSessionRunner re-prompts (does not raise) on wrong-length input.

    Patches typer.prompt so that the first call returns "AB" (too short for EASY
    output_length=5), and subsequent calls return valid 5-char EASY probes.
    Asserts no ValueError is raised and the attempts list contains valid entries.
    """
    # First prompt: "AB" (invalid, too short), then 5 valid probes + final answer
    probe_responses = ["AB", "ABCDE", "BCDEF", "CDEFG", "DEFGH", "EFGHI", "ABCDE"]
    with patch("typer.prompt", side_effect=probe_responses):
        runner = create_human_session(
            seed=42,
            difficulty=EASY,
            player_name="tester",
            output_dir=tmp_sessions_dir,
        )
        # Should not raise — re-prompt loop handles invalid input
        session_record = runner.run()

    # All attempts must have valid probes (invalid input consumed re-prompt, not attempt budget)
    valid_attempts = [a for a in session_record["attempts"] if not a["extraction_failed"]]
    assert len(valid_attempts) >= 1
    # Probe field must be 5 chars from EASY alphabet
    for attempt in valid_attempts:
        assert attempt["probe"] is not None
        assert len(attempt["probe"]) == 5
        assert all(c in EASY.alphabet for c in attempt["probe"])


# ---------------------------------------------------------------------------
# SESS-02: input validation — re-prompt on chars outside alphabet (D-05)
# ---------------------------------------------------------------------------


def test_human_runner_rejects_chars_outside_alphabet(tmp_sessions_dir):
    """SESS-02: HumanSessionRunner re-prompts (does not raise) when chars outside alphabet.

    EASY alphabet is 'ABCDEFGHIJ'. 'K' is outside this alphabet.
    First prompt returns 'ABCDK' (K is outside EASY alphabet).
    Second prompt returns 'ABCDA' (valid EASY chars).
    Asserts no ValueError and re-prompt occurred without crash.
    """
    # ABCDK: K is outside EASY alphabet "ABCDEFGHIJ"
    # Then provide enough valid responses to complete the session
    probe_responses = ["ABCDK", "ABCDA", "BCDEF", "CDEFG", "DEFGH", "EFGHI", "ABCDE"]
    with patch("typer.prompt", side_effect=probe_responses):
        runner = create_human_session(
            seed=42,
            difficulty=EASY,
            player_name="tester2",
            output_dir=tmp_sessions_dir,
        )
        # Must not raise — re-prompt handles the invalid 'K'
        session_record = runner.run()

    # First valid attempt must be 'ABCDA' (not 'ABCDK')
    assert len(session_record["attempts"]) >= 1
    assert session_record["attempts"][0]["probe"] == "ABCDA"
