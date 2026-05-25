"""Multi-provider search routing for Hermes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from hermes_adaptive_router.intent_signals import (
    detect_intent,
    recommend_providers_by_intent,
)
from hermes_adaptive_router.language_detection import (
    detect_language,
    recommend_providers_by_language,
)
from hermes_adaptive_router.providers import (
    classify_provider_extended,
    list_provider_names,
)
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

    if not cfg.enabled:
        return ProviderPreference("auto", "adaptive routing disabled", 0.5)

    provider_name, provider_reason, provider_confidence = classify_provider_extended(
        query,
        available_providers=providers,
    )
    return ProviderPreference(provider_name, provider_reason, provider_confidence)


def route_with_provider(
    query: str,
    config: Optional[AdaptiveQueryRoutingConfig] = None,
    *,
    available_tools: Optional[Iterable[str]] = None,
    available_providers: Optional[Iterable[str]] = None,
    use_extended_providers: bool = True,
    use_language_detection: bool = True,
) -> dict[str, Any]:
    """Full routing decision: datasource + complexity + provider.

    Returns a dict combining QueryRoute and ProviderPreference.

    Args:
        query: User query text.
        config: Adaptive routing config.
        available_tools: Set of available tool names.
        available_providers: Set of available provider names.
        use_extended_providers: If True, use the extended provider registry
            (Google, Bing, DuckDuckGo, Brave, Perplexity) in addition to
            the original three (Tavily, MMX, Exa).
        use_language_detection: If True, use language detection to influence
            provider selection (e.g., Chinese queries prefer MMX).
    """
    route = classify_query(query, config, available_tools=available_tools)
    cfg = config or load_adaptive_query_routing_config()

    # Normalize providers
    if available_providers is not None:
        providers = set(available_providers)
    elif use_extended_providers:
        providers = set(list_provider_names())
    else:
        providers = {"tavily", "mmx", "exa"}

    # When routing is disabled or query is empty/direct, skip provider selection
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
            "language": "unknown",
            "intent": "general",
        }

    # Language and intent detection.
    lang_result = detect_language(query) if use_language_detection else None
    language = lang_result.language if lang_result else "unknown"
    lang_confidence = lang_result.confidence if lang_result else 0.0
    intent_result = detect_intent(query)
    intent = intent_result.primary_intent

    # Provider selection comes from the registry-backed selector.
    provider_name, provider_reason, provider_confidence = classify_provider_extended(
        query,
        available_providers=providers,
    )

    # Language-based provider override (if confidence is high)
    if use_language_detection and lang_result and lang_result.confidence >= 0.5:
        lang_providers = recommend_providers_by_language(language, providers)
        if lang_providers and lang_providers[0] != provider_name:
            # Override if language strongly suggests a different provider
            if language == "zh" and "mmx" in providers:
                provider_name = "mmx"
                provider_reason = f"Language-based override ({language}, confidence={lang_confidence:.2f})"
                provider_confidence = max(provider_confidence, lang_confidence)
            elif language in ("ja", "ko") and "google" in providers:
                provider_name = "google"
                provider_reason = f"Language-based override ({language}, confidence={lang_confidence:.2f})"
                provider_confidence = max(provider_confidence, lang_confidence)

    # Intent is a weaker signal than explicit provider/language matches.
    if use_extended_providers and intent_result.confidence >= 0.65:
        intent_providers = recommend_providers_by_intent(intent, providers)
        generic_reason = provider_reason.startswith("Default provider") or provider_reason.startswith("Fallback")
        if intent_providers and generic_reason and intent_providers[0] != provider_name:
            provider_name = intent_providers[0]
            provider_reason = f"Intent-based override ({intent}, confidence={intent_result.confidence:.2f})"
            provider_confidence = max(provider_confidence, intent_result.confidence)

    return {
        "datasource": route.datasource,
        "complexity": route.complexity,
        "retrieval_strategy": route.retrieval_strategy,
        "confidence": route.confidence,
        "reason": route.reason,
        "provider": provider_name,
        "provider_reason": provider_reason,
        "provider_confidence": provider_confidence,
        "language": language,
        "language_confidence": lang_confidence,
        "intent": intent,
        "intent_confidence": intent_result.confidence,
    }


__all__ = [
    "ProviderPreference",
    "classify_provider",
    "route_with_provider",
]
