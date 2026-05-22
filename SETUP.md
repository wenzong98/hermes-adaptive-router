# Setup Guide

## 1. 配置 config.yaml

在 `~/.hermes/config.yaml` 的 `web:` 段下添加：

```yaml
web:
  adaptive_query_routing:
    enabled: true
    prefer_search_summary: true
    tavily_answer: advanced
```

可选配置项：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enabled` | bool | `true` | 总开关 |
| `prefer_search_summary` | bool | `true` | 优先使用 Tavily AI 摘要 |
| `tavily_answer` | string/bool | `"advanced"` | Tavily answer 级别：`basic`/`advanced`/false |
| `simple_max_words` | int | `14` | 简单查询的最大词数 |
| `complex_min_signals` | int | `2` | 判定复杂查询的最小信号数 |
| `force_web_keywords` | list | 内置 | 强制走 web_search 的关键词 |
| `complex_keywords` | list | 内置 | 增加复杂度评分的关键词 |
| `direct_keywords` | list | 内置 | 直接回答的关键词 |

## 2. 确保 PYTHONPATH

Hermes agent 启动时需要能导入 `hermes-adaptive-router`。

**方式 A：环境变量（推荐开发时）**

```bash
export PYTHONPATH="$HOME/.hermes/hermes-adaptive-router/src:$PYTHONPATH"
hermes chat
```

**方式 B：写入 shell 配置**

```bash
echo 'export PYTHONPATH="$HOME/.hermes/hermes-adaptive-router/src:$PYTHONPATH"' >> ~/.zshrc
```

**方式 C：pip 安装（推荐稳定使用）**

```bash
cd ~/.hermes/hermes-adaptive-router
pip install -e .
```

## 3. 验证安装

```bash
cd ~/.hermes/hermes-adaptive-router
make test
```

或直接在 Hermes 中验证：

```bash
cd ~/.hermes/hermes-agent
python -m pytest tests/agent/test_adaptive_query_router.py tests/tools/test_web_tools_tavily.py -q
```

## 4. 关闭功能

```yaml
web:
  adaptive_query_routing:
    enabled: false
```

或完全删除 `adaptive_query_routing` 段，shim 会优雅降级到直接回答模式。
