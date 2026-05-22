"""Hermes Adaptive Query Router — deterministic query classification."""

from hermes_adaptive_router.integrations import (
    classify_for_hermes,
    get_system_prompt_addition,
    tavily_search_payload_override,
)
from hermes_adaptive_router.observability import (
    RoutingEvent,
    clear_routing_history,
    get_routing_history,
    get_routing_stats,
    record_routing_event,
    set_post_route_callback,
)
from hermes_adaptive_router.router import (
    AdaptiveQueryRoutingConfig,
    QueryRoute,
    build_adaptive_query_routing_prompt,
    classify_query,
    load_adaptive_query_routing_config,
)

__all__ = [
    "AdaptiveQueryRoutingConfig",
    "QueryRoute",
    "build_adaptive_query_routing_prompt",
    "classify_for_hermes",
    "classify_query",
    "clear_routing_history",
    "get_routing_history",
    "get_routing_stats",
    "get_system_prompt_addition",
    "load_adaptive_query_routing_config",
    "record_routing_event",
    "set_post_route_callback",
    "tavily_search_payload_override",
]
