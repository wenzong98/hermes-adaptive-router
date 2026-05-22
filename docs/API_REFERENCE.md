# API Reference

## Core Router

### `classify_query(query: str, config: AdaptiveQueryRoutingConfig | None = None) -> QueryRoute`

Classify a user query into a routing decision.

**Parameters:**
- `query` (str): The user query text
- `config` (AdaptiveQueryRoutingConfig, optional): Routing configuration. Uses defaults if not provided.

**Returns:**
- `QueryRoute`: A dataclass with fields:
  - `datasource` (str): One of `"direct"`, `"web_search"`, `"web_extract"`
  - `complexity` (str): One of `"simple"`, `"intermediate"`, `"complex"`
  - `confidence` (float): Confidence score 0.0-1.0
  - `retrieval_strategy` (str): One of `"none"`, `"single"`, `"iterative"`

**Example:**
```python
from hermes_adaptive_router import classify_query

route = classify_query("latest Bitcoin price today")
print(route.datasource)      # "web_search"
print(route.complexity)      # "intermediate"
print(route.confidence)      # 0.92
print(route.retrieval_strategy)  # "single"
```

---

### `class AdaptiveQueryRoutingConfig`

Configuration dataclass for the router.

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `True` | Master switch |
| `prefer_search_summary` | bool | `True` | Prefer Tavily AI summary over raw results |
| `tavily_answer` | str \| bool | `"advanced"` | Tavily answer level: `"basic"`, `"advanced"`, or `False` |
| `simple_max_words` | int | `14` | Max word count for simple queries |
| `complex_min_signals` | int | `2` | Minimum signals to mark complex |
| `force_web_keywords` | tuple | built-in | Keywords forcing web_search |
| `complex_keywords` | tuple | built-in | Keywords increasing complexity |
| `direct_keywords` | tuple | built-in | Keywords short-circuiting to direct |

**Example:**
```python
from hermes_adaptive_router import AdaptiveQueryRoutingConfig

config = AdaptiveQueryRoutingConfig(
    enabled=True,
    prefer_search_summary=True,
    tavily_answer="advanced",
    simple_max_words=10,
    complex_min_signals=3,
)
```

---

### `load_adaptive_query_routing_config(config_dict: dict | None) -> AdaptiveQueryRoutingConfig`

Load configuration from a dictionary (typically from YAML).

Supports two shapes:
```yaml
# Top-level
adaptive_query_routing:
  enabled: true
  prefer_search_summary: true

# Nested under web
web:
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
```

**Example:**
```python
import yaml
from hermes_adaptive_router import load_adaptive_query_routing_config

with open("config.yaml") as f:
    config = yaml.safe_load(f)

routing_config = load_adaptive_query_routing_config(config)
```

---

## Multi-Provider Routing

### `classify_provider(query: str, config: AdaptiveQueryRoutingConfig | None = None) -> ProviderPreference`

Classify which search provider is best suited for a query.

**Returns:**
- `ProviderPreference` with fields:
  - `provider` (str): `"tavily"`, `"mmx"`, or `"exa"`
  - `reason` (str): Human-readable reason
  - `confidence` (float): 0.0-1.0

**Example:**
```python
from hermes_adaptive_router import classify_provider

pref = classify_provider("最新中文AI模型")
print(pref.provider)    # "mmx"
print(pref.reason)      # "Chinese query detected"

pref = classify_provider("research paper on neural embeddings")
print(pref.provider)    # "exa"
print(pref.reason)      # "Academic/research query detected"
```

---

### `route_with_provider(query: str, config: AdaptiveQueryRoutingConfig | None = None) -> tuple[QueryRoute, ProviderPreference]`

Combined routing: classify both datasource and provider.

**Returns:**
- Tuple of `(QueryRoute, ProviderPreference)`

**Example:**
```python
from hermes_adaptive_router import route_with_provider

route, provider = route_with_provider("latest OpenAI pricing today")
print(route.datasource)      # "web_search"
print(provider.provider)     # "tavily"
```

---

## System Prompt Integration

### `build_adaptive_query_routing_prompt(available_tools: set[str]) -> str`

Generate the system prompt paragraph that teaches the LLM about routing.

