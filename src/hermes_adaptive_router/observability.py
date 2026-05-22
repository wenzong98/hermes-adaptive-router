"""Lightweight observability for routing decisions.

No external dependencies.  Events are plain dicts; consumers can log them,
forward to OpenTelemetry, or accumulate in memory for A/B analysis.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from hermes_adaptive_router.router import QueryRoute


@dataclass
class RoutingEvent:
    """A single routing decision with metadata."""

    query: str
    route: QueryRoute
    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Global in-memory sink for quick introspection (not for production at scale).
# Each entry is a RoutingEvent.
_ROUTING_HISTORY: list[RoutingEvent] = []
_MAX_HISTORY = 10_000

# Optional callback: fn(event) -> None, called synchronously after each route.
_post_route_callback: Optional[Callable[[RoutingEvent], None]] = None


def set_post_route_callback(fn: Optional[Callable[[RoutingEvent], None]]) -> None:
    """Register a callback invoked after every routing decision."""
    global _post_route_callback
    _post_route_callback = fn


def record_routing_event(event: RoutingEvent) -> None:
    """Store event in memory and invoke optional callback."""
    _ROUTING_HISTORY.append(event)
    if len(_ROUTING_HISTORY) > _MAX_HISTORY:
        _ROUTING_HISTORY.pop(0)
    if _post_route_callback is not None:
        try:
            _post_route_callback(event)
        except Exception:
            pass


def get_routing_history(limit: int = 100) -> list[RoutingEvent]:
    """Return recent routing events (newest first)."""
    return list(reversed(_ROUTING_HISTORY[-limit:]))


def get_routing_stats() -> dict[str, Any]:
    """Aggregate statistics over all recorded events."""
    total = len(_ROUTING_HISTORY)
    if total == 0:
        return {"total": 0}

    counts: dict[str, int] = {}
    complexity_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    latencies: list[float] = []

    for ev in _ROUTING_HISTORY:
        counts[ev.route.datasource] = counts.get(ev.route.datasource, 0) + 1
        complexity_counts[ev.route.complexity] = complexity_counts.get(ev.route.complexity, 0) + 1
        strategy_counts[ev.route.retrieval_strategy] = strategy_counts.get(ev.route.retrieval_strategy, 0) + 1
        latencies.append(ev.latency_ms)

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


def clear_routing_history() -> None:
    """Drop all in-memory history."""
    _ROUTING_HISTORY.clear()


__all__ = [
    "RoutingEvent",
    "clear_routing_history",
    "get_routing_history",
    "get_routing_stats",
    "record_routing_event",
    "set_post_route_callback",
]
