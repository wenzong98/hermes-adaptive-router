"""Hermes integration helpers.

These adapters let hermes-agent consume hermes-adaptive-router without
hard-coding the router into the agent codebase.  They are optional glue.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from hermes_adaptive_router.router import (
    AdaptiveQueryRoutingConfig,
    QueryRoute,
    build_adaptive_query_routing_prompt,
    classify_query,
    load_adaptive_query_routing_config,
)


def _load_hermes_raw_config() -> Mapping[str, Any]:
    """Best-effort Hermes config loader kept out of the core router layer."""
    try:
        from hermes_cli.config import load_config

        config = load_config()
    except Exception:
        return {}
    return config if isinstance(config, Mapping) else {}


def classify_for_hermes(
    query: str,
    *,
    available_tools: Optional[Iterable[str]] = None,
    raw_config: Optional[Mapping[str, Any]] = None,
) -> QueryRoute:
    """Classify a query using Hermes-style tool names.

    ``available_tools`` should be the set of tool names the current agent
    session has registered (e.g. ``{"web_search", "web_extract"}``).
    """
    cfg = load_adaptive_query_routing_config(raw_config if raw_config is not None else _load_hermes_raw_config())
    return classify_query(query, cfg, available_tools=available_tools)


def get_system_prompt_addition(
    available_tools: Iterable[str],
    *,
    raw_config: Optional[Mapping[str, Any]] = None,
) -> str:
    """Return the adaptive-routing paragraph to append to the system prompt.

    Returns empty string when routing is disabled or no web tools are loaded.
    """
    cfg = load_adaptive_query_routing_config(raw_config if raw_config is not None else _load_hermes_raw_config())
    return build_adaptive_query_routing_prompt(available_tools, cfg)


def tavily_search_payload_override(
    payload: dict[str, Any],
    *,
    raw_config: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Mutate a Tavily search payload based on adaptive routing config.

    If ``prefer_search_summary`` is enabled and ``tavily_answer`` is set,
    this adds ``include_answer`` (and ``search_depth`` for ``advanced``).
    """
    cfg = load_adaptive_query_routing_config(raw_config if raw_config is not None else _load_hermes_raw_config())
    if not cfg.enabled or not cfg.prefer_search_summary:
        return payload

    if cfg.tavily_answer:
        payload["include_answer"] = cfg.tavily_answer
        if str(cfg.tavily_answer).lower() == "advanced":
            payload["search_depth"] = "advanced"
    return payload


__all__ = [
    "classify_for_hermes",
    "get_system_prompt_addition",
    "tavily_search_payload_override",
]
