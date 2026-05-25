"""Extended provider registry and signals for hermes-adaptive-router.

This module adds support for additional search providers beyond the
original three (Tavily, MMX, Exa):
- Google (SerpAPI / Programmable Search Engine)
- Bing (Azure Cognitive Search)
- DuckDuckGo (no API key required)
- Brave Search
- Perplexity (AI-native search with citations)

Each provider has keyword signals that help the router decide when to
prefer it over the default Tavily.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hermes_adaptive_router.intent_signals import recommend_providers_by_intent


@dataclass(frozen=True)
class ProviderInfo:
    """Metadata for a search provider."""

    name: str
    description: str
    requires_api_key: bool
    supports_extract: bool
    supports_answer_summary: bool
    preferred_languages: tuple[str, ...] = ()
    keyword_signals: tuple[str, ...] = ()


# ── Provider registry ────────────────────────────────────────────────────────

_ALL_PROVIDERS: dict[str, ProviderInfo] = {}


def register_provider(info: ProviderInfo) -> None:
    """Register a provider at import time."""
    _ALL_PROVIDERS[info.name] = info
    if "_build_provider_keyword_map" in globals():
        _build_provider_keyword_map()


def get_provider(name: str) -> ProviderInfo | None:
    """Get provider metadata by name."""
    return _ALL_PROVIDERS.get(name)


def list_providers() -> list[ProviderInfo]:
    """Return all registered providers."""
    return list(_ALL_PROVIDERS.values())


def list_provider_names() -> list[str]:
    """Return all registered provider names."""
    return list(_ALL_PROVIDERS.keys())


def filter_providers_by_capability(
    capability: str,
) -> list[ProviderInfo]:
    """Filter providers by a boolean attribute name.

    Example: ``filter_providers_by_capability("supports_extract")``
    """
    return [p for p in _ALL_PROVIDERS.values() if getattr(p, capability, False)]


# ── Built-in providers ───────────────────────────────────────────────────────

register_provider(
    ProviderInfo(
        name="tavily",
        description="Default provider. Best all-rounder with AI answer summaries.",
        requires_api_key=True,
        supports_extract=False,
        supports_answer_summary=True,
        keyword_signals=(
            "latest", "current", "today", "now", "recent", "news",
            "breaking", "price", "pricing", "release date",
            "changelog", "version",
            "最新", "今天", "现在", "近期", "新闻",
            "价格", "定价", "版本", "发布日期",
        ),
    )
)

register_provider(
    ProviderInfo(
        name="mmx",
        description="MiniMax search. Good for Chinese queries.",
        requires_api_key=True,
        supports_extract=False,
        supports_answer_summary=False,
        preferred_languages=("zh",),
        keyword_signals=(
            "中文", "汉语", "中国", "国内", "国产", "中文网站",
            "百度", "知乎", "微博", "微信", "哔哩哔哩", "bilibili",
            "抖音", "小红书", "淘宝", "京东",
            "minimax", "海螺", "abab",
        ),
    )
)

register_provider(
    ProviderInfo(
        name="exa",
        description="Semantic / neural search. Good for research and academic queries.",
        requires_api_key=True,
        supports_extract=True,
        supports_answer_summary=False,
        keyword_signals=(
            "research", "paper", "arxiv", "academic", "scholar",
            "semantic", "neural", "embedding", "vector",
            "论文", "研究", "学术", "科研",
            "in-depth", "deep dive", "comprehensive", "thorough",
            "深入", "全面", "系统",
        ),
    )
)

register_provider(
    ProviderInfo(
        name="google",
        description="Google Search via SerpAPI or Programmable Search Engine.",
        requires_api_key=True,
        supports_extract=False,
        supports_answer_summary=False,
        keyword_signals=(
            "google", "serp", "programmable search",
            "谷歌", "谷歌搜索",
        ),
    )
)

register_provider(
    ProviderInfo(
        name="bing",
        description="Bing Search via Azure Cognitive Search.",
        requires_api_key=True,
        supports_extract=False,
        supports_answer_summary=False,
        keyword_signals=(
            "bing", "azure", "microsoft search",
            "必应", "微软搜索",
        ),
    )
)

register_provider(
    ProviderInfo(
        name="duckduckgo",
        description="DuckDuckGo search. No API key required.",
        requires_api_key=False,
        supports_extract=False,
        supports_answer_summary=False,
        keyword_signals=(
            "duckduckgo", "ddg", "privacy search",
            "隐私搜索",
        ),
    )
)

register_provider(
    ProviderInfo(
        name="brave",
        description="Brave Search. Privacy-focused with independent index.",
        requires_api_key=True,
        supports_extract=False,
        supports_answer_summary=False,
        keyword_signals=(
            "brave", "brave search",
        ),
    )
)

register_provider(
    ProviderInfo(
        name="perplexity",
        description="Perplexity API. AI-native search with inline citations.",
        requires_api_key=True,
        supports_extract=False,
        supports_answer_summary=True,
        keyword_signals=(
            "perplexity", "ai search", "citation",
            "perplexity api", "with sources",
        ),
    )
)


# ── Provider signals for routing ─────────────────────────────────────────────

# Re-export for backward compatibility with existing multi_provider.py imports
_MMX_PREFERRED_KEYWORDS = tuple(
    (get_provider("mmx") or ProviderInfo("", "", False, False, False)).keyword_signals
)
_EXA_PREFERRED_KEYWORDS = tuple(
    (get_provider("exa") or ProviderInfo("", "", False, False, False)).keyword_signals
)
_TAVILY_PREFERRED_KEYWORDS = tuple(
    (get_provider("tavily") or ProviderInfo("", "", False, False, False)).keyword_signals
)

# New provider keyword maps
_PROVIDER_KEYWORD_MAP: dict[str, tuple[str, ...]] = {}


def _build_provider_keyword_map() -> None:
    """Build the keyword map from registered providers."""
    global _PROVIDER_KEYWORD_MAP
    _PROVIDER_KEYWORD_MAP = {
        name: info.keyword_signals
        for name, info in _ALL_PROVIDERS.items()
        if info.keyword_signals
    }


_build_provider_keyword_map()


def get_provider_keywords(provider: str) -> tuple[str, ...]:
    """Get keyword signals for a specific provider."""
    return _PROVIDER_KEYWORD_MAP.get(provider, ())


def _match_provider_keyword(
    query: str,
    providers: set[str],
) -> tuple[str, str, float] | None:
    text_l = f" {query.lower()} "
    best_match: tuple[str, str, float, int, int] | None = None
    priority_order = ["mmx", "exa", "tavily", "google", "bing", "duckduckgo", "brave", "perplexity"]
    priority_rank = {name: idx for idx, name in enumerate(priority_order)}

    for name, keywords in _PROVIDER_KEYWORD_MAP.items():
        if name not in providers:
            continue
        match_count = sum(1 for kw in keywords if kw and kw.lower() in text_l)
        if match_count <= 0:
            continue
        info = get_provider(name)
        desc = info.description if info else name
        rank = priority_rank.get(name, len(priority_rank))
        candidate = (name, f"{desc} keyword signal", 0.82, match_count, -rank)
        if best_match is None or candidate[3:] > best_match[3:]:
            best_match = candidate

    if best_match is None:
        return None
    return best_match[:3]


def _fallback_provider(providers: set[str]) -> tuple[str, str, float]:
    if "tavily" in providers:
        return ("tavily", "Default provider", 0.7)

    fallback_chain = ["exa", "mmx", "duckduckgo", "brave", "perplexity", "google", "bing"]
    for name in fallback_chain:
        if name in providers:
            return (name, "Fallback (Tavily unavailable)", 0.6)

    if providers:
        first = next(iter(providers))
        return (first, "Fallback (no keyword match)", 0.5)

    return ("auto", "No specific provider available", 0.4)


def classify_provider_extended(
    query: str,
    available_providers: Iterable[str] | None = None,
    *,
    intent: str | None = None,
) -> tuple[str, str, float]:
    """Pick the best provider from an extended set.

    Returns ``(provider_name, reason, confidence)``.

    Priority order:
    1. Keyword signal match (highest confidence)
    2. Default to Tavily if available (medium confidence)
    3. Fallback chain: Exa → MMX → DuckDuckGo (no key) → first available
    """
    providers = set(available_providers) if available_providers is not None else set(list_provider_names())
    if not providers:
        return ("auto", "No specific provider available", 0.4)

    intent_candidates = recommend_providers_by_intent(intent or "general", providers)
    if intent and intent != "general" and intent_candidates:
        preferred = intent_candidates[0]
        return (preferred, f"Intent-based preference ({intent})", 0.76)

    keyword_match = _match_provider_keyword(query, providers)
    if keyword_match is not None:
        return keyword_match

    return _fallback_provider(providers)


__all__ = [
    "ProviderInfo",
    "classify_provider_extended",
    "filter_providers_by_capability",
    "get_provider",
    "get_provider_keywords",
    "list_provider_names",
    "list_providers",
    "register_provider",
]
