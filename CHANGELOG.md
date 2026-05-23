# Changelog

## 0.3.0 (2026-05-23)

### Bug Fixes
- **URL detection with balanced parentheses**: `_has_url` now strips unmatched
  closing parentheses and trailing punctuation (``.,;:!?`\"'\]\}>``) so that
  URLs embedded in prose or markdown are matched correctly. Previously
  ``https://example.com/wiki/Python_(programming_language)`` would be truncated
  at the first ``)``.
- **Tool name normalization**: `_normalize_tools` now strips whitespace from
  tool names. Previously ``["  web_search  "]`` was kept with spaces.
- **Empty string tavily_answer**: ``tavily_answer: ""`` in config now correctly
  becomes ``False`` instead of falling back to the default ``"advanced"``.
- **Direct query provider selection**: `route_with_provider` now returns
  ``provider="auto"`` for direct/empty/disabled queries instead of picking a
  provider unnecessarily.

### Tests
- Added comprehensive edge-case test suite (`tests/test_edge_cases.py`) with
  125 tests covering:
  - Internal helpers: `_as_bool`, `_as_int`, `_as_tuple`, `_contains_any`,
    `_word_count`, `_has_url`, `_normalize_tools`
  - Config loading: invalid shapes, empty strings, None values
  - Query classification: whitespace-only, very long, multi-URL, emoji,
    Japanese, Korean, numbers-only, special chars
  - Provider classification: disabled routing, empty query, single provider
  - Integration helpers: Tavily payload override, system prompt generation
  - Observability: history limits, stats aggregation, callbacks, JSONL persistence
- Total test count: 173 (was 48).

## 0.2.0 (2026-05-23)

### Bug Fixes
- **CJK word counting**: ``_word_count`` now correctly counts each CJK character
  individually. Previously ``[\\w\\u4e00-\\u9fff]+`` treated a run of CJK
  characters as a single match (because ``\\w`` inside ``[]`` only covers ASCII
  alphanumerics), causing pure-Chinese queries like "分析比特币为什么最近一直跌"
  to be mis-classified as ``simple`` instead of triggering web search.
- **'最近' keyword**: Added to ``_DEFAULT_FORCE_WEB_KEYWORDS`` alongside '最新'.
  Queries containing '最近' (recently) now correctly route to ``web_search``.
- **Empty provider set**: ``classify_provider`` with ``available_providers=set()``
  now returns ``"auto"`` instead of incorrectly falling back to ``"tavily"``.
  The previous ``set() or DEFAULT`` idiom was a Python falsy-bug.

### Tests
- Added 5 regression tests covering all three bug fixes plus edge cases
  (empty query, disabled routing, single-provider availability).
- Updated 2 benchmark cases whose expected complexity changed after the CJK
  word-count fix (they now correctly reflect ``complex`` for long Chinese
  reasoning queries with no web signal).
- Total test count: 48 (was 42).

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
