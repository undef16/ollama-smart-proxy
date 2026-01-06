"""Query caching mechanism for database operations."""

from .cache import BaseCache


class QueryCache(BaseCache):
    """LRU cache for database operations with TTL-based invalidation."""
    
    def __init__(self, max_size: int = 512, default_ttl: int = 300):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        super().__init__(max_size=max_size, default_ttl=default_ttl)
