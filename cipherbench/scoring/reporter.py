"""CipherBench scoring reporter — Rich terminal output for score reports (D-11).

Public names:
  render_score_report  — print Rich Panel + Table for a ScoreReport
  render_live_summary  — print one-line summary for end of cipherbench run (D-03)

Design decisions:
  D-11  Rich Panel header: model name + session count
  D-11  Rich Table columns: Difficulty | Sessions | Success Rate | Avg Efficiency | AGI Proximity | Probe Efficiency | Avg Known Info
  D-11  Solution probability shown as separate breakdown table (known_info → success rate)
  D-03  Live summary: one typer.echo line only — no Rich components
"""
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from cipherbench.scoring.scorer import ScoreReport

_console = Console()


def render_score_report(report: "ScoreReport", model: str) -> None:
    """Print Rich Panel header + per-difficulty Table to terminal (D-11).

    Parameters
    ----------
    report : ScoreReport
        Structured scoring result from compute_report().
    model : str
        Model identifier string shown in the Panel title.
    """
    # Panel header — matches _show_puzzle_header style from human_runner.py
    _console.print(
        Panel(
            f"Model: {model}  |  Sessions scored: {report['sessions_scored']}",
            title="[bold]CipherBench Score Report[/bold]",
        )
    )

    # Table — matches _show_attempt_history style (show_header=True, header_style="bold")
    table = Table(title="Score Breakdown", show_header=True, header_style="bold")
    table.add_column("Difficulty", min_width=10)
    table.add_column("Sessions", justify="right", min_width=8)
    table.add_column("Success Rate", justify="right", min_width=12)
    table.add_column("Avg Efficiency", justify="right", min_width=14)
    table.add_column("AGI Proximity", justify="right", min_width=13)
    table.add_column("Probe Efficiency", justify="right", min_width=16)
    table.add_column("Avg Known Info", justify="right", min_width=14)

    for tier, stats in report["by_difficulty"].items():
        proximity_str = (
            f"{stats['agi_proximity']:.2f}x"
            if stats["agi_proximity"] is not None
            else "N/A"
        )
        pe_str = (
            f"{stats['avg_probe_efficiency']:.2f}"
            if stats["avg_probe_efficiency"] is not None
            else "N/A"
        )
        table.add_row(
            tier,
            str(stats["sessions"]),
            f"{stats['success_rate']:.0%}",
            f"{stats['avg_efficiency']:.2f}",
            proximity_str,
            pe_str,
            f"{stats['avg_known_info']:.1f}/26",
        )

    # Totals row — bold to distinguish
    totals = report["totals"]
    proximity_str = (
        f"{totals['agi_proximity']:.2f}x"
        if totals["agi_proximity"] is not None
        else "N/A"
    )
    total_pe_str = (
        f"{totals['avg_probe_efficiency']:.2f}"
        if totals["avg_probe_efficiency"] is not None
        else "N/A"
    )
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{totals['sessions']}[/bold]",
        f"[bold]{totals['success_rate']:.0%}[/bold]",
        f"[bold]{totals['avg_efficiency']:.2f}[/bold]",
        f"[bold]{proximity_str}[/bold]",
        f"[bold]{total_pe_str}[/bold]",
        f"[bold]{totals['avg_known_info']:.1f}/26[/bold]",
    )
    _console.print(table)

    # Solution probability breakdown — success rate per known_info level (x → y)
    sp = totals["solution_probability"]
    if sp:
        sp_table = Table(
            title="Solution Probability  (chars known → success rate)",
            show_header=True,
            header_style="bold",
        )
        sp_table.add_column("Chars Known (x)", justify="center", min_width=15)
        sp_table.add_column("Success Rate (y)", justify="center", min_width=16)
        for ki, sr in sp.items():
            style = "green" if sr >= 0.5 else ("yellow" if sr > 0 else "red")
            sp_table.add_row(str(ki), f"[{style}]{sr:.0%}[/{style}]")
        _console.print(sp_table)

    # D-10 hint when no baseline available
    if totals["agi_proximity"] is None:
        _console.print(
            "[dim]Hint: Run `cipherbench play` to record a human baseline.[/dim]"
        )


def render_live_summary(sessions: list[dict], human_sessions: list[dict]) -> None:
    """Print one-line summary at end of cipherbench run (D-03).

    Format: "3/5 success (60%) | avg efficiency: 0.72 | AGI proximity: 0.85x"
    Uses typer.echo (not Rich console) to keep run output clean.

    Parameters
    ----------
    sessions : list[dict]
        Completed model sessions for the current run.
    human_sessions : list[dict]
        Human baseline sessions for AGI proximity calculation (SCORE-03).
    """
    # Lazy import to avoid any circular dependency
    from cipherbench.scoring.scorer import agi_proximity, efficiency_score, success_rate

    total = len(sessions)
    successes = sum(1 for s in sessions if s.get("outcome") == "success")
    sr = success_rate(sessions)
    avg_eff = (
        sum(efficiency_score(s) for s in sessions) / total if total else 0.0
    )
    proximity = agi_proximity(sessions, human_sessions)
    proximity_str = f"{proximity:.2f}x" if proximity is not None else "N/A"
    typer.echo(
        f"{successes}/{total} success ({sr:.0%}) | "
        f"avg efficiency: {avg_eff:.2f} | AGI proximity: {proximity_str}"
    )
