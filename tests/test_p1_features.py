"""Tests for P1 features: providers, intent, language, cache, A/B testing."""

import json
import time
from pathlib import Path

import pytest

from hermes_adaptive_router.ab_testing import (
    ABTestRunner,
    GoldenCase,
    StrategyMetrics,
    create_golden_dataset,
)
from hermes_adaptive_router.cache import (
    CacheStats,
    RoutingCache,
    cached_classify,
    get_default_cache,
    set_default_cache,
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
    classify_query,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Provider Registry Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderRegistry:
    """Tests for the extended provider registry."""

    def test_list_providers(self):
        names = list_provider_names()
        assert "tavily" in names
        assert "mmx" in names
        assert "exa" in names
        assert "google" in names
        assert "bing" in names
        assert "duckduckgo" in names
        assert "brave" in names
        assert "perplexity" in names
        assert len(names) == 8

    def test_get_provider_tavily(self):
        p = get_provider("tavily")
        assert p is not None
        assert p.name == "tavily"
        assert p.supports_answer_summary is True
        assert p.requires_api_key is True

    def test_get_provider_duckduckgo(self):
        p = get_provider("duckduckgo")
        assert p is not None
        assert p.requires_api_key is False
        assert p.supports_answer_summary is False

    def test_get_provider_perplexity(self):
        p = get_provider("perplexity")
        assert p is not None
        assert p.supports_answer_summary is True

    def test_get_provider_unknown(self):
        assert get_provider("nonexistent") is None

    def test_filter_by_capability(self):
        summary_providers = filter_providers_by_capability("supports_answer_summary")
        names = [p.name for p in summary_providers]
        assert "tavily" in names
        assert "perplexity" in names
        assert "mmx" not in names

    def test_filter_by_extract(self):
        extract_providers = filter_providers_by_capability("supports_extract")
        names = [p.name for p in extract_providers]
        assert "exa" in names
        assert "tavily" not in names

    def test_register_custom_provider(self):
        custom = ProviderInfo(
            name="custom_search",
            description="Custom search provider",
            requires_api_key=True,
            supports_extract=False,
            supports_answer_summary=False,
            keyword_signals=("custom", "special"),
        )
        register_provider(custom)
        assert "custom_search" in list_provider_names()
        p = get_provider("custom_search")
        assert p.description == "Custom search provider"

    def test_get_provider_keywords(self):
        keywords = get_provider_keywords("mmx")
        assert "中文" in keywords
        assert "minimax" in keywords

    def test_provider_info_dataclass(self):
        p = ProviderInfo(
            name="test",
            description="test provider",
            requires_api_key=False,
            supports_extract=True,
            supports_answer_summary=False,
            preferred_languages=("en",),
            keyword_signals=("test",),
        )
        assert p.preferred_languages == ("en",)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Extended Provider Classification Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifyProviderExtended:
    """Tests for classify_provider_extended."""

    def test_tavily_recency_signal(self):
        provider, reason, confidence = classify_provider_extended(
            "latest news today",
            available_providers={"tavily", "google", "bing"},
        )
        assert provider == "tavily"
        assert confidence > 0.8

    def test_google_keyword_signal(self):
        provider, reason, confidence = classify_provider_extended(
            "google search results",
            available_providers={"tavily", "google", "bing"},
        )
        assert provider == "google"

    def test_bing_keyword_signal(self):
        provider, reason, confidence = classify_provider_extended(
            "bing azure search",
            available_providers={"tavily", "google", "bing"},
        )
        assert provider == "bing"

    def test_duckduckgo_no_key(self):
        provider, reason, confidence = classify_provider_extended(
            "privacy search duckduckgo",
            available_providers={"tavily", "duckduckgo"},
        )
        assert provider == "duckduckgo"

    def test_brave_keyword_signal(self):
        provider, reason, confidence = classify_provider_extended(
            "brave search results",
            available_providers={"tavily", "brave"},
        )
        assert provider == "brave"

    def test_perplexity_keyword_signal(self):
        provider, reason, confidence = classify_provider_extended(
            "perplexity ai search with sources",
            available_providers={"tavily", "perplexity"},
        )
        assert provider == "perplexity"

    def test_fallback_chain(self):
        provider, reason, confidence = classify_provider_extended(
            "neutral query",
            available_providers={"google", "bing"},
        )
        # Should fall back to first available (google) since tavily not available
        assert provider in ("google", "bing")

    def test_empty_providers(self):
        provider, reason, confidence = classify_provider_extended(
            "test",
            available_providers=set(),
        )
        assert provider == "auto"

    def test_mmx_chinese_signal(self):
        provider, reason, confidence = classify_provider_extended(
            "中文内容搜索",
            available_providers={"tavily", "mmx", "google"},
        )
        assert provider == "mmx"

    def test_exa_research_signal(self):
        provider, reason, confidence = classify_provider_extended(
            "arxiv paper on neural networks",
            available_providers={"tavily", "exa", "google"},
        )
        assert provider == "exa"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Intent Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntentDetection:
    """Tests for query intent detection."""

    def test_code_intent_github(self):
        intent = detect_intent("github source code for quicksort")
        assert intent.code is True
        assert intent.primary_intent == "code"
        assert intent.confidence > 0.5

    def test_code_intent_chinese(self):
        intent = detect_intent("Python代码示例")
        assert intent.code is True
        assert "code" in intent.matched_keywords

    def test_image_intent(self):
        intent = detect_intent("show me images of cats")
        assert intent.image is True
        assert intent.primary_intent == "image"

    def test_image_intent_chinese(self):
        intent = detect_intent("猫咪图片")
        assert intent.image is True

    def test_video_intent(self):
        intent = detect_intent("youtube tutorial on python")
        assert intent.video is True
        assert intent.primary_intent == "video"

    def test_video_intent_chinese(self):
        intent = detect_intent("Python教程视频")
        assert intent.video is True

    def test_docs_intent(self):
        intent = detect_intent("API documentation for requests")
        assert intent.docs is True
        assert intent.primary_intent == "docs"

    def test_docs_intent_chinese(self):
        intent = detect_intent("API文档说明")
        assert intent.docs is True

    def test_shopping_intent(self):
        intent = detect_intent("buy iphone 16 on amazon")
        assert intent.shopping is True
        assert intent.primary_intent == "shopping"

    def test_shopping_intent_chinese(self):
        intent = detect_intent("淘宝购买iPhone")
        assert intent.shopping is True

    def test_general_intent(self):
        intent = detect_intent("hello world")
        assert intent.primary_intent == "general"
        assert intent.confidence == 0.0

    def test_multiple_intents(self):
        intent = detect_intent("buy python programming tutorial video")
        # Should detect shopping + code + video
        assert intent.shopping is True
        assert intent.code is True
        assert intent.video is True
        # Primary is the one with highest score
        assert intent.primary_intent in ("shopping", "code", "video")

    def test_list_intents(self):
        intents = list_intents()
        assert "code" in intents
        assert "image" in intents
        assert "video" in intents
        assert "docs" in intents
        assert "shopping" in intents

    def test_get_intent_keywords(self):
        keywords = get_intent_keywords("code")
        assert "github" in keywords
        assert "代码" in keywords

    def test_recommend_providers_by_intent_code(self):
        providers = recommend_providers_by_intent("code", {"tavily", "google", "bing"})
        assert providers[0] == "google"

    def test_recommend_providers_by_intent_image(self):
        providers = recommend_providers_by_intent("image", {"tavily", "google", "bing", "brave"})
        assert "bing" in providers

    def test_recommend_providers_filtered(self):
        providers = recommend_providers_by_intent("code", {"tavily", "bing"})
        assert "google" not in providers
        assert "bing" in providers


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Language Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLanguageDetection:
    """Tests for language detection."""

    def test_detect_english(self):
        result = detect_language("Hello world, how are you today?")
        assert result.language == "en"
        assert result.confidence >= 0.2
        assert result.script == "latin"

    def test_detect_chinese(self):
        result = detect_language("最新的人工智能新闻")
        assert result.language == "zh"
        assert result.confidence > 0.5
        assert result.script == "cjk"

    def test_detect_japanese(self):
        result = detect_language("最新のニュース")
        assert result.language == "ja"
        assert result.script == "cjk"

    def test_detect_korean(self):
        result = detect_language("최신 뉴스")
        assert result.language == "ko"
        assert result.script == "cjk"

    def test_detect_german(self):
        result = detect_language("der die das und ist")
        assert result.language == "de"
        assert result.script == "latin"

    def test_detect_french(self):
        result = detect_language("le la les un une et est")
        assert result.language == "fr"

    def test_detect_spanish(self):
        result = detect_language("el la los las un una y es")
        assert result.language == "es"

    def test_detect_russian(self):
        result = detect_language("в и не на я быть")
        assert result.language == "ru"
        assert result.script == "cyrillic"

    def test_detect_empty(self):
        result = detect_language("")
        assert result.language == "unknown"
        assert result.confidence == 0.0

    def test_is_cjk(self):
        assert is_cjk("中文") is True
        assert is_cjk("hello") is False

    def test_is_latin(self):
        assert is_latin("hello world") is True
        assert is_latin("中文") is False

    def test_get_language_name(self):
        assert get_language_name("zh") == "Chinese"
        assert get_language_name("en") == "English"
        assert get_language_name("ja") == "Japanese"
        assert get_language_name("unknown") == "Unknown"
        assert get_language_name("xx") == "xx"

    def test_recommend_providers_by_language_zh(self):
        providers = recommend_providers_by_language("zh", {"tavily", "mmx", "google"})
        assert providers[0] == "mmx"

    def test_recommend_providers_by_language_en(self):
        providers = recommend_providers_by_language("en", {"tavily", "exa", "google"})
        assert "tavily" in providers

    def test_recommend_providers_filtered(self):
        providers = recommend_providers_by_language("zh", {"tavily", "google"})
        assert "mmx" not in providers
        assert "tavily" in providers

    def test_multilingual_detection(self):
        result = detect_language("Hello 世界")
        # Should detect both English and Chinese signals
        assert result.is_multilingual is True or result.language in ("en", "zh")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Cache Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoutingCache:
    """Tests for LRU routing cache."""

    def test_basic_get_set(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        cache.set("test query", {"result": "direct"})
        result = cache.get("test query")
        assert result == {"result": "direct"}

    def test_cache_miss(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_hit_updates_lru(self):
        cache = RoutingCache(max_size=2, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        # Access 'a' to make it most recent
        cache.get("a")
        # Add 'c' — should evict 'b' (least recently used)
        cache.set("c", 3)
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_ttl_expiration(self):
        cache = RoutingCache(max_size=10, ttl_seconds=0.1)
        cache.set("test", "value")
        assert cache.get("test") == "value"
        time.sleep(0.15)
        assert cache.get("test") is None

    def test_zero_ttl_no_expiration(self):
        cache = RoutingCache(max_size=10, ttl_seconds=0)
        cache.set("test", "value")
        time.sleep(0.1)
        assert cache.get("test") == "value"

    def test_invalidate(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        cache.set("test", "value")
        assert cache.invalidate("test") is True
        assert cache.get("test") is None
        assert cache.invalidate("test") is False

    def test_clear(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert len(cache) == 0

    def test_cache_stats(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 0.5
        assert stats.size == 1

    def test_max_size_eviction(self):
        cache = RoutingCache(max_size=3, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Should evict 'a'
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_contains(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        cache.set("test", "value")
        assert "test" in cache
        assert "nonexistent" not in cache

    def test_normalization(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        cache.set("  Test   QUERY  ", "value")
        # Should match with different whitespace
        assert cache.get("test query") == "value"

    def test_default_cache(self):
        set_default_cache(None)
        cache = get_default_cache()
        assert isinstance(cache, RoutingCache)
        cache.set("test", "value")
        assert get_default_cache().get("test") == "value"

    def test_cached_classify_wrapper(self):
        cache = RoutingCache(max_size=10, ttl_seconds=3600)
        call_count = [0]

        def mock_classify(query):
            call_count[0] += 1
            return QueryRoute("direct", "simple", "none", 0.9, "test")

        wrapped = cached_classify(mock_classify, cache=cache)
        result1 = wrapped("test query")
        result2 = wrapped("test query")

        assert call_count[0] == 1  # Only called once
        assert result1.datasource == "direct"
        assert result2.datasource == "direct"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. A/B Testing Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestABTesting:
    """Tests for A/B testing framework."""

    def test_register_strategy(self):
        runner = ABTestRunner()
        runner.register_strategy("A", lambda q: QueryRoute("direct", "simple", "none", 0.9, "A"))
        assert "A" in runner._strategies

    def test_unregister_strategy(self):
        runner = ABTestRunner()
        runner.register_strategy("A", lambda q: QueryRoute("direct", "simple", "none", 0.9, "A"))
        assert runner.unregister_strategy("A") is True
        assert runner.unregister_strategy("A") is False

    def test_add_golden_case(self):
        runner = ABTestRunner()
        runner.add_golden_case(
            GoldenCase("test", "direct", "simple", "none")
        )
        assert len(runner._golden_dataset) == 1

    def test_run_comparison(self):
        runner = ABTestRunner()
        runner.register_strategy("A", lambda q: QueryRoute("direct", "simple", "none", 0.9, "A"))
        runner.register_strategy("B", lambda q: QueryRoute("web_search", "intermediate", "single_retrieval", 0.8, "B"))
        runner.add_golden_case(GoldenCase("test", "direct", "simple", "none"))

        results = runner.run_comparison()
        assert "A" in results
        assert "B" in results
        assert results["A"].total == 1
        assert results["A"].fully_correct == 1
        assert results["B"].fully_correct == 0

    def test_generate_report(self):
        runner = ABTestRunner()
        runner.register_strategy("A", lambda q: QueryRoute("direct", "simple", "none", 0.9, "A"))
        runner.register_strategy("B", lambda q: QueryRoute("web_search", "intermediate", "single_retrieval", 0.8, "B"))
        runner.add_golden_case(GoldenCase("test", "direct", "simple", "none"))
        runner.run_comparison()

        report = runner.generate_report()
        assert "A/B Test Report" in report
        assert "Strategy: A" in report
        assert "Strategy: B" in report
        assert "Winner:" in report

    def test_export_results(self, tmp_path):
        runner = ABTestRunner()
        runner.register_strategy("A", lambda q: QueryRoute("direct", "simple", "none", 0.9, "A"))
        runner.add_golden_case(GoldenCase("test", "direct", "simple", "none"))
        runner.run_comparison()

        path = tmp_path / "results.json"
        runner.export_results(path)
        assert path.exists()

        with open(path) as f:
            data = json.load(f)
        assert "strategies" in data
        assert "details" in data

    def test_load_golden_dataset(self, tmp_path):
        cases = [
            {
                "query": "Who wrote Hamlet?",
                "expected_datasource": "direct",
                "expected_complexity": "simple",
                "expected_strategy": "none",
            }
        ]
        path = tmp_path / "golden.json"
        create_golden_dataset(cases, path)

        runner = ABTestRunner()
        count = runner.load_golden_dataset(path)
        assert count == 1
        assert runner._golden_dataset[0].query == "Who wrote Hamlet?"

    def test_strategy_metrics(self):
        metrics = StrategyMetrics(name="test")
        metrics.total = 10
        metrics.correct_datasource = 8
        metrics.correct_complexity = 7
        metrics.correct_strategy = 9
        metrics.fully_correct = 6
        metrics.total_latency_ms = 50.0

        assert metrics.datasource_accuracy == 0.8
        assert metrics.complexity_accuracy == 0.7
        assert metrics.strategy_accuracy == 0.9
        assert metrics.overall_accuracy == 0.6
        assert metrics.mean_latency_ms == 5.0

        d = metrics.to_dict()
        assert d["name"] == "test"
        assert d["overall_accuracy"] == 0.6

    def test_error_handling(self):
        runner = ABTestRunner()
        runner.register_strategy("A", lambda q: (_ for _ in ()).throw(RuntimeError("boom")))
        runner.add_golden_case(GoldenCase("test", "direct", "simple", "none"))
        results = runner.run_comparison()
        # Should not crash; counts as incorrect
        assert results["A"].total == 1
        assert results["A"].fully_correct == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestP1Integration:
    """Integration tests combining multiple P1 features."""

    def test_route_with_provider_extended(self):
        from hermes_adaptive_router.multi_provider import route_with_provider

        result = route_with_provider(
            "latest news today",
            available_tools={"web_search"},
            available_providers={"tavily", "google", "bing"},
            use_extended_providers=True,
            use_language_detection=True,
        )
        assert result["datasource"] == "web_search"
        assert result["provider"] in ("tavily", "google", "bing")
        assert "language" in result
        assert "intent" in result

    def test_route_with_provider_chinese(self):
        from hermes_adaptive_router.multi_provider import route_with_provider

        result = route_with_provider(
            "最新中文AI新闻",
            available_tools={"web_search"},
            available_providers={"tavily", "mmx", "google"},
            use_extended_providers=True,
            use_language_detection=True,
        )
        assert result["datasource"] == "web_search"
        assert result["language"] == "zh"
        # With high-confidence Chinese detection, should prefer MMX
        assert result["provider"] == "mmx"

    def test_route_with_provider_disabled_language(self):
        from hermes_adaptive_router.multi_provider import route_with_provider

        result = route_with_provider(
            "latest news",
            available_tools={"web_search"},
            available_providers={"tavily", "google"},
            use_extended_providers=True,
            use_language_detection=False,
        )
        assert result["language"] == "unknown"

    def test_route_with_provider_direct_query(self):
        from hermes_adaptive_router.multi_provider import route_with_provider

        result = route_with_provider(
            "What is Python?",
            available_tools={"web_search"},
            available_providers={"tavily", "google"},
            use_extended_providers=True,
            use_language_detection=True,
        )
        assert result["datasource"] == "direct"
        assert result["provider"] == "auto"

    def test_end_to_end_intent_provider_recommendation(self):
        intent = detect_intent("github python code example")
        assert intent.code is True
        providers = recommend_providers_by_intent(
            intent.primary_intent,
            {"tavily", "google", "bing", "exa"}
        )
        assert "google" in providers

    def test_end_to_end_language_provider_recommendation(self):
        lang = detect_language("最新的人工智能技术")
        assert lang.language == "zh"
        providers = recommend_providers_by_language(
            lang.language,
            {"tavily", "mmx", "google", "bing"}
        )
        assert providers[0] == "mmx"
