"""Query caching mechanism for database operations."""

import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class QueryCache:
    """LRU cache for database operations with TTL-based invalidation."""
    
    def __init__(self, max_size: int = 512, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()  # OrderedDict for LRU eviction
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        with self._lock:
            if key in self.cache:
                cached_value, expiration = self.cache[key]
                if datetime.now() < expiration:
                    # Move to end to mark as recently used (LRU)
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return cached_value
                else:
                    # Expired, remove from cache
                    del self.cache[key]
                    self.evictions += 1
            
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Cache a value with optional TTL."""
        with self._lock:
            # If key exists, remove it first to update position
            if key in self.cache:
                del self.cache[key]
            
            expiration = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            self.cache[key] = (value, expiration)
            
            # Evict least recently used items if over capacity
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.evictions += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'evictions': self.evictions,
                'size': len(self.cache),
                'max_size': self.max_size
            }
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from the cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of found key-value pairs
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    def put_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Put multiple values into the cache.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time-to-live in seconds
        """
        for key, value in items.items():
            self.put(key, value, ttl)
