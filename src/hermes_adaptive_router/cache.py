"""LRU cache for routing decisions.

Caches query -> route decisions to avoid recomputing for identical or
near-identical queries. Uses a normalized query key (lowercased, whitespace
collapsed) for cache lookups.

Features:
- TTL-based expiration (default 1 hour)
- Thread-safe operations
- Configurable max size
- Cache hit/miss statistics
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    """Internal cache entry with TTL."""

    key: str
    value: T
    timestamp: float
    hit_count: int = 0


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    ttl_seconds: float = 0.0
    hit_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hit_rate": round(self.hit_rate, 4),
        }


class RoutingCache:
    """Thread-safe LRU cache for routing decisions.

    Usage:
        cache = RoutingCache(max_size=1000, ttl_seconds=3600)

        # Check cache
        result = cache.get("latest news")
        if result is not None:
            return result

        # Compute and store
        decision = classify_query("latest news")
        cache.set("latest news", decision)
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float = 3600.0,
    ) -> None:
        self._max_size = max(max_size, 1)
        self._ttl = max(ttl_seconds, 0.0)
        self._cache: dict[str, _CacheEntry[Any]] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=self._max_size, ttl_seconds=self._ttl)
        self._access_order: list[str] = []  # LRU: most recent at end

    def _normalize_key(self, query: str) -> str:
        """Normalize query for cache key."""
        # Lowercase, collapse whitespace, strip
        normalized = query.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _is_expired(self, entry: _CacheEntry[Any]) -> bool:
        """Check if a cache entry has expired."""
        if self._ttl <= 0:
            return False
        return (time.time() - entry.timestamp) > self._ttl

    def _evict_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired_keys = [
            k for k, e in self._cache.items()
            if self._ttl > 0 and (now - e.timestamp) > self._ttl
        ]
        for k in expired_keys:
            del self._cache[k]
            if k in self._access_order:
                self._access_order.remove(k)
            self._stats.evictions += 1

    def _evict_lru(self) -> None:
        """Evict least recently used entry when cache is full."""
        while len(self._cache) >= self._max_size and self._access_order:
            oldest = self._access_order.pop(0)
            if oldest in self._cache:
                del self._cache[oldest]
                self._stats.evictions += 1

    def get(self, query: str) -> Any | None:
        """Get cached decision for a query.

        Returns None if not found or expired.
        """
        key = self._normalize_key(query)

        with self._lock:
            self._evict_expired()

            entry = self._cache.get(key)
            if entry is None:
                self._stats.misses += 1
                self._update_hit_rate()
                return None

            if self._is_expired(entry):
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats.misses += 1
                self._stats.evictions += 1
                self._update_hit_rate()
                return None

            # Update access order (move to end = most recent)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            entry.hit_count += 1
            self._stats.hits += 1
            self._update_hit_rate()
            return entry.value

    def set(self, query: str, value: Any) -> None:
        """Store a routing decision in the cache."""
        key = self._normalize_key(query)

        with self._lock:
            self._evict_expired()

            # Evict LRU if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()

            self._cache[key] = _CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
            )

            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            self._stats.size = len(self._cache)

    def invalidate(self, query: str) -> bool:
        """Remove a specific query from cache.

        Returns True if the entry was found and removed.
        """
        key = self._normalize_key(query)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats.size = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats.size = 0

    def get_stats(self) -> CacheStats:
        """Return cache statistics."""
        with self._lock:
            self._stats.size = len(self._cache)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size,
                max_size=self._max_size,
                ttl_seconds=self._ttl,
                hit_rate=self._stats.hit_rate,
            )

    def _update_hit_rate(self) -> None:
        """Recalculate hit rate."""
        total = self._stats.hits + self._stats.misses
        if total > 0:
            self._stats.hit_rate = self._stats.hits / total

    def __len__(self) -> int:
        """Return current cache size."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, query: str) -> bool:
        """Check if a query is in the cache (not expired)."""
        return self.get(query) is not None


# Global default cache instance
_DEFAULT_CACHE: Optional[RoutingCache] = None


def get_default_cache() -> RoutingCache:
    """Get or create the global default cache."""
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        _DEFAULT_CACHE = RoutingCache(max_size=1000, ttl_seconds=3600.0)
    return _DEFAULT_CACHE


def set_default_cache(cache: Optional[RoutingCache]) -> None:
    """Set or clear the global default cache."""
    global _DEFAULT_CACHE
    _DEFAULT_CACHE = cache


def cached_classify(
    classify_fn: Callable[..., T],
    cache: Optional[RoutingCache] = None,
) -> Callable[..., T]:
    """Decorator/wrapper to cache classify function results.

    Usage:
        from hermes_adaptive_router.router import classify_query
        from hermes_adaptive_router.cache import cached_classify

        cached_classify_query = cached_classify(classify_query)
        result = cached_classify_query("latest news")  # cache miss
        result = cached_classify_query("latest news")  # cache hit
    """
    _cache = cache or get_default_cache()

    def wrapper(query: str, *args: Any, **kwargs: Any) -> T:
        # Try cache first
        cached = _cache.get(query)
        if cached is not None:
            return cached

        # Compute and cache
        result = classify_fn(query, *args, **kwargs)
        _cache.set(query, result)
        return result

    return wrapper


__all__ = [
    "CacheStats",
    "RoutingCache",
    "cached_classify",
    "get_default_cache",
    "set_default_cache",
]
