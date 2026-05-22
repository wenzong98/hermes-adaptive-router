# Quick Start Guide

## Installation

### Option 1: pip install (recommended for users)

```bash
pip install hermes-adaptive-router
```

### Option 2: Editable install (recommended for developers)

```bash
git clone https://github.com/wenzong98/hermes-adaptive-router.git
cd hermes-adaptive-router
pip install -e .
```

### Option 3: Copy source (minimal dependencies)

```bash
cp -r src/hermes_adaptive_router /path/to/your/project/
```

---

## Basic Usage

### 1. Classify a Query

```python
from hermes_adaptive_router import classify_query

# Simple fact → direct answer
route = classify_query("What is Python?")
print(route.datasource)   # "direct"
print(route.complexity)   # "simple"

# Current news → web search
route = classify_query("latest AI news today")
print(route.datasource)   # "web_search"
print(route.complexity)   # "intermediate"

# URL provided → extract
route = classify_query("Summarize https://example.com/article")
print(route.datasource)   # "web_extract"
```

### 2. Multi-Provider Routing

```python
from hermes_adaptive_router import classify_provider

# Chinese query → MMX
pref = classify_provider("最新中文AI模型")
print(pref.provider)   # "mmx"

# Academic query → Exa
pref = classify_provider("research paper on neural embeddings")
print(pref.provider)   # "exa"

# General query → Tavily (default)
pref = classify_provider("latest Bitcoin price")
print(pref.provider)   # "tavily"
```

### 3. System Prompt Integration

```python
from hermes_adaptive_router import build_adaptive_query_routing_prompt

# Generate routing guidance for LLM
prompt = build_adaptive_query_routing_prompt({"web_search", "web_extract"})

# Inject into your system prompt
system_prompt = f"""You are a helpful assistant.

{prompt}

Answer the user's question."""
```

### 4. Tavily Integration

```python
from hermes_adaptive_router import tavily_search_payload_override, AdaptiveQueryRoutingConfig

config = AdaptiveQueryRoutingConfig()
payload = {"query": "latest AI news"}

# Auto-add include_answer and search_depth
modified = tavily_search_payload_override(payload, config)
print(modified)
# {"query": "latest AI news", "include_answer": "advanced", "search_depth": "advanced"}
```

---

## Configuration

### Config File (YAML)

```yaml
# ~/.hermes/config.yaml
web:
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
    tavily_answer: advanced
    simple_max_words: 14
    complex_min_signals: 2
```

### Environment Variables

```bash
# Exa API key (optional, for Exa provider)
export EXA_API_KEY=your-key-here
```

### Programmatic Configuration

```python
from hermes_adaptive_router import AdaptiveQueryRoutingConfig

config = AdaptiveQueryRoutingConfig(
    enabled=True,
    prefer_search_summary=True,
    tavily_answer="advanced",
    simple_max_words=10,
    complex_min_signals=3,
)

route = classify_query("your query", config)
```

---

## Hermes Agent Integration

### 1. Install the Package

```bash
cd ~/.hermes/hermes-adaptive-router
pip install -e .
```

### 2. Configure config.yaml

```yaml
# ~/.hermes/config.yaml
web:
  search_backend: tavily
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
    tavily_answer: advanced
```

### 3. Verify Installation

```bash
cd ~/.hermes/hermes-adaptive-router
make test
```

Expected output:
```
42 passed
```

### 4. Test in Hermes

Start a conversation and check that:
- Simple questions are answered directly (no web search)
- Current events trigger web_search
- URLs trigger web_extract

---

## Next Steps

- Read the [API Reference](API_REFERENCE.md) for complete function documentation
- Check [DESIGN.md](../DESIGN.md) for architecture details
- See [benchmark tests](../tests/test_benchmark.py) for expected routing decisions
- Review [SETUP.md](../SETUP.md) for detailed configuration options
