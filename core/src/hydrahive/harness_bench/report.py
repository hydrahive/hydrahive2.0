"""Zusammenfassung und Vorher/Nachher-Vergleich von Benchmark-Läufen."""
from __future__ import annotations

from statistics import median

from hydrahive.runner._measured_usage import prompt_tokens_from_metadata


def input_tokens(row: dict) -> int:
    """Gesendete Eingabe-Tokens eines Laufs, je Anbieter richtig gezählt.

    Codex meldet gecachte Tokens bereits in `prompt_tokens`; sie dazuzuzählen verdoppelt den Cache-Anteil
    (Baseline 09.11.2026: bugfix 55.967 statt 42.271). Anthropic weist Cache-Lesen und -Schreiben getrennt aus.
    Ältere Rohdaten haben kein `cache_creation_tokens`.
    """
    return prompt_tokens_from_metadata({
        "input_tokens": row["prompt_tokens"], "cache_read_tokens": row["cache_read_tokens"],
        "cache_creation_tokens": row.get("cache_creation_tokens", 0), "model": row["model"],
    })


def summarize(results: list[dict]) -> dict[str, dict]:
    by_task: dict[str, list[dict]] = {}
    for row in results:
        by_task.setdefault(row["task"], []).append(row)
    summary = {}
    for task, rows in by_task.items():
        costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
        summary[task] = {
            "runs": len(rows),
            "success_rate": round(sum(r["success"] for r in rows) / len(rows), 2),
            "median_seconds": median(r["seconds"] for r in rows),
            "median_input_tokens": median(input_tokens(r) for r in rows),
            "median_output_tokens": median(r["completion_tokens"] for r in rows),
            "median_tool_errors": median(r["tool_errors"] for r in rows),
            "total_cost_usd": round(sum(costs), 4) if costs else None,
        }
    return summary


def markdown(summary: dict[str, dict], *, title: str) -> str:
    header = ("| Aufgabe | Läufe | Erfolg | Median s | Median Input-Tokens | Median Output-Tokens "
              "| Tool-Fehler | Kosten $ |")
    lines = [f"## {title}", "", header, "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for task, s in summary.items():
        cost = "Abo" if s["total_cost_usd"] is None else f"{s['total_cost_usd']:.4f}"
        lines.append(f"| {task} | {s['runs']} | {s['success_rate']:.0%} | {s['median_seconds']:.0f} | "
                     f"{s['median_input_tokens']:,.0f} | {s['median_output_tokens']:,.0f} | "
                     f"{s['median_tool_errors']:.0f} | {cost} |")
    return "\n".join(lines)


def compare(before: dict[str, dict], after: dict[str, dict]) -> str:
    lines = ["| Aufgabe | Erfolg vorher → nachher | Input-Tokens Δ | Dauer Δ |", "|---|---|---:|---:|"]
    for task in before.keys() & after.keys():
        b, a = before[task], after[task]
        tok = (a["median_input_tokens"] - b["median_input_tokens"]) / max(b["median_input_tokens"], 1)
        sec = (a["median_seconds"] - b["median_seconds"]) / max(b["median_seconds"], 1)
        lines.append(f"| {task} | {b['success_rate']:.0%} → {a['success_rate']:.0%} | {tok:+.0%} | {sec:+.0%} |")
    return "\n".join(lines)
