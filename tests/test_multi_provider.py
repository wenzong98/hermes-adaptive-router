"""Tests for multi-provider routing."""

import pytest

from hermes_adaptive_router.multi_provider import (
    ProviderPreference,
    classify_provider,
    route_with_provider,
)


class TestClassifyProvider:
    def test_chinese_query_prefers_mmx(self):
        pref = classify_provider("最新中文AI模型对比", available_providers={"tavily", "mmx", "exa"})
        assert pref.provider == "mmx"
        assert pref.confidence > 0.8

    def test_research_query_prefers_exa(self):
        pref = classify_provider("research paper on neural embeddings", available_providers={"tavily", "mmx", "exa"})
        assert pref.provider == "exa"
        assert pref.confidence > 0.75

    def test_news_query_prefers_tavily(self):
        pref = classify_provider("latest Bitcoin price today", available_providers={"tavily", "mmx", "exa"})
        assert pref.provider == "tavily"
        assert pref.confidence > 0.8

    def test_default_fallback_to_tavily(self):
        pref = classify_provider("Python programming tutorial", available_providers={"tavily", "mmx", "exa"})
        assert pref.provider == "tavily"

    def test_empty_providers_returns_auto(self):
        pref = classify_provider("test", available_providers=set())
        # Empty set means no providers available — must return "auto", not "tavily".
        assert pref.provider == "auto", (
            f"Empty providers should return 'auto', got {pref.provider!r}"
        )

    def test_none_providers_defaults_to_all(self):
        pref = classify_provider("Python tutorial", available_providers=None)
        assert pref.provider == "tavily"  # None means "assume all available"

    def test_single_available_provider_used(self):
        pref = classify_provider("Python tutorial", available_providers={"mmx"})
        assert pref.provider == "mmx"

    def test_unavailable_provider_skipped(self):
        pref = classify_provider("最新中文AI模型", available_providers={"tavily", "exa"})
        # MMX not available, should fall through to Tavily default
        assert pref.provider == "tavily"


class TestRouteWithProvider:
    def test_combined_routing(self):
        result = route_with_provider(
            "latest OpenAI pricing",
            available_tools={"web_search", "web_extract"},
            available_providers={"tavily", "mmx", "exa"},
        )
        assert result["datasource"] == "web_search"
        assert result["provider"] == "tavily"
        assert "price" in result["provider_reason"].lower() or "default" in result["provider_reason"].lower() or "recency" in result["provider_reason"].lower()

    def test_direct_query_routes_to_direct(self):
        result = route_with_provider(
            "What is Python?",
            available_tools={"web_search", "web_extract"},
            available_providers={"tavily", "mmx", "exa"},
        )
        assert result["datasource"] == "direct"
        assert result["provider"] == "auto"  # direct queries skip provider selection


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
