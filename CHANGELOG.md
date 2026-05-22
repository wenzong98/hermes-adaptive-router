# Changelog

## 0.1.0 (2025-05-22)

### Features
- Deterministic query classifier (`classify_query`) — no LLM, regex + keyword based
- Config-driven routing policy (`AdaptiveQueryRoutingConfig`)
- Support for top-level and `web.*` nested config shapes
- Tavily summary-first integration (`tavily_answer`, `prefer_search_summary`)
- System prompt builder (`build_adaptive_query_routing_prompt`)
- Hermes integration layer (`classify_for_hermes`, `get_system_prompt_addition`, `tavily_search_payload_override`)
- Observability: in-memory routing history, stats aggregation, optional callbacks

### Tests
- 34 tests covering router, integrations, observability, benchmark regression
- Benchmark suite with 18 curated queries documenting expected routing
