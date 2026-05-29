"""Unit tests for scoring reporter — Rich terminal output (D-11, D-03)."""
from __future__ import annotations

import pytest

reporter_mod = pytest.importorskip("cipherbench.scoring.reporter")
render_score_report = reporter_mod.render_score_report
render_live_summary = reporter_mod.render_live_summary


@pytest.mark.skip(reason="Wave 0 stub — implement in Wave 2")
def test_render_score_report_prints_panel():
    """D-11: output contains model name in panel."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implement in Wave 2")
def test_render_score_report_prints_table():
    """D-11: output contains difficulty tier rows."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implement in Wave 2")
def test_render_score_report_na_hint():
    """D-10: hint printed when agi_proximity is None."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implement in Wave 2")
def test_render_live_summary_format():
    """D-03: one-line format N/M success (P%) | avg efficiency: X.XX | AGI proximity: Y.YYx."""
    pass
