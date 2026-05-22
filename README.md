# hermes-adaptive-router

Deterministic adaptive query routing for [Hermes Agent](https://github.com/wenzong98/hermes-agent) and other LLM applications.

[![CI](https://github.com/wenzong98/hermes-adaptive-router/actions/workflows/ci.yml/badge.svg)](https://github.com/wenzong98/hermes-adaptive-router/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What

A lightweight, **no-LLM** query classifier that decides whether a user query should be:

- **Answered directly** — stable evergreen facts, definitions, straightforward reasoning
- **Routed to web_search** — current events, pricing, news, recent releases
- **Routed to web_extract** — user-provided URLs, PDFs, or when search summaries are insufficient

**Key features:**

- ⚡ **Sub-millisecond latency** — regex + keyword matching, zero API calls
- 🎯 **Deterministic** — same input always produces same output
- 🧪 **Fully tested** — 42 tests with benchmark regression suite
- 🔧 **Configurable** — YAML-driven policy, no code changes needed
- 🔌 **Multi-provider** — Tavily (default), MMX (Chinese), Exa (academic)
- 📊 **Observable** — built-in routing history and statistics

## Install

```bash
pip install hermes-adaptive-router
```

Or editable for development:

```bash
git clone https://github.com/wenzong98/hermes-adaptive-router.git
cd hermes-adaptive-router
pip install -e .
```

## Quick Start

```python
from hermes_adaptive_router import classify_query, build_adaptive_query_routing_prompt

# Classify a query
route = classify_query("latest OpenAI pricing today")
print(route.datasource)   # "web_search"
print(route.complexity)   # "intermediate"
print(route.confidence)   # 0.92

# Generate system prompt guidance
prompt = build_adaptive_query_routing_prompt({"web_search", "web_extract"})
```

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](docs/QUICK_START.md) | Installation, basic usage, Hermes integration |
| [API Reference](docs/API_REFERENCE.md) | Complete function documentation with examples |
| [DESIGN.md](DESIGN.md) | Architecture, decision flow, extensibility guide |
| [SETUP.md](SETUP.md) | Detailed configuration options (Chinese) |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## Config (config.yaml)

```yaml
web:
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
    tavily_answer: advanced
```

Or top-level:

```yaml
adaptive_query_routing:
  enabled: true
  prefer_search_summary: true
  tavily_answer: advanced
```

## Test

```bash
pytest tests/ -q
```

Expected: `42 passed`

## Why Deterministic?

| Approach | Latency | Cost | Testability | Drift |
|----------|---------|------|-------------|-------|
| **Our router** (regex) | ~0.05ms | $0 | ✅ Exact | None |
| LLM classification | ~500ms | $0.001-0.01 | ❌ Probabilistic | Temperature, model version |
| ML classifier | ~1ms | Training cost | ⚠️ Dataset dependent | Concept drift |

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

## Multi-Provider Support

| Provider | Strength | Use Case |
|----------|----------|----------|
| **Tavily** | AI summaries, fast | General web search (default) |
| **MMX** | Chinese content | Chinese queries, MiniMax ecosystem |
| **Exa** | Semantic search | Academic papers, research |

```python
from hermes_adaptive_router import classify_provider

classify_provider("最新中文AI模型")          # → mmx
classify_provider("neural embedding paper")  # → exa
classify_provider("latest Bitcoin price")    # → tavily
```

## Hermes Agent Integration

This package is designed to integrate seamlessly with Hermes Agent:

1. **System prompt injection** — teaches LLM when to search vs. answer directly
2. **Tavily payload override** — auto-adds `include_answer` and `search_depth`
3. **Observability** — records routing decisions for analytics

See [Quick Start](docs/QUICK_START.md#hermes-agent-integration) for setup instructions.

## License

MIT — see [LICENSE](LICENSE)
