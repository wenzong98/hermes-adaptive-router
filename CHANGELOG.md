# Changelog

## 0.4.0 (2026-05-24)

### Features (P1 — 高价值，低复杂度)

#### 1. 更多 Provider 支持
- **Provider Registry** (`providers.py`): 统一注册表管理 8 个搜索 Provider
  - Tavily, MMX, Exa (原有)
  - Google (SerpAPI), Bing (Azure), DuckDuckGo (免 API key)
  - Brave (隐私搜索), Perplexity (AI 原生搜索)
- 每个 Provider 包含元数据：是否需要 API key、是否支持 extract、是否支持 answer summary
- `classify_provider_extended()`: 基于关键词信号的扩展 Provider 选择器
- `filter_providers_by_capability()`: 按能力筛选 Provider

#### 2. 查询意图增强
- **Intent Signals** (`intent_signals.py`): 5 大意图类别检测
  - `code`: GitHub, StackOverflow, 编程关键词 (中英双语)
  - `image`: 图片、照片、截图、设计
  - `video`: YouTube, 教程、直播、B站
  - `docs`: 文档、API reference、手册
  - `shopping`: 购买、价格、淘宝、Amazon
- `detect_intent()`: 返回主意图 + 置信度 + 匹配关键词
- `recommend_providers_by_intent()`: 按意图推荐 Provider (code → Google, image → Bing)

#### 3. 语言检测自动路由
- **Language Detection** (`language_detection.py`): 零依赖，16 种语言支持
  - 检测方法：Unicode script 范围 + 关键词频率分析
  - 支持：en, zh, ja, ko, de, fr, es, ru, ar, pt, it, nl, tr, vi, th, hi
- `detect_language()`: 返回语言代码 + 置信度 + script 家族
- `recommend_providers_by_language()`: 中文 → MMX, 英文 → Tavily/Exa
- `route_with_provider()` 集成：高置信度中文自动 override 到 MMX

#### 4. LRU 路由决策缓存
- **Routing Cache** (`cache.py`): 线程安全 LRU 缓存
  - 可配置 max_size (默认 1000) 和 TTL (默认 1 小时)
  - 查询 key 归一化：小写 + 空格折叠
  - Cache hit/miss 统计 + hit rate 计算
- `cached_classify()`: 装饰器包装任意 classify 函数
- `get_default_cache() / set_default_cache()`: 全局默认缓存实例

#### 5. A/B 测试框架
- **AB Testing** (`ab_testing.py`): 策略对比框架
  - `ABTestRunner`: 注册多个策略，并行跑 golden dataset
  - 指标：datasource/complexity/strategy 准确率 + overall accuracy + 延迟
  - `generate_report()`: 人类可读对比报告
  - `export_results()`: JSON 导出详细结果
- `create_golden_dataset()`: 从 Python list 创建标准 golden dataset

### API 扩展
- `__init__.py` 导出全部新模块（40+ 公共符号）
- `route_with_provider()` 新增参数：
  - `use_extended_providers=True`: 启用 8 Provider 注册表
  - `use_language_detection=True`: 启用语言检测
- 返回值新增字段：`language`, `language_confidence`, `intent`

### Tests
- 新增 `tests/test_p1_features.py`: 81 个测试覆盖全部 P1 功能
  - Provider Registry: 11 tests
  - Extended Classification: 10 tests
  - Intent Detection: 14 tests
  - Language Detection: 14 tests
  - Cache: 13 tests
  - A/B Testing: 11 tests
  - Integration: 8 tests
- **全量测试: 254 passed** (原 173 → 254)

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
