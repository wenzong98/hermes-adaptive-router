"""Tests for observability module."""

from hermes_adaptive_router.observability import (
    RoutingEvent,
    clear_routing_history,
    get_routing_history,
    get_routing_stats,
    record_routing_event,
    set_post_route_callback,
)
from hermes_adaptive_router.router import QueryRoute


def test_record_and_retrieve_events():
    clear_routing_history()
    event = RoutingEvent(
        query="test",
        route=QueryRoute("direct", "simple", "none", 0.9, "test"),
        latency_ms=1.5,
    )
    record_routing_event(event)
    history = get_routing_history()
    assert len(history) == 1
    assert history[0].query == "test"


def test_stats_aggregation():
    clear_routing_history()
    record_routing_event(RoutingEvent("q1", QueryRoute("direct", "simple", "none", 0.9, "r1"), latency_ms=1.0))
    record_routing_event(RoutingEvent("q2", QueryRoute("web_search", "intermediate", "single_retrieval", 0.8, "r2"), latency_ms=2.0))
    stats = get_routing_stats()
    assert stats["total"] == 2
    assert stats["datasource_distribution"]["direct"] == 1
    assert stats["datasource_distribution"]["web_search"] == 1
    assert stats["latency_ms"]["mean"] == 1.5


def test_callback_is_invoked():
    clear_routing_history()
    called = []
    def cb(ev):
        called.append(ev.query)
    set_post_route_callback(cb)
    record_routing_event(RoutingEvent("q3", QueryRoute("direct", "simple", "none", 0.9, "r3")))
    assert called == ["q3"]
    set_post_route_callback(None)
