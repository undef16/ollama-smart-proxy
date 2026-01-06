"""LRU Cache for frequently accessed templates."""

from .cache import BaseCache


class TemplateCache(BaseCache):
    """LRU cache for frequently accessed templates with statistics tracking."""
    
    def __init__(self, max_size: int = 1024, default_ttl: int = 3600):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        super().__init__(max_size=max_size, default_ttl=default_ttl)
    
    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
