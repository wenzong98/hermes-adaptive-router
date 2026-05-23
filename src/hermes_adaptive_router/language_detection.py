"""Lightweight language detection for query routing.

No external dependencies. Uses Unicode script ranges and keyword heuristics
to detect the primary language of a query.

Supported languages:
- English (en)
- Chinese (zh) — simplified & traditional
- Japanese (ja)
- Korean (ko)
- German (de)
- French (fr)
- Spanish (es)
- Russian (ru)
- Arabic (ar)
- Portuguese (pt)
- Italian (it)
- Dutch (nl)
- Turkish (tr)
- Vietnamese (vi)
- Thai (th)
- Hindi (hi)

Usage:
    detect_language("最新AI新闻")  # -> "zh"
    detect_language("Hello world")  # -> "en"
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


# ── Unicode script ranges ────────────────────────────────────────────────────

_CJK_RE = re.compile(
    "[\u4e00-\u9fff\u3400-\u4dbf"
    "\U00020000-\U0002a6df]",
    re.UNICODE,
)
_HIRAGANA_RE = re.compile("[\u3040-\u309f]", re.UNICODE)
_KATAKANA_RE = re.compile("[\u30a0-\u30ff]", re.UNICODE)
_HANGUL_RE = re.compile("[\uac00-\ud7af\u1100-\u11ff]", re.UNICODE)
_CYRILLIC_RE = re.compile("[\u0400-\u04ff]", re.UNICODE)
_ARABIC_RE = re.compile("[\u0600-\u06ff\u0750-\u077f]", re.UNICODE)
_THAI_RE = re.compile("[\u0e00-\u0e7f]", re.UNICODE)
_DEVANAGARI_RE = re.compile("[\u0900-\u097f]", re.UNICODE)
_LATIN_RE = re.compile("[a-zA-Z]", re.UNICODE)

# Language-specific character detection
_SCRIPT_DETECTORS: dict[str, tuple[re.Pattern, float]] = {
    "zh": (_CJK_RE, 1.0),       # CJK Unified Ideographs
    "ja": (_HIRAGANA_RE, 0.8),  # Hiragana (strong Japanese signal)
    "ko": (_HANGUL_RE, 1.0),    # Hangul
    "ru": (_CYRILLIC_RE, 1.0),  # Cyrillic
    "ar": (_ARABIC_RE, 1.0),    # Arabic
    "th": (_THAI_RE, 1.0),      # Thai
    "hi": (_DEVANAGARI_RE, 1.0), # Devanagari (Hindi)
}

# Japanese also has Katakana (secondary signal)
_JA_SECONDARY = (_KATAKANA_RE, 0.5)


# ── Language-specific keywords for disambiguation ────────────────────────────

_LANGUAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "en": (
        "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "can", "shall",
    ),
    "zh": (
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
        "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
        "你", "会", "着", "没有", "看", "好", "自己", "这",
    ),
    "ja": (
        "の", "に", "は", "を", "た", "が", "で", "て", "と", "し",
        "れ", "さ", "ある", "いる", "も", "する", "から", "な",
        "こと", "として", "い", "や", "れる", "など", "なっ",
    ),
    "ko": (
        "은", "는", "이", "가", "을", "를", "의", "에", "으로",
        "하고", "이다", "있", "하", "되", "않", "없", "나",
        "우리", "그", "저", "이", "것", "수", "등",
    ),
    "de": (
        "der", "die", "das", "und", "ist", "von", "mit", "für",
        "auf", "nicht", "ein", "eine", "als", "auch", "sich",
        "dem", "den", "zu", "bei", "nach", "wie", "im",
    ),
    "fr": (
        "le", "la", "les", "un", "une", "des", "et", "est",
        "dans", "pour", "par", "sur", "avec", "que", "qui",
        "ce", "cette", "son", "sa", "ses", "ne", "pas",
    ),
    "es": (
        "el", "la", "los", "las", "un", "una", "y", "es",
        "en", "por", "para", "con", "de", "del", "al",
        "se", "su", "lo", "como", "más", "pero", "sus",
    ),
    "ru": (
        "в", "и", "не", "на", "я", "быть", "он", "с", "что",
        "а", "по", "это", "она", "к", "но", "мы", "как",
        "из", "у", "то", "за", "свой", "ее", "о",
    ),
    "pt": (
        "o", "a", "os", "as", "um", "uma", "e", "é", "de",
        "em", "para", "com", "por", "se", "mas", "que",
        "não", "uma", "ele", "ela", "seu", "sua",
    ),
    "it": (
        "il", "la", "i", "le", "un", "una", "e", "è", "di",
        "in", "per", "con", "su", "da", "non", "che", "chi",
        "mi", "ti", "lo", "gli", "nel", "del",
    ),
    "nl": (
        "de", "het", "een", "en", "van", "is", "voor", "op",
        "met", "zijn", "te", "dat", "door", "over", "ze",
        "zich", "bij", "maar", "om", "naar", "uit",
    ),
    "tr": (
        "ve", "bir", "için", "bu", "mi", "ile", "de", "da",
        "a", "e", "in", "nın", "nın", "nin", "nun",
        "olarak", "kadar", "gibi", "sonra", "her",
    ),
    "vi": (
        "củ", "và", "là", "có", "được", "không", "ngườ", "này",
        "cho", "trong", "một", "đến", "với", "để", "về",
        "nhưng", "cũng", "hay", "tại", "theo",
    ),
}


# ── Provider preferences by language ─────────────────────────────────────────

_LANGUAGE_PROVIDER_MAP: dict[str, list[str]] = {
    "zh": ["mmx", "tavily", "google", "bing"],
    "ja": ["google", "tavily", "bing"],
    "ko": ["google", "tavily", "bing"],
    "en": ["tavily", "exa", "google", "bing", "perplexity"],
    "de": ["google", "bing", "tavily"],
    "fr": ["google", "bing", "tavily"],
    "es": ["google", "bing", "tavily"],
    "ru": ["google", "bing", "tavily"],
    "ar": ["google", "bing", "tavily"],
    "pt": ["google", "bing", "tavily"],
    "it": ["google", "bing", "tavily"],
    "nl": ["google", "bing", "tavily"],
    "tr": ["google", "bing", "tavily"],
    "vi": ["google", "bing", "tavily"],
    "th": ["google", "bing", "tavily"],
    "hi": ["google", "bing", "tavily"],
}


@dataclass(frozen=True)
class LanguageResult:
    """Language detection result."""

    language: str           # ISO 639-1 code or "unknown"
    confidence: float       # 0.0 - 1.0
    script: str             # Detected script family
    is_multilingual: bool   # Multiple strong signals detected


def detect_language(query: str) -> LanguageResult:
    """Detect the primary language of a query.

    Uses a multi-layer approach:
    1. Unicode script detection (strongest signal)
    2. Keyword frequency analysis
    3. Fallback to "en" if Latin script dominates

    Returns LanguageResult with language code, confidence, and script.
    """
    text = query.strip()
    if not text:
        return LanguageResult("unknown", 0.0, "none", False)

    total_chars = len(text)
    if total_chars == 0:
        return LanguageResult("unknown", 0.0, "none", False)

    # Layer 1: Unicode script detection
    script_scores: dict[str, float] = {}

    for lang, (pattern, weight) in _SCRIPT_DETECTORS.items():
        count = len(pattern.findall(text))
        if count > 0:
            ratio = count / total_chars
            script_scores[lang] = max(script_scores.get(lang, 0.0), ratio * weight)

    # Japanese secondary signal (Katakana)
    ja_kata_count = len(_JA_SECONDARY[0].findall(text))
    if ja_kata_count > 0:
        ja_score = script_scores.get("ja", 0.0)
        script_scores["ja"] = ja_score + (ja_kata_count / total_chars) * _JA_SECONDARY[1]

    # Layer 2: Keyword frequency analysis (for Latin-script languages)
    keyword_scores: dict[str, float] = {}
    text_l = f" {text.lower()} "

    for lang, keywords in _LANGUAGE_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw and f" {kw.lower()} " in text_l)
        if matches > 0:
            keyword_scores[lang] = matches / max(len(keywords), 1)

    # Layer 3: Combine scores
    combined: dict[str, float] = {}

    # Script scores dominate
    for lang, score in script_scores.items():
        combined[lang] = combined.get(lang, 0.0) + score * 0.7

    # Keyword scores supplement
    for lang, score in keyword_scores.items():
        combined[lang] = combined.get(lang, 0.0) + score * 0.3

    if not combined:
        # Fallback: if mostly Latin characters, assume English
        latin_count = len(_LATIN_RE.findall(text))
        if latin_count / total_chars > 0.5:
            return LanguageResult("en", 0.3, "latin", False)
        return LanguageResult("unknown", 0.0, "mixed", False)

    # Find primary language
    primary = max(combined, key=lambda k: combined[k])
    primary_score = combined[primary]

    # Check for multilingual ambiguity
    sorted_scores = sorted(combined.values(), reverse=True)
    is_multilingual = len(sorted_scores) > 1 and sorted_scores[0] - sorted_scores[1] < 0.15

    # Determine script family
    script = _get_script_family(primary)

    confidence = min(primary_score * 1.5, 0.95)
    if confidence < 0.2:
        confidence = 0.2

    return LanguageResult(
        language=primary,
        confidence=round(confidence, 2),
        script=script,
        is_multilingual=is_multilingual,
    )


def _get_script_family(lang: str) -> str:
    """Map language code to script family."""
    script_map = {
        "zh": "cjk",
        "ja": "cjk",
        "ko": "cjk",
        "ru": "cyrillic",
        "ar": "arabic",
        "th": "thai",
        "hi": "devanagari",
    }
    return script_map.get(lang, "latin")


def get_language_name(code: str) -> str:
    """Get human-readable language name from ISO code."""
    names = {
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "ru": "Russian",
        "ar": "Arabic",
        "pt": "Portuguese",
        "it": "Italian",
        "nl": "Dutch",
        "tr": "Turkish",
        "vi": "Vietnamese",
        "th": "Thai",
        "hi": "Hindi",
        "unknown": "Unknown",
    }
    return names.get(code, code)


def recommend_providers_by_language(
    language: str,
    available_providers: Iterable[str] | None = None,
) -> list[str]:
    """Recommend providers for a given language.

    Returns ordered list of provider names, filtered by availability.
    """
    candidates = _LANGUAGE_PROVIDER_MAP.get(language, _LANGUAGE_PROVIDER_MAP.get("en", ["tavily"]))
    if available_providers is None:
        return candidates
    available = set(available_providers)
    return [p for p in candidates if p in available]


def is_cjk(query: str) -> bool:
    """Quick check if query contains CJK characters."""
    return bool(_CJK_RE.search(query))


def is_latin(query: str) -> bool:
    """Quick check if query is primarily Latin script."""
    text = query.strip()
    if not text:
        return False
    latin_count = len(_LATIN_RE.findall(text))
    return latin_count / len(text) > 0.5


__all__ = [
    "LanguageResult",
    "detect_language",
    "get_language_name",
    "is_cjk",
    "is_latin",
    "recommend_providers_by_language",
]
