"""Unit tests for report_writer — D-12 JSON report file output."""
from __future__ import annotations

import json

import pytest

writer_mod = pytest.importorskip("cipherbench.scoring.report_writer")
write_json_report = writer_mod.write_json_report


@pytest.mark.skip(reason="Wave 0 stub — implement in Wave 2")
def test_write_json_report_creates_file(tmp_path):
    """Creates file and writes valid JSON."""
    report = {
        "model": "test/model",
        "sessions_scored": 3,
        "by_difficulty": {
            "easy": {"sessions": 3, "success_rate": 0.67, "avg_efficiency": 0.6, "agi_proximity": None}
        },
        "totals": {"sessions": 3, "success_rate": 0.67, "avg_efficiency": 0.6, "agi_proximity": None},
        "generated_at": "2026-05-29T00:00:00Z",
    }
    out = tmp_path / "report.json"
    write_json_report(report, out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["model"] == "test/model"
    assert data["totals"]["agi_proximity"] is None  # D-12: null not string "N/A"


@pytest.mark.skip(reason="Wave 0 stub — implement in Wave 2")
def test_write_json_report_null_agi_proximity(tmp_path):
    """D-12: None stored as JSON null not string "N/A"."""
    report = {
        "totals": {"sessions": 1, "success_rate": 0.0, "avg_efficiency": 0.0, "agi_proximity": None},
    }
    out = tmp_path / "report.json"
    write_json_report(report, out)
    raw = out.read_text()
    assert '"agi_proximity": null' in raw
    assert "N/A" not in raw


@pytest.mark.skip(reason="Wave 0 stub — implement in Wave 2")
def test_write_json_report_creates_parent_dirs(tmp_path):
    """Creates intermediate directories."""
    out = tmp_path / "nested" / "deep" / "report.json"
    write_json_report({"model": "test"}, out)
    assert out.exists()
