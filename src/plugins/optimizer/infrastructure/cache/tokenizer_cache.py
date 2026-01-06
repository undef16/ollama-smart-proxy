"""Tokenizer cache for repeated tokenization operations."""

from typing import Dict, Any
from .cache import BaseCache


class TokenizerCache(BaseCache):
    """LRU cache for tokenization results with size limits and TTL."""
    
    def __init__(self, max_size: int = 256, default_ttl: int = 900):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of tokenization results to cache
            default_ttl: Default time-to-live in seconds
        """
        super().__init__(max_size=max_size, default_ttl=default_ttl)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        stats = super().get_stats()
        stats['average_tokens_saved'] = self.hits * 0.75  # Estimate based on typical tokenization
        return stats
