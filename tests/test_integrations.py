"""Tests for Hermes integration helpers."""

import sys
import types

from hermes_adaptive_router.integrations import (
    classify_for_hermes,
    get_system_prompt_addition,
    tavily_search_payload_override,
)


def test_classify_for_hermes_routes_direct():
    route = classify_for_hermes("Who wrote Hamlet?", available_tools={"web_search", "web_extract"})
    assert route.datasource == "direct"
    assert route.complexity == "simple"


def test_classify_for_hermes_routes_web_search():
    route = classify_for_hermes("latest news today", available_tools={"web_search"})
    assert route.datasource == "web_search"


def test_system_prompt_addition_when_enabled():
    prompt = get_system_prompt_addition({"web_search", "web_extract"})
    assert "Adaptive query routing" in prompt
    assert "direct" in prompt


def test_system_prompt_addition_when_disabled():
    prompt = get_system_prompt_addition(
        {"web_search"},
        raw_config={"adaptive_query_routing": {"enabled": False}},
    )
    assert prompt == ""


def test_tavily_payload_override_basic():
    payload = tavily_search_payload_override(
        {"query": "test"},
        raw_config={"adaptive_query_routing": {"enabled": True, "prefer_search_summary": True, "tavily_answer": "basic"}},
    )
    assert payload["include_answer"] == "basic"
    assert "search_depth" not in payload


def test_tavily_payload_override_advanced():
    payload = tavily_search_payload_override(
        {"query": "test"},
        raw_config={"adaptive_query_routing": {"enabled": True, "prefer_search_summary": True, "tavily_answer": "advanced"}},
    )
    assert payload["include_answer"] == "advanced"
    assert payload["search_depth"] == "advanced"


def test_tavily_payload_override_disabled():
    payload = tavily_search_payload_override(
        {"query": "test"},
        raw_config={"adaptive_query_routing": {"enabled": False}},
    )
    assert "include_answer" not in payload


def test_classify_for_hermes_loads_host_config_outside_core_router(monkeypatch):
    fake_config_module = types.ModuleType("hermes_cli.config")
    fake_config_module.load_config = lambda: {
        "adaptive_query_routing": {
            "enabled": True,
            "simple_max_words": 2,
        }
    }
    fake_package = types.ModuleType("hermes_cli")
    fake_package.config = fake_config_module

    monkeypatch.setitem(sys.modules, "hermes_cli", fake_package)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake_config_module)

    route = classify_for_hermes(
        "Python programming language overview",
        available_tools={"web_search", "web_extract"},
    )
    assert route.complexity == "intermediate"
