#!/usr/bin/env python3
"""Daily routing statistics report for hermes-adaptive-router.

Reads routing stats from a persistent JSON file and prints a formatted report.
Designed to run as a cron job at 22:00 daily.

To enable persistent tracking, configure a post-route callback in your
Hermes agent that writes to ~/.hermes/adaptive_router_history.jsonl
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Default history file location
DEFAULT_HISTORY_FILE = Path.home() / ".hermes" / "adaptive_router_history.jsonl"


def load_history_from_file(history_file: Path = DEFAULT_HISTORY_FILE) -> list[dict]:
    """Load routing events from JSONL file."""
    events = []
    if not history_file.exists():
        return events
    
    with open(history_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def compute_stats(events: list[dict]) -> dict:
    """Compute statistics from events."""
    total = len(events)
    if total == 0:
        return {"total": 0}
    
    counts: dict[str, int] = {}
    complexity_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    latencies: list[float] = []
    
    for ev in events:
        route = ev.get("route", {})
        counts[route.get("datasource", "unknown")] = counts.get(route.get("datasource", "unknown"), 0) + 1
        complexity_counts[route.get("complexity", "unknown")] = complexity_counts.get(route.get("complexity", "unknown"), 0) + 1
        strategy_counts[route.get("retrieval_strategy", "unknown")] = strategy_counts.get(route.get("retrieval_strategy", "unknown"), 0) + 1
        latencies.append(ev.get("latency_ms", 0))
    
    return {
        "total": total,
        "datasource_distribution": counts,
        "complexity_distribution": complexity_counts,
        "strategy_distribution": strategy_counts,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 3),
            "min": round(min(latencies), 3),
            "max": round(max(latencies), 3),
        },
    }


def format_report(events: list[dict] | None = None) -> str:
    """Generate a formatted daily routing report."""
    if events is None:
        events = load_history_from_file()
    
    stats = compute_stats(events)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Filter today's events
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_events = [
        ev for ev in events
        if datetime.fromtimestamp(ev.get("timestamp", 0)) >= today_start
    ]
    
    lines = [
        f"📊 *Adaptive Router Daily Report* — {today}",
        f"Generated: {now}",
        "",
        f"📈 *Total Queries*: `{stats.get('total', 0)}`",
        f"📅 *Today's Queries*: `{len(today_events)}`",
        "",
        "*Datasource Distribution*:",
    ]
    
    ds_dist = stats.get("datasource_distribution", {})
    total_ds = sum(ds_dist.values()) if ds_dist else 0
    if total_ds > 0:
        for ds, count in sorted(ds_dist.items(), key=lambda x: -x[1]):
            pct = (count / total_ds * 100) if total_ds > 0 else 0
            bar = "█" * int(pct / 5)
            lines.append(f"  `{ds:12s}`: {count:4d} ({pct:5.1f}%) {bar}")
    else:
        lines.append("  _(no data)_")
    
    lines.append("")
    lines.append("*Complexity Distribution*:")
    
    cx_dist = stats.get("complexity_distribution", {})
    total_cx = sum(cx_dist.values()) if cx_dist else 0
    if total_cx > 0:
        for cx, count in sorted(cx_dist.items(), key=lambda x: -x[1]):
            pct = (count / total_cx * 100) if total_cx > 0 else 0
            bar = "█" * int(pct / 5)
            lines.append(f"  `{cx:12s}`: {count:4d} ({pct:5.1f}%) {bar}")
    else:
        lines.append("  _(no data)_")
    
    lines.append("")
    lines.append("*Strategy Distribution*:")
    
    st_dist = stats.get("strategy_distribution", {})
    total_st = sum(st_dist.values()) if st_dist else 0
    if total_st > 0:
        for st, count in sorted(st_dist.items(), key=lambda x: -x[1]):
            pct = (count / total_st * 100) if total_st > 0 else 0
            bar = "█" * int(pct / 5)
            lines.append(f"  `{st:12s}`: {count:4d} ({pct:5.1f}%) {bar}")
    else:
        lines.append("  _(no data)_")
    
    latency = stats.get("latency_ms", {})
    if latency:
        lines.append("")
        lines.append("*Latency* (ms):")
        lines.append(f"  Mean: `{latency.get('mean', 'N/A')}`")
        lines.append(f"  Min:  `{latency.get('min', 'N/A')}`")
        lines.append(f"  Max:  `{latency.get('max', 'N/A')}`")
    
    # Today's sample queries
    if today_events:
        lines.append("")
        lines.append(f"*Today's Sample Queries* (last {min(5, len(today_events))}):")
        for ev in today_events[-5:]:
            ts = datetime.fromtimestamp(ev.get("timestamp", 0)).strftime("%H:%M")
            query_preview = ev.get("query", "")[:40]
            if len(ev.get("query", "")) > 40:
                query_preview += "..."
            route = ev.get("route", {})
            lines.append(f"  `{ts}` [{route.get('datasource', '?')}] {query_preview}")
    
    lines.append("")
    lines.append("_Report generated by hermes-adaptive-router_")
    
    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    try:
        events = load_history_from_file()
        report = format_report(events)
        print(report)
        return 0
    except Exception as exc:
        print(f"Error generating report: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
