"""Base LRU Cache with TTL support."""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Generic, TypeVar

T = TypeVar('T')

class BaseCache(Generic[T]):
    """Base LRU cache with TTL-based invalidation."""
    
    def __init__(self, max_size: int = 512, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, tuple[T, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[T]:
        """Get cached value if not expired."""
        with self._lock:
            if key in self.cache:
                value, expiration = self.cache[key]
                if time.time() < expiration:
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return value
                del self.cache[key]
                self.evictions += 1
            self.misses += 1
            return None
    
    def put(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """Cache a value with optional TTL."""
        with self._lock:
            expiration = time.time() + (ttl or self.default_ttl)
            if key in self.cache:
                del self.cache[key]
            self.cache[key] = (value, expiration)
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
                self.evictions += 1
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self.hits + self.misses
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': self.hits / total if total > 0 else 0,
                'evictions': self.evictions,
                'size': len(self.cache),
                'max_size': self.max_size
            }
    
    def get_many(self, keys: List[str]) -> Dict[str, T]:
        """Get multiple values."""
        return {k: v for k in keys if (v := self.get(k)) is not None}
    
    def put_many(self, items: Dict[str, T], ttl: Optional[int] = None) -> None:
        """Put multiple values."""
        for k, v in items.items():
            self.put(k, v, ttl)
