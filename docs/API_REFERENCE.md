# API Reference

## Core Router

### `classify_query(query: str, config: AdaptiveQueryRoutingConfig | None = None, *, available_tools: Iterable[str] | None = None) -> QueryRoute`

Classify a user query into a deterministic routing decision.

**Returns**
- `QueryRoute.datasource`: `"direct"`, `"web_search"`, or `"web_extract"`
- `QueryRoute.complexity`: `"simple"`, `"intermediate"`, or `"complex"`
- `QueryRoute.retrieval_strategy`: `"none"`, `"single_retrieval"`, or `"iterative_retrieval"`
- `QueryRoute.confidence`: `0.0` to `1.0`
- `QueryRoute.reason`: short explanation for the decision

```python
from hermes_adaptive_router import classify_query

route = classify_query(
    "latest Bitcoin price today",
    available_tools={"web_search", "web_extract"},
)
print(route.datasource)          # "web_search"
print(route.retrieval_strategy)  # "single_retrieval"
```

### `class AdaptiveQueryRoutingConfig`

Configuration dataclass for the deterministic router.

| Field | Type | Default |
|---|---|---|
| `enabled` | `bool` | `True` |
| `simple_max_words` | `int` | `14` |
| `prefer_search_summary` | `bool` | `True` |
| `tavily_answer` | `str | bool | None` | `"advanced"` |
| `force_web_keywords` | `tuple[str, ...]` | built-in defaults |
| `complex_keywords` | `tuple[str, ...]` | built-in defaults |
| `direct_keywords` | `tuple[str, ...]` | built-in defaults |
| `complex_min_signals` | `int` | `2` |

### `load_adaptive_query_routing_config(raw_config: Mapping[str, Any] | None) -> AdaptiveQueryRoutingConfig`

Parse routing config from a plain mapping. Passing `None` returns built-in defaults.

Supported shapes:

```yaml
adaptive_query_routing:
  enabled: true

web:
  adaptive_query_routing:
    enabled: true
    tavily_answer: advanced
```

## Provider Routing

### `classify_provider(query: str, config: AdaptiveQueryRoutingConfig | None = None, *, available_providers: Iterable[str] | None = None) -> ProviderPreference`

Pick the preferred provider for a query using the provider registry.

```python
from hermes_adaptive_router import classify_provider

pref = classify_provider(
    "research paper on neural embeddings",
    available_providers={"tavily", "mmx", "exa"},
)
print(pref.provider)  # "exa"
```

### `route_with_provider(...) -> dict[str, Any]`

Combined routing for datasource, retrieval strategy, provider, language, and intent.

Returned keys:
- `datasource`
- `complexity`
- `retrieval_strategy`
- `confidence`
- `reason`
- `provider`
- `provider_reason`
- `provider_confidence`
- `language`
- `language_confidence`
- `intent`
- `intent_confidence`

```python
from hermes_adaptive_router import route_with_provider

result = route_with_provider(
    "search github python code example",
    available_tools={"web_search"},
    available_providers={"tavily", "google", "bing"},
)
print(result["datasource"])  # "web_search"
print(result["provider"])    # "google"
print(result["intent"])      # "code"
```

## Hermes Helpers

### `build_adaptive_query_routing_prompt(available_tools: Iterable[str], config: AdaptiveQueryRoutingConfig | None = None) -> str`

Return the prompt fragment that teaches the LLM when to stay direct, use `web_search`, or escalate to `web_extract`.

### `classify_for_hermes(query: str, *, available_tools: Iterable[str] | None = None, raw_config: Mapping[str, Any] | None = None) -> QueryRoute`

Hermes adapter that loads host config in the integration layer and then calls the core router.

### `get_system_prompt_addition(available_tools: Iterable[str], *, raw_config: Mapping[str, Any] | None = None) -> str`

Hermes-friendly wrapper around `build_adaptive_query_routing_prompt`.

### `tavily_search_payload_override(payload: dict[str, Any], *, raw_config: Mapping[str, Any] | None = None) -> dict[str, Any]`

Mutate a Tavily payload when summary answers are enabled.

```python
from hermes_adaptive_router import tavily_search_payload_override

payload = {"query": "latest AI news"}
modified = tavily_search_payload_override(
    payload,
    raw_config={"adaptive_query_routing": {"tavily_answer": "advanced"}},
)
print(modified["include_answer"])  # "advanced"
print(modified["search_depth"])    # "advanced"
```

## Observability

### `record_routing_event(event: RoutingEvent) -> None`

Record a routing decision.

```python
from hermes_adaptive_router import QueryRoute, RoutingEvent, record_routing_event

record_routing_event(
    RoutingEvent(
        query="latest Bitcoin price",
        route=QueryRoute("web_search", "intermediate", "single_retrieval", 0.92, "recency signal"),
        latency_ms=0.05,
    )
)
```

### `get_routing_stats() -> dict[str, Any]`

Returns aggregates like:

```python
{
    "total": 100,
    "datasource_distribution": {"direct": 42, "web_search": 45, "web_extract": 13},
    "complexity_distribution": {"simple": 50, "intermediate": 35, "complex": 15},
    "strategy_distribution": {"none": 42, "single_retrieval": 38, "iterative_retrieval": 20},
    "latency_ms": {"mean": 0.05, "min": 0.01, "max": 0.3},
}
```

### `get_routing_history(limit: int = 100) -> list[RoutingEvent]`

Return recent events, newest first.

### `clear_routing_history() -> None`

Clear in-memory history.

### `set_post_route_callback(callback: Callable[[RoutingEvent], None] | None) -> None`

Register a callback invoked after each recorded event.