**Parameters:**
- `available_tools` (set[str]): Available tool names (e.g., `{"web_search", "web_extract"}`)

**Returns:**
- `str`: Formatted prompt paragraph

**Example:**
```python
from hermes_adaptive_router import build_adaptive_query_routing_prompt

prompt = build_adaptive_query_routing_prompt({"web_search", "web_extract"})
# Inject into system prompt
```

---

### `get_system_prompt_addition(available_tools: set[str]) -> str`

Alias for `build_adaptive_query_routing_prompt()`. Hermes integration helper.

---

## Tavily Integration

### `tavily_search_payload_override(payload: dict, config: AdaptiveQueryRoutingConfig) -> dict`

Mutate a Tavily search payload to include adaptive routing parameters.

**Modifications:**
- Adds `include_answer: "advanced"` when `prefer_search_summary` is True
- Adds `search_depth: "advanced"` for richer synthesis

**Example:**
```python
from hermes_adaptive_router import tavily_search_payload_override, AdaptiveQueryRoutingConfig

config = AdaptiveQueryRoutingConfig()
payload = {"query": "latest AI news"}
modified = tavily_search_payload_override(payload, config)
# {"query": "latest AI news", "include_answer": "advanced", "search_depth": "advanced"}
```

---

## Observability

### `record_routing_event(event: RoutingEvent) -> None`

Record a routing decision for analytics.

**Example:**
```python
from hermes_adaptive_router import record_routing_event, RoutingEvent

record_routing_event(RoutingEvent(
    query="latest Bitcoin price",
    datasource="web_search",
    complexity="intermediate",
    confidence=0.92,
    latency_ms=0.05,
))
```

---

### `get_routing_stats() -> dict`

Get aggregate statistics about routing decisions.

**Returns:**
```python
{
    "total": 100,
    "datasource_distribution": {"direct": 42, "web_search": 45, "web_extract": 13},
    "complexity_distribution": {"simple": 50, "intermediate": 35, "complex": 15},
    "avg_latency_ms": 0.05,
}
```

---

### `get_routing_history() -> list[RoutingEvent]`

Get the full routing history (last 1000 events).

---

### `clear_routing_history() -> None`

Clear all recorded routing events.

---

### `set_post_route_callback(callback: Callable[[RoutingEvent], None]) -> None`

Set a callback invoked after each routing decision.

**Example:**
```python
from hermes_adaptive_router import set_post_route_callback

def log_to_datadog(event):
    # Send to external monitoring
    pass

set_post_route_callback(log_to_datadog)
```

---

## Hermes Integration Helpers

### `classify_for_hermes(query: str, available_tools: set[str], config: AdaptiveQueryRoutingConfig | None = None) -> QueryRoute`

Drop-in replacement for Hermes' internal classify function.

Automatically checks if web tools are available and adjusts routing accordingly.

---

## Complete Example

```python
from hermes_adaptive_router import (
    classify_query,
    classify_provider,
    route_with_provider,
    AdaptiveQueryRoutingConfig,
    build_adaptive_query_routing_prompt,
    tavily_search_payload_override,
    record_routing_event,
    get_routing_stats,
)

# 1. Configure
config = AdaptiveQueryRoutingConfig(
    enabled=True,
    prefer_search_summary=True,
    tavily_answer="advanced",
)

# 2. Classify a query
query = "latest OpenAI pricing today"
route = classify_query(query, config)
print(f"Route: {route.datasource} (confidence: {route.confidence})")

# 3. Pick provider
provider = classify_provider(query, config)
print(f"Provider: {provider.provider} ({provider.reason})")

# 4. Combined routing
route, provider = route_with_provider(query, config)

# 5. Generate system prompt
prompt = build_adaptive_query_routing_prompt({"web_search", "web_extract"})

# 6. Modify Tavily payload
payload = {"query": query}
modified = tavily_search_payload_override(payload, config)

# 7. Record for observability
record_routing_event(RoutingEvent(
    query=query,
    datasource=route.datasource,
    complexity=route.complexity,
    confidence=route.confidence,
    latency_ms=0.05,
))

# 8. Check stats
stats = get_routing_stats()
print(f"Total routed: {stats['total']}")
```
