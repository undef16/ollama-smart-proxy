"""LRU Cache for frequently accessed templates."""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional
import logging


class TemplateCache:
    """LRU cache for frequently accessed templates with statistics tracking."""
    
    def __init__(self, max_size: int = 1024, default_ttl: int = 3600):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()  # OrderedDict for LRU eviction
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            if key in self.cache:
                cached_value, expiration, access_time = self.cache[key]
                current_time = time.time()
                
                if current_time < expiration:
                    # Move to end to mark as recently used (LRU)
                    self.cache.move_to_end(key)
                    self.hits += 1
                    self.logger.debug(f"Cache hit for key: {key}")
                    return cached_value
                else:
                    # Expired, remove from cache
                    del self.cache[key]
                    self.evictions += 1
                    self.logger.debug(f"Cache expired and evicted for key: {key}")
            
            self.misses += 1
            self.logger.debug(f"Cache miss for key: {key}")
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Cache a value with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            expiration = time.time() + (ttl or self.default_ttl)
            
            # If key exists, remove it first to update position
            if key in self.cache:
                del self.cache[key]
            
            # Add to cache
            self.cache[key] = (value, expiration, time.time())
            
            # Evict least recently used items if over capacity
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.evictions += 1
                self.logger.debug(f"LRU eviction for key: {oldest_key}")
    
    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.logger.debug(f"Cache invalidated for key: {key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'evictions': self.evictions,
                'size': len(self.cache),
                'max_size': self.max_size,
                'current_hit_rate': hit_rate
            }
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
            self.logger.info("Cache cleared")
    
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
