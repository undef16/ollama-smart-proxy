"""Fingerprint cache for computed fingerprints."""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional
import logging


class FingerprintCache:
    """LRU cache for computed fingerprints with TTL-based invalidation."""
    
    def __init__(self, max_size: int = 512, default_ttl: int = 1800):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of fingerprints to cache
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
        
    def get(self, text_hash: str) -> Optional[Dict[int, int]]:
        """Get cached fingerprints for a text hash.
        
        Args:
            text_hash: Hash of the text to look up
            
        Returns:
            Dictionary of fingerprints or None if not found/expired
        """
        with self._lock:
            if text_hash in self.cache:
                fingerprints, expiration = self.cache[text_hash]
                current_time = time.time()
                
                if current_time < expiration:
                    # Move to end to mark as recently used (LRU)
                    self.cache.move_to_end(text_hash)
                    self.hits += 1
                    self.logger.debug(f"Fingerprint cache hit for hash: {text_hash[:8]}...")
                    return fingerprints
                else:
                    # Expired, remove from cache
                    del self.cache[text_hash]
                    self.evictions += 1
                    self.logger.debug(f"Fingerprint cache expired for hash: {text_hash[:8]}...")
            
            self.misses += 1
            self.logger.debug(f"Fingerprint cache miss for hash: {text_hash[:8]}...")
            return None
    
    def put(self, text_hash: str, fingerprints: Dict[int, int], ttl: Optional[int] = None) -> None:
        """Cache fingerprints for a text hash.
        
        Args:
            text_hash: Hash of the text
            fingerprints: Dictionary of fingerprints to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            expiration = time.time() + (ttl or self.default_ttl)
            
            # If text_hash exists, remove it first to update position
            if text_hash in self.cache:
                del self.cache[text_hash]
            
            # Add to cache
            self.cache[text_hash] = (fingerprints, expiration)
            
            # Evict least recently used items if over capacity
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.evictions += 1
                self.logger.debug(f"Fingerprint cache LRU eviction for hash: {oldest_key[:8]}...")
    
    def invalidate_all(self) -> None:
        """Invalidate all cached fingerprints (e.g., on template updates)."""
        with self._lock:
            self.cache.clear()
            self.logger.info("All fingerprint cache entries invalidated")
    
    def invalidate(self, text_hash: str) -> None:
        """Invalidate a specific fingerprint cache entry.
        
        Args:
            text_hash: Hash of the text to invalidate
        """
        with self._lock:
            if text_hash in self.cache:
                del self.cache[text_hash]
                self.logger.debug(f"Fingerprint cache invalidated for hash: {text_hash[:8]}...")
    
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
            self.logger.info("Fingerprint cache cleared")
    
    def get_many(self, keys: List[str]) -> Dict[str, Dict[int, int]]:
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
    
    def put_many(self, items: Dict[str, Dict[int, int]], ttl: Optional[int] = None) -> None:
        """Put multiple values into the cache.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time-to-live in seconds
        """
        for key, value in items.items():
            self.put(key, value, ttl)
