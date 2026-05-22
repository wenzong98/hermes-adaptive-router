# Setup Guide

## 1. Configure config.yaml

Add to `~/.hermes/config.yaml` under the `web:` section:

```yaml
web:
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
    tavily_answer: advanced
```

Optional configuration:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `true` | Master switch |
| `prefer_search_summary` | bool | `true` | Prefer Tavily AI summary |
| `tavily_answer` | str/bool | `"advanced"` | Tavily answer level: `basic`/`advanced`/false |
| `simple_max_words` | int | `14` | Max words for simple queries |
| `complex_min_signals` | int | `2` | Min signals for complex queries |
| `force_web_keywords` | list | built-in | Keywords forcing web_search |
| `complex_keywords` | list | built-in | Keywords increasing complexity |
| `direct_keywords` | list | built-in | Keywords for direct answer |

## 2. Set PYTHONPATH

Hermes agent needs to import `hermes-adaptive-router` at runtime.

**Option A: Environment variable (development)**

```bash
export PYTHONPATH="$HOME/.hermes/hermes-adaptive-router/src:$PYTHONPATH"
hermes chat
```

**Option B: Shell config (permanent)**

```bash
echo 'export PYTHONPATH="$HOME/.hermes/hermes-adaptive-router/src:$PYTHONPATH"' >> ~/.zshrc
```

**Option C: pip install (recommended for production)**

```bash
cd ~/.hermes/hermes-adaptive-router
pip install -e .
```

## 3. Verify Installation

```bash
cd ~/.hermes/hermes-adaptive-router
make test
```

Or test within Hermes:

```bash
cd ~/.hermes/hermes-agent
python -m pytest tests/agent/test_adaptive_query_router.py tests/tools/test_web_tools_tavily.py -q
```

## 4. Disable

```yaml
web:
  adaptive_query_routing:
    enabled: false
```

Or remove the `adaptive_query_routing` section entirely — the shim gracefully falls back to direct answer mode.
