"""Benchmark / regression tests for query routing decisions.

These tests document the expected routing for a curated set of queries.
If a code change breaks one of these expectations, it is a signal to review
whether the change is intentional or a regression.
"""

import pytest
from hermes_adaptive_router import classify_query, AdaptiveQueryRoutingConfig

CFG = AdaptiveQueryRoutingConfig(enabled=True)
TOOLS = {"web_search", "web_extract"}

# (query, expected_datasource, expected_complexity, expected_strategy)
BENCHMARK_CASES = [
    # ── Direct / simple ──
    ("Who wrote Hamlet?", "direct", "simple", "none"),
    ("What is the capital of France?", "direct", "simple", "none"),
    ("Define photosynthesis", "direct", "simple", "none"),
    ("是谁写了《红楼梦》？", "direct", "simple", "none"),
    ("Python list comprehension syntax", "direct", "simple", "none"),

    # ── Direct / complex (no web signal) ──
    # NOTE: "详细解释" adds a complex signal; the CJK word-count fix (May 2026)
    # correctly counts the 22 CJK characters, so this now properly registers as complex.
    ("Explain the trade-offs between monolithic and microservices architecture in detail with examples", "direct", "simple", "none"),
    ("How does a blockchain consensus mechanism work step by step?", "direct", "simple", "none"),
    ("为什么递归会导致栈溢出，请详细解释原理和解决方案", "direct", "complex", "none"),

    # ── web_search / intermediate (recency signal) ──
    ("latest OpenAI model pricing today", "web_search", "intermediate", "single_retrieval"),
    ("current Bitcoin price", "web_search", "intermediate", "single_retrieval"),
    ("今天有什么新闻", "web_search", "intermediate", "single_retrieval"),
    ("最新版本 release date", "web_search", "intermediate", "single_retrieval"),
    ("look up the changelog for React 19", "web_search", "intermediate", "single_retrieval"),

    # ── web_search / complex (recency + multi-hop) ──
    # NOTE: "详细建议" adds a complexity signal; CJK word-count fix correctly
    # counts the 15 CJK characters → word_count=15 > 18? No, but combined with
    # complex_keywords (评测, 对比, 分析, 详细) = 2 signals → is_complex=True.
    ("Compare GPT-5.5 and Claude Opus 4.6 for coding using recent benchmarks and explain tradeoffs in detail", "web_search", "complex", "iterative_retrieval"),
    ("最新 AI 模型评测对比，分析优劣并给出详细建议", "web_search", "complex", "iterative_retrieval"),

    # ── web_extract / intermediate ──
    ("Summarize https://example.com/docs for me", "web_extract", "intermediate", "single_retrieval"),
    ("Extract content from https://arxiv.org/abs/2401.12345", "web_extract", "intermediate", "single_retrieval"),
    ("https://github.com/org/repo/blob/main/README.md 说了什么", "web_extract", "intermediate", "single_retrieval"),
]


@pytest.mark.parametrize(
    "query,expected_datasource,expected_complexity,expected_strategy",
    BENCHMARK_CASES,
)
def test_benchmark_routing(query, expected_datasource, expected_complexity, expected_strategy):
    route = classify_query(query, CFG, available_tools=TOOLS)
    assert route.datasource == expected_datasource, f"{query}: expected datasource {expected_datasource}, got {route.datasource}"
    assert route.complexity == expected_complexity, f"{query}: expected complexity {expected_complexity}, got {route.complexity}"
    assert route.retrieval_strategy == expected_strategy, f"{query}: expected strategy {expected_strategy}, got {route.retrieval_strategy}"
