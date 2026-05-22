# hermes-adaptive-router Design

## Philosophy

**Deterministic over probabilistic.** The router uses regex + keyword matching
instead of LLM calls. This makes it:
- **Cheap**: zero API cost per classification
- **Fast**: sub-millisecond latency
- **Testable**: exact inputs produce exact outputs
- **Predictable**: no temperature or model-version drift

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Query    │────▶│  classify_query  │────▶│   QueryRoute    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ AdaptiveQueryRouting │
                    │       Config         │
                    └──────────────────────┘
```

## Decision Flow

```
query ──▶ empty? ──yes──▶ direct/simple/none
           │
           no
           ▼
    enabled? ──no──▶ direct/simple/none
           │
           yes
           ▼
    has URL? ──yes──▶ web_extract (or web_search fallback)
           │
           no
           ▼
    web signal? ──yes──▶ web_search (complex? iterative : single)
           │
           no
           ▼
    complex signals >= threshold? ──yes──▶ direct/complex/none
           │
           no
           ▼
    short or direct keyword? ──yes──▶ direct/simple/none
           │
           no
           ▼
    direct/intermediate/none
```

## Signal Types

| Signal | Examples | Effect |
|--------|----------|--------|
| **Force web** | "latest", "today", "price", "新闻" | Routes to `web_search` |
| **Complex** | "compare", "analyze", "如何" | Increases complexity tier |
| **Direct** | "who", "what", "是什么" | Short-circuits to `direct` |
| **URL** | `https://...` | Routes to `web_extract` |

## Configuration

Two shapes supported in `config.yaml`:

```yaml
# Top-level (future-proof for non-web routing)
adaptive_query_routing:
  enabled: true
  prefer_search_summary: true
  tavily_answer: advanced

# Nested under web (recommended)
web:
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
    tavily_answer: advanced
```

## Integration with Hermes

### 1. System Prompt

`build_adaptive_query_routing_prompt()` generates a paragraph injected into
the system prompt when web tools are available. It teaches the LLM:
- Don't search for simple facts
- Use search summaries before extracting URLs
- Respect Tavily's `data.answer` when available

### 2. Tavily Provider

`tavily_search_payload_override()` mutates the search payload:
- Adds `include_answer: advanced` when `prefer_search_summary` is on
- Adds `search_depth: advanced` for richer synthesis

### 3. Observability

`RoutingEvent` records every decision:
- Query text
- Route result
- Latency
- Session/user IDs

`get_routing_stats()` aggregates:
- Datasource distribution
- Complexity distribution
- Latency percentiles

## Extensibility

### Adding a New Signal

1. Add keyword to `_DEFAULT_*_KEYWORDS` in `router.py`
2. Add test case to `tests/test_benchmark.py`
3. Run `make test` to verify no regressions

### Adding a New Datasource

1. Extend `Datasource` type alias
2. Add branch in `classify_query()`
3. Update `build_adaptive_query_routing_prompt()`
4. Add benchmark case

## Performance

- **Latency**: ~0.05ms per classification (measured on M3 Mac)
- **Memory**: zero allocations after module load
- **Throughput**: >100k classifications/second

## Future Work

- [ ] Weighted keyword scoring (instead of binary presence)
- [ ] Multi-language expansion (Japanese, Korean, etc.)
- [ ] Optional LLM fallback for confidence < 0.7
- [ ] Persistent stats storage (SQLite / Redis)
- [ ] A/B testing framework for config variants
