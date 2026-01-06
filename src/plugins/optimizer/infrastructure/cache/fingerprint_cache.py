"""Fingerprint cache for computed fingerprints."""

from typing import Dict
from .cache import BaseCache


class FingerprintCache(BaseCache[Dict[int, int]]):
    """LRU cache for computed fingerprints with TTL-based invalidation."""
    
    def __init__(self, max_size: int = 512, default_ttl: int = 1800):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of fingerprints to cache
            default_ttl: Default time-to-live in seconds
        """
        super().__init__(max_size=max_size, default_ttl=default_ttl)
    
    def invalidate_all(self) -> None:
        """Invalidate all cached fingerprints (e.g., on template updates)."""
        self.clear()
    
    def invalidate(self, text_hash: str) -> None:
        """Invalidate a specific fingerprint cache entry.
        
        Args:
            text_hash: Hash of the text to invalidate
        """
        with self._lock:
            if text_hash in self.cache:
                del self.cache[text_hash]
