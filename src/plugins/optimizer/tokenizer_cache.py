"""Tokenizer cache for repeated tokenization operations."""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional
import logging


class TokenizerCache:
    """LRU cache for tokenization results with size limits and TTL."""
    
    def __init__(self, max_size: int = 256, default_ttl: int = 900):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of tokenization results to cache
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
        
    def get(self, text_hash: str) -> Optional[List[str]]:
        """Get cached tokens for a text hash.
        
        Args:
            text_hash: Hash of the text to look up
            
        Returns:
            List of tokens or None if not found/expired
        """
        with self._lock:
            if text_hash in self.cache:
                tokens, expiration = self.cache[text_hash]
                current_time = time.time()
                
                if current_time < expiration:
                    # Move to end to mark as recently used (LRU)
                    self.cache.move_to_end(text_hash)
                    self.hits += 1
                    self.logger.debug(f"Tokenizer cache hit for hash: {text_hash[:8]}...")
                    return tokens
                else:
                    # Expired, remove from cache
                    del self.cache[text_hash]
                    self.evictions += 1
                    self.logger.debug(f"Tokenizer cache expired for hash: {text_hash[:8]}...")
            
            self.misses += 1
            self.logger.debug(f"Tokenizer cache miss for hash: {text_hash[:8]}...")
            return None
    
    def put(self, text_hash: str, tokens: List[str], ttl: Optional[int] = None) -> None:
        """Cache tokenization results for a text hash.
        
        Args:
            text_hash: Hash of the text
            tokens: List of tokens to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            expiration = time.time() + (ttl or self.default_ttl)
            
            # If text_hash exists, remove it first to update position
            if text_hash in self.cache:
                del self.cache[text_hash]
            
            # Add to cache
            self.cache[text_hash] = (tokens, expiration)
            
            # Evict least recently used items if over capacity
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.evictions += 1
                self.logger.debug(f"Tokenizer cache LRU eviction for hash: {oldest_key[:8]}...")
    
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
                'current_hit_rate': hit_rate,
                'average_tokens_saved': self.hits * 0.75  # Estimate based on typical tokenization
            }
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
            self.logger.info("Tokenizer cache cleared")
    
    def get_many(self, keys: List[str]) -> Dict[str, List[str]]:
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
    
    def put_many(self, items: Dict[str, List[str]], ttl: Optional[int] = None) -> None:
        """Put multiple values into the cache.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time-to-live in seconds
        """
        for key, value in items.items():
            self.put(key, value, ttl)
