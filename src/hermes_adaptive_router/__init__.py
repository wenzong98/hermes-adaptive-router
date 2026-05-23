"""Hermes Adaptive Query Router — deterministic query classification."""

from hermes_adaptive_router.ab_testing import (
    ABTestRunner,
    GoldenCase,
    StrategyMetrics,
    StrategyResult,
    create_golden_dataset,
)
from hermes_adaptive_router.cache import (
    CacheStats,
    RoutingCache,
    cached_classify,
    get_default_cache,
    set_default_cache,
)
from hermes_adaptive_router.integrations import (
    classify_for_hermes,
    get_system_prompt_addition,
    tavily_search_payload_override,
)
from hermes_adaptive_router.intent_signals import (
    IntentSignals,
    detect_intent,
    get_intent_keywords,
    list_intents,
    recommend_providers_by_intent,
)
from hermes_adaptive_router.language_detection import (
    LanguageResult,
    detect_language,
    get_language_name,
    is_cjk,
    is_latin,
    recommend_providers_by_language,
)
from hermes_adaptive_router.multi_provider import (
    ProviderPreference,
    classify_provider,
    route_with_provider,
)
from hermes_adaptive_router.observability import (
    RoutingEvent,
    clear_routing_history,
    get_routing_history,
    get_routing_stats,
    record_routing_event,
    set_post_route_callback,
)
from hermes_adaptive_router.providers import (
    ProviderInfo,
    classify_provider_extended,
    filter_providers_by_capability,
    get_provider,
    get_provider_keywords,
    list_provider_names,
    list_providers,
    register_provider,
)
from hermes_adaptive_router.router import (
    AdaptiveQueryRoutingConfig,
    QueryRoute,
    build_adaptive_query_routing_prompt,
    classify_query,
    load_adaptive_query_routing_config,
)

__all__ = [
    "ABTestRunner",
    "AdaptiveQueryRoutingConfig",
    "CacheStats",
    "GoldenCase",
    "IntentSignals",
    "LanguageResult",
    "ProviderInfo",
    "ProviderPreference",
    "QueryRoute",
    "RoutingCache",
    "RoutingEvent",
    "StrategyMetrics",
    "StrategyResult",
    "build_adaptive_query_routing_prompt",
    "cached_classify",
    "classify_for_hermes",
    "classify_provider",
    "classify_provider_extended",
    "classify_query",
    "clear_routing_history",
    "create_golden_dataset",
    "detect_intent",
    "detect_language",
    "filter_providers_by_capability",
    "get_default_cache",
    "get_intent_keywords",
    "get_language_name",
    "get_provider",
    "get_provider_keywords",
    "get_routing_history",
    "get_routing_stats",
    "get_system_prompt_addition",
    "is_cjk",
    "is_latin",
    "list_intents",
    "list_provider_names",
    "list_providers",
    "load_adaptive_query_routing_config",
    "recommend_providers_by_intent",
    "recommend_providers_by_language",
    "record_routing_event",
    "register_provider",
    "route_with_provider",
    "set_default_cache",
    "set_post_route_callback",
    "tavily_search_payload_override",
]
