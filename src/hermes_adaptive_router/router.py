"""Deterministic adaptive query routing helpers for Hermes.

This module intentionally stays cheap: it does **not** call an LLM.  It gives
Hermes a configurable, testable policy for deciding whether a user query should
be answered directly, start with search-result summaries, or escalate to deeper
URL extraction.  The policy is used as system-prompt guidance and by web
providers that can cheaply return synthesized search answers (Tavily).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Mapping, Optional

Datasource = str
Complexity = str
RetrievalStrategy = str

_URL_RE = re.compile(r"https?://[^\s<>)\]\}\"']+", re.IGNORECASE)
_WORD_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)

_DEFAULT_FORCE_WEB_KEYWORDS = (
    # English recency / web intent
    "latest",
    "current",
    "today",
    "now",
    "recent",
    "news",
    "breaking",
    "price",
    "pricing",
    "release date",
    "changelog",
    "version",
    "search",
    "look up",
    "lookup",
    "web search",
    "online",
    # Chinese recency / web intent
    "最新",
    "最近",
    "今天",
    "现在",
    "近期",
    "新闻",
    "价格",
    "定价",
    "版本",
    "发布日期",
    "搜索",
    "查一下",
    "查下",
    "联网",
    "网上",
)

_DEFAULT_COMPLEX_KEYWORDS = (
    # Multi-hop / synthesis intent
    "compare",
    "comparison",
    "versus",
    " vs ",
    "tradeoff",
    "trade-off",
    "benchmarks",
    "benchmark",
    "evaluate",
    "analysis",
    "analyze",
    "why",
    "how",
    "explain",
    "strategy",
    "architecture",
    "root cause",
    "multi-step",
    # Chinese
    "比较",
    "对比",
    "权衡",
    "基准",
    "评测",
    "分析",
    "为什么",
    "怎么",
    "如何",
    "原理",
    "架构",
    "根因",
)

_DEFAULT_DIRECT_KEYWORDS = (
    "who",
    "what",
    "when",
    "where",
    "define",
    "meaning",
    "是谁",
    "是什么",
    "什么时候",
    "在哪里",
    "定义",
)


@dataclass(frozen=True)
class AdaptiveQueryRoutingConfig:
    """Config for the deterministic adaptive query router.

    Config can be provided either as top-level ``adaptive_query_routing`` or as
    ``web.adaptive_query_routing`` / ``web.adaptive_routing`` in config.yaml.
    """

    enabled: bool = True
    simple_max_words: int = 14
    prefer_search_summary: bool = True
    tavily_answer: str | bool = "advanced"
    force_web_keywords: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_FORCE_WEB_KEYWORDS)
    complex_keywords: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_COMPLEX_KEYWORDS)
    direct_keywords: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_DIRECT_KEYWORDS)
    complex_min_signals: int = 2


@dataclass(frozen=True)
class QueryRoute:
    """A query routing decision.

    ``datasource`` values intentionally match Hermes tool names where possible:
    ``direct``, ``web_search``, or ``web_extract``.
    """

    datasource: Datasource
    complexity: Complexity
    retrieval_strategy: RetrievalStrategy
    confidence: float
    reason: str


_DEF_CONFIG = AdaptiveQueryRoutingConfig()


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled", "enable"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled", "disable"}:
            return False
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 10_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def _as_tuple(value: Any, default: Iterable[str]) -> tuple[str, ...]:
    if value is None:
        return tuple(default)
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        items = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
        return tuple(items) if items else tuple(default)
    return tuple(default)


def _select_config_section(raw_config: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = raw_config.get("adaptive_query_routing")
    if isinstance(direct, Mapping):
        return direct

    web_cfg = raw_config.get("web")
    if isinstance(web_cfg, Mapping):
        nested = web_cfg.get("adaptive_query_routing") or web_cfg.get("adaptive_routing")
        if isinstance(nested, Mapping):
            return nested

    return {}


def load_adaptive_query_routing_config(
    raw_config: Optional[Mapping[str, Any]] = None,
) -> AdaptiveQueryRoutingConfig:
    """Load adaptive routing config from a mapping or Hermes config.yaml.

    Supported shapes::

        adaptive_query_routing:
          enabled: true

        web:
          adaptive_query_routing:
            enabled: true
            prefer_search_summary: true
            tavily_answer: advanced

    The ``web`` nested form keeps this close to ``web_search``/``web_extract``;
    the top-level form is supported for future non-web routing expansion.
    """

    if raw_config is None:
        try:
            from hermes_cli.config import load_config

            raw_config = load_config() or {}
        except Exception:
            raw_config = {}

    section = _select_config_section(raw_config if isinstance(raw_config, Mapping) else {})
    default = _DEF_CONFIG

    tavily_answer = section.get("tavily_answer", default.tavily_answer)
    if isinstance(tavily_answer, str):
        normalized_answer = tavily_answer.strip().lower()
        if normalized_answer == "":
            tavily_answer = False
        elif normalized_answer in {"false", "off", "none", "no", "0"}:
            tavily_answer = False
        elif normalized_answer in {"true", "on", "yes", "1"}:
            tavily_answer = True
        elif normalized_answer not in {"basic", "advanced"}:
            tavily_answer = default.tavily_answer

    return AdaptiveQueryRoutingConfig(
        enabled=_as_bool(section.get("enabled"), default.enabled),
        simple_max_words=_as_int(section.get("simple_max_words"), default.simple_max_words, minimum=1, maximum=100),
        prefer_search_summary=_as_bool(section.get("prefer_search_summary"), default.prefer_search_summary),
        tavily_answer=tavily_answer,
        force_web_keywords=_as_tuple(section.get("force_web_keywords"), default.force_web_keywords),
        complex_keywords=_as_tuple(section.get("complex_keywords"), default.complex_keywords),
        direct_keywords=_as_tuple(section.get("direct_keywords"), default.direct_keywords),
        complex_min_signals=_as_int(section.get("complex_min_signals"), default.complex_min_signals, minimum=1, maximum=10),
    )


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords if keyword)


def _word_count(query: str) -> int:
    # \w in a [] character class does not match CJK characters, so we count
    # ASCII/ASCII-compatible words and full CJK characters separately and sum.
    ascii_words = _WORD_RE.findall(query)  # [\w]+ part (CJK excluded inside [])
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", query)  # pure CJK chars
    return len(ascii_words) + len(cjk_chars)


def _has_url(query: str) -> bool:
    """Detect URLs with balanced-parentheses handling.

    Trailing punctuation (``.,;:!?`\"'\]\}>``) and unmatched closing
    parentheses are stripped so that URLs embedded in prose or markdown
    are matched correctly.
    """
    for m in _URL_RE.finditer(query):
        url = m.group()
        # Strip unmatched closing parens
        while url.endswith(")") and url.count(")") > url.count("("):
            url = url[:-1]
        # Strip other trailing punctuation that is never part of a URL
        while url and url[-1] in ".;:!?,'\"]}>":
            url = url[:-1]
        if len(url) > len("http://"):
            return True
    return False


def _normalize_tools(available_tools: Optional[Iterable[str]]) -> set[str]:
    if available_tools is None:
        return {"web_search", "web_extract"}
    return {str(tool).strip() for tool in available_tools if str(tool).strip()}


def _route(
    datasource: Datasource,
    complexity: Complexity,
    strategy: RetrievalStrategy,
    reason: str,
    confidence: float,
) -> QueryRoute:
    return QueryRoute(
        datasource=datasource,
        complexity=complexity,
        retrieval_strategy=strategy,
        reason=reason,
        confidence=round(max(0.0, min(confidence, 1.0)), 2),
    )


def classify_query(
    query: str,
    config: Optional[AdaptiveQueryRoutingConfig] = None,
    *,
    available_tools: Optional[Iterable[str]] = None,
) -> QueryRoute:
    """Classify a user query into Hermes' adaptive retrieval tiers.

    The classifier is deterministic and intentionally conservative. It avoids
    forcing web retrieval for ordinary evergreen knowledge, but it routes
    recency-sensitive or explicitly web-oriented questions to ``web_search``.
    URL-specific requests prefer ``web_extract`` when that tool is available.
    """

    cfg = config or load_adaptive_query_routing_config()
    tools = _normalize_tools(available_tools)
    text = (query or "").strip()
    text_l = f" {text.lower()} "
    words = _word_count(text)

    if not text:
        return _route("direct", "simple", "none", "empty query", 0.9)

    if not cfg.enabled:
        return _route("direct", "simple", "none", "adaptive routing disabled", 0.7)

    if _has_url(text):
        if "web_extract" in tools:
            return _route("web_extract", "intermediate", "single_retrieval", "query contains URL", 0.95)
        if "web_search" in tools:
            return _route("web_search", "intermediate", "single_retrieval", "query contains URL but web_extract unavailable", 0.75)
        return _route("direct", "intermediate", "none", "query contains URL but web tools unavailable", 0.55)

    has_web_signal = _contains_any(text_l, cfg.force_web_keywords)
    complex_signals = 0
    if _contains_any(text_l, cfg.complex_keywords):
        complex_signals += 1
    if words > max(cfg.simple_max_words, 18):
        complex_signals += 1
    if any(mark in text for mark in ("?", "？")) and words > cfg.simple_max_words:
        complex_signals += 1
    is_complex = complex_signals >= cfg.complex_min_signals

    if has_web_signal and "web_search" in tools:
        if is_complex:
            return _route("web_search", "complex", "iterative_retrieval", "recency/web intent plus multi-hop complexity", 0.86)
        return _route("web_search", "intermediate", "single_retrieval", "recency or explicit web-search intent", 0.88)

    if has_web_signal:
        return _route("direct", "intermediate", "none", "web intent detected but web_search unavailable", 0.5)

    if is_complex:
        # Without a recency/web signal, this may be pure reasoning.  Mark the
        # complexity but keep the default datasource direct so strong reasoning
        # models are not forced into unnecessary web calls for coding/debugging.
        return _route("direct", "complex", "none", "complex reasoning query without external-data signal", 0.65)

    if words <= cfg.simple_max_words or _contains_any(text_l, cfg.direct_keywords):
        return _route("direct", "simple", "none", "simple evergreen query", 0.82)

    return _route("direct", "intermediate", "none", "no external-data signal", 0.7)


def build_adaptive_query_routing_prompt(
    available_tools: Iterable[str],
    config: Optional[AdaptiveQueryRoutingConfig] = None,
) -> str:
    """Build the system-prompt block that teaches the LLM the routing policy."""

    cfg = config or load_adaptive_query_routing_config()
    tools = _normalize_tools(available_tools)
    has_search = "web_search" in tools
    has_extract = "web_extract" in tools

    if not cfg.enabled or not (has_search or has_extract):
        return ""

    search_line = (
        "- intermediate / web_search: use for current, recent, news, pricing, release/version, or explicitly web-search questions."
        if has_search
        else "- intermediate / web_search: unavailable in this session."
    )
    extract_line = (
        "- page-specific / web_extract: use for user-provided URLs, PDFs, or when search snippets/summaries are insufficient; do not extract every result by default."
        if has_extract
        else "- page-specific / web_extract: unavailable in this session; rely on search summaries/snippets when possible."
    )
    tavily_line = ""
    if cfg.prefer_search_summary and has_search:
        tavily_line = (
            " When the search backend is Tavily and web_search returns a Tavily ``data.answer`` AI summary or rich result descriptions,"
            " treat that as the first retrieval layer; answer from it with source URLs when sufficient instead of reflexively calling web_extract."
        )

    return (
        "Adaptive query routing (web/retrieval): before using web tools, classify the user query and pick the cheapest sufficient layer.\n"
        "- simple / direct: answer from model knowledge for stable evergreen facts, definitions, and straightforward reasoning; do not call web tools just because they exist.\n"
        f"{search_line}\n"
        f"{extract_line}\n"
        "- complex / iterative: for multi-hop current research, compare/investigate with web_search first, inspect the answer/snippets, then web_extract only selected high-value URLs if needed.\n"
        f"{tavily_line}"
    ).strip()


__all__ = [
    "AdaptiveQueryRoutingConfig",
    "QueryRoute",
    "build_adaptive_query_routing_prompt",
    "classify_query",
    "load_adaptive_query_routing_config",
]
