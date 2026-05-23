"""Query intent detection signals.

Extends the router with fine-grained intent categories:
- code: GitHub, StackOverflow, programming questions
- image: image search, photos, screenshots
- video: video search, YouTube, tutorials
- docs: documentation, API reference, manuals
- shopping: buy, price comparison, e-commerce

These signals can be used to:
1. Augment routing decisions (e.g., code queries → prefer Google/StackOverflow)
2. Select specialized providers (e.g., image queries → Bing Image Search)
3. Generate richer system prompts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class IntentSignals:
    """Detected intent signals for a query."""

    code: bool = False
    image: bool = False
    video: bool = False
    docs: bool = False
    shopping: bool = False
    primary_intent: str = "general"
    confidence: float = 0.0
    matched_keywords: tuple[str, ...] = field(default_factory=tuple)


# ── Intent keyword sets ──────────────────────────────────────────────────────

_CODE_KEYWORDS = (
    # English
    "github", "stackoverflow", "stack overflow", "code", "source code",
    "programming", "developer", "dev", "api", "sdk", "library",
    "function", "method", "class", "module", "package",
    "bug", "debug", "fix", "error", "exception", "traceback",
    "python", "javascript", "typescript", "java", "go", "rust",
    "cpp", "c++", "c#", "ruby", "php", "swift", "kotlin",
    "snippet", "example code", "code example", "how to code",
    "implementation", "implement", "algorithm", "data structure",
    "regex", "regular expression", "sql", "query", "database",
    "docker", "kubernetes", "k8s", "ci/cd", "pipeline",
    "git", "commit", "pull request", "pr", "issue",
    "compile", "build", "deploy", "test", "unit test",
    # Chinese
    "代码", "源码", "源代码", "程序", "编程", "开发",
    "函数", "方法", "类", "模块", "包", "库",
    "bug", "调试", "修复", "错误", "异常",
    "算法", "数据结构", "实现", "示例代码",
    "正则表达式", "数据库", "查询", "sql",
    "部署", "编译", "构建", "测试", "git",
)

_IMAGE_KEYWORDS = (
    # English
    "image", "images", "photo", "photos", "picture", "pictures",
    "screenshot", "screenshots", "gif", "jpg", "jpeg", "png",
    "webp", "svg", "icon", "icons", "logo", "diagram",
    "chart", "graph", "infographic", "visualization",
    "look like", "appearance", "design", "ui", "ux",
    "mockup", "wireframe", "prototype", "render",
    # Chinese
    "图片", "照片", "截图", "图像", "图标",
    "设计图", "效果图", "示意图", "可视化",
    "长什么样", "外观", "界面", "设计",
)

_VIDEO_KEYWORDS = (
    # English
    "video", "videos", "youtube", "vimeo", "tiktok",
    "tutorial", "tutorials", "how-to", "howto", "walkthrough",
    "demo", "demonstration", "presentation", "recording",
    "lecture", "course", "lesson", "training",
    "watch", "stream", "streaming", "live",
    # Chinese
    "视频", "教程", "演示", "讲解", "课程",
    "直播", "录播", "观看", "学习",
    "b站", "哔哩哔哩", "抖音", "快手",
)

_DOCS_KEYWORDS = (
    # English
    "documentation", "docs", "doc", "manual", "guide",
    "api reference", "api docs", "reference", "specification",
    "spec", "readme", "changelog", "release notes",
    "wiki", "knowledge base", "kb", "faq",
    "getting started", "quick start", "tutorial",
    "configuration", "config", "setup", "installation",
    # Chinese
    "文档", "手册", "指南", "参考", "说明",
    "api文档", "接口文档", "配置", "安装",
    "入门", "快速开始", "教程", "wiki",
)

_SHOPPING_KEYWORDS = (
    # English
    "buy", "purchase", "shop", "shopping", "order",
    "price", "pricing", "cost", "cheap", "discount",
    "deal", "sale", "promo", "coupon", "offer",
    "amazon", "ebay", "aliexpress", "taobao", "jd",
    "best buy", "walmart", "target", "costco",
    "compare price", "price comparison", "where to buy",
    "recommendation", "best", "top rated", "review",
    # Chinese
    "购买", "买", "购物", "下单", "订购",
    "价格", "多少钱", "便宜", "优惠", "折扣",
    "淘宝", "京东", "拼多多", "亚马逊",
    "推荐", "评测", "对比", "哪个好",
)

_ALL_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "code": _CODE_KEYWORDS,
    "image": _IMAGE_KEYWORDS,
    "video": _VIDEO_KEYWORDS,
    "docs": _DOCS_KEYWORDS,
    "shopping": _SHOPPING_KEYWORDS,
}


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    text_l = f" {text.lower()} "
    return any(kw.lower() in text_l for kw in keywords if kw)


def detect_intent(query: str) -> IntentSignals:
    """Detect query intent from keyword signals.

    Returns an IntentSignals dataclass with boolean flags for each intent
    category, a primary_intent string, and confidence score.
    """
    text_l = f" {query.lower()} "
    matched: list[str] = []
    scores: dict[str, int] = {}

    for intent, keywords in _ALL_INTENT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw and kw.lower() in text_l)
        if count > 0:
            scores[intent] = count
            matched.append(intent)

    if not scores:
        return IntentSignals(primary_intent="general", confidence=0.0)

    # Primary intent = highest score
    primary = max(scores, key=lambda k: scores[k])
    total_signals = sum(scores.values())
    confidence = min(0.5 + 0.15 * scores[primary], 0.95)

    return IntentSignals(
        code="code" in scores,
        image="image" in scores,
        video="video" in scores,
        docs="docs" in scores,
        shopping="shopping" in scores,
        primary_intent=primary,
        confidence=round(confidence, 2),
        matched_keywords=tuple(matched),
    )


def get_intent_keywords(intent: str) -> tuple[str, ...]:
    """Get keyword set for a specific intent."""
    return _ALL_INTENT_KEYWORDS.get(intent, ())


def list_intents() -> list[str]:
    """Return all supported intent categories."""
    return list(_ALL_INTENT_KEYWORDS.keys())


# ── Provider recommendations by intent ───────────────────────────────────────

_INTENT_PROVIDER_MAP: dict[str, list[str]] = {
    "code": ["google", "tavily", "bing"],
    "image": ["bing", "google", "brave"],
    "video": ["google", "bing", "tavily"],
    "docs": ["tavily", "google", "perplexity"],
    "shopping": ["google", "bing", "brave"],
    "general": ["tavily", "exa", "duckduckgo"],
}


def recommend_providers_by_intent(
    intent: str,
    available_providers: Iterable[str] | None = None,
) -> list[str]:
    """Recommend providers for a given intent.

    Returns ordered list of provider names that support the intent,
    filtered by availability.
    """
    candidates = _INTENT_PROVIDER_MAP.get(intent, _INTENT_PROVIDER_MAP["general"])
    if available_providers is None:
        return candidates
    available = set(available_providers)
    return [p for p in candidates if p in available]


__all__ = [
    "IntentSignals",
    "detect_intent",
    "get_intent_keywords",
    "list_intents",
    "recommend_providers_by_intent",
]
