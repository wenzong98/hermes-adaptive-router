"""Multi-provider search routing for Hermes.

Extends the adaptive query router with provider-aware routing:
- Tavily: default, supports search + extract + crawl, has AI answer summary
- MMX: MiniMax search, good for Chinese queries, no extract/crawl
- Exa: semantic/neural search, good for research, supports extract

The router picks the best provider based on query signals and availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from hermes_adaptive_router.router import (
    AdaptiveQueryRoutingConfig,
    QueryRoute,
    classify_query,
    load_adaptive_query_routing_config,
)


@dataclass(frozen=True)
class ProviderPreference:
    """Which provider to use for a given query."""

    provider: str  # "tavily", "mmx", "exa", "auto"
    reason: str
    confidence: float


# Provider-specific keyword signals
_MMX_PREFERRED_KEYWORDS = (
    # Chinese content signals
    "中文", "汉语", "中国", "国内", "国产", "中文网站",
    "百度", "知乎", "微博", "微信", "哔哩哔哩", "bilibili",
    "抖音", "小红书", "淘宝", "京东",
    # MiniMax-specific
    "minimax", "海螺", "abab",
)

_EXA_PREFERRED_KEYWORDS = (
    # Research / academic signals
    "research", "paper", "arxiv", "academic", "scholar",
    "semantic", "neural", "embedding", "vector",
    "论文", "研究", "学术", "科研",
    # Deep content signals
    "in-depth", "deep dive", "comprehensive", "thorough",
    "深入", "全面", "系统",
)

_TAVILY_PREFERRED_KEYWORDS = (
    # Recency signals where Tavily's answer summary shines
    "latest", "current", "today", "now", "recent", "news",
    "breaking", "price", "pricing", "release date",
    "changelog", "version",
    "最新", "今天", "现在", "近期", "新闻",
    "价格", "定价", "版本", "发布日期",
)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords if keyword)


def classify_provider(
    query: str,
    config: Optional[AdaptiveQueryRoutingConfig] = None,
    *,
    available_providers: Optional[Iterable[str]] = None,
) -> ProviderPreference:
    """Pick the best search provider for a query.

    Args:
        query: User query text.
        config: Adaptive routing config.
        available_providers: Set of available provider names
            (e.g. {"tavily", "mmx", "exa"}). If None, assumes all.

    Returns:
        ProviderPreference with provider name and reason.
    """
    cfg = config or load_adaptive_query_routing_config()
    providers = set(available_providers) if available_providers is not None else {"tavily", "mmx", "exa"}
    text_l = f" {query.lower()} "

    if not cfg.enabled:
        return ProviderPreference("auto", "adaptive routing disabled", 0.5)

    # Check provider-specific signals
    if "mmx" in providers and _contains_any(text_l, _MMX_PREFERRED_KEYWORDS):
        return ProviderPreference("mmx", "Chinese/MiniMax-specific query", 0.82)

    if "exa" in providers and _contains_any(text_l, _EXA_PREFERRED_KEYWORDS):
        return ProviderPreference("exa", "Research/academic query", 0.78)

    if "tavily" in providers and _contains_any(text_l, _TAVILY_PREFERRED_KEYWORDS):
        return ProviderPreference(
            "tavily", "Recency query where Tavily answer summary excels", 0.85
        )

    # Default: Tavily if available (best all-rounder with answer summary)
    if "tavily" in providers:
        return ProviderPreference("tavily", "Default provider", 0.7)

    # Fallback chain — only return a provider if it is actually available
    if "exa" in providers:
        return ProviderPreference("exa", "Fallback (Tavily unavailable)", 0.6)
    if "mmx" in providers:
        return ProviderPreference("mmx", "Fallback (Tavily/Exa unavailable)", 0.55)

    return ProviderPreference("auto", "No specific provider available", 0.4)


def _route_provider(query: str, providers: set[str]) -> ProviderPreference:
    """Internal: pick provider without config check (used by route_with_provider)."""
    text_l = f" {query.lower()} "

    if "mmx" in providers and _contains_any(text_l, _MMX_PREFERRED_KEYWORDS):
        return ProviderPreference("mmx", "Chinese/MiniMax-specific query", 0.82)

    if "exa" in providers and _contains_any(text_l, _EXA_PREFERRED_KEYWORDS):
        return ProviderPreference("exa", "Research/academic query", 0.78)

    if "tavily" in providers and _contains_any(text_l, _TAVILY_PREFERRED_KEYWORDS):
        return ProviderPreference(
            "tavily", "Recency query where Tavily answer summary excels", 0.85
        )

    if "tavily" in providers:
        return ProviderPreference("tavily", "Default provider", 0.7)
    if "exa" in providers:
        return ProviderPreference("exa", "Fallback (Tavily unavailable)", 0.6)
    if "mmx" in providers:
        return ProviderPreference("mmx", "Fallback (Tavily/Exa unavailable)", 0.55)

    return ProviderPreference("auto", "No specific provider available", 0.4)


def route_with_provider(
    query: str,
    config: Optional[AdaptiveQueryRoutingConfig] = None,
    *,
    available_tools: Optional[Iterable[str]] = None,
    available_providers: Optional[Iterable[str]] = None,
) -> dict[str, Any]:
    """Full routing decision: datasource + complexity + provider.

    Returns a dict combining QueryRoute and ProviderPreference.
    """
    route = classify_query(query, config, available_tools=available_tools)
    providers = set(available_providers) if available_providers is not None else {"tavily", "mmx", "exa"}

    # When routing is disabled or query is empty/direct, skip provider selection
    cfg = config or load_adaptive_query_routing_config()
    if not cfg.enabled or not query or not query.strip() or route.datasource == "direct":
        return {
            "datasource": route.datasource,
            "complexity": route.complexity,
            "retrieval_strategy": route.retrieval_strategy,
            "confidence": route.confidence,
            "reason": route.reason,
            "provider": "auto",
            "provider_reason": "routing disabled or no web tools needed",
            "provider_confidence": 0.0,
        }

    provider_pref = _route_provider(query, providers)

    return {
        "datasource": route.datasource,
        "complexity": route.complexity,
        "retrieval_strategy": route.retrieval_strategy,
        "confidence": route.confidence,
        "reason": route.reason,
        "provider": provider_pref.provider,
        "provider_reason": provider_pref.reason,
        "provider_confidence": provider_pref.confidence,
    }


__all__ = [
    "ProviderPreference",
    "classify_provider",
    "route_with_provider",
]
