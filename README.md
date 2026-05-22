# hermes-adaptive-router

Deterministic adaptive query routing for Hermes Agent.

## What

A lightweight, **no-LLM** query classifier that decides whether a user query should be:
- answered **directly** (stable evergreen knowledge)
- routed to **web_search** (recency-sensitive or web-oriented)
- routed to **web_extract** (URL-specific or when summaries are insufficient)

## Install

Copy `src/hermes_adaptive_router/` into your Hermes `agent/` directory, or install as an editable package:

```bash
pip install -e .
```

## Quick Start

```python
from hermes_adaptive_router import classify_query, build_adaptive_query_routing_prompt

route = classify_query("latest OpenAI pricing today")
print(route.datasource)   # "web_search"
print(route.complexity)   # "intermediate"

prompt = build_adaptive_query_routing_prompt({"web_search", "web_extract"})
print(prompt)  # inject into system prompt
```

## Config (config.yaml)

```yaml
adaptive_query_routing:
  enabled: true
  prefer_search_summary: true
  tavily_answer: advanced
```

Or nested under `web:`:

```yaml
web:
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
    tavily_answer: advanced
```

## Test

```bash
pytest tests/ -q
```
