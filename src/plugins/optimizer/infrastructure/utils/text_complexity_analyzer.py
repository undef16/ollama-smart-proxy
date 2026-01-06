"""Text complexity analysis for adaptive SimHash resolution selection."""

import logging
import re
import threading
import time
from collections import OrderedDict
from typing import List, Dict, Optional


class TextComplexityAnalyzer:
    """Analyzes text complexity to determine optimal SimHash resolutions."""

    # Pre-compiled regex patterns - single combined patterns where possible
    _WORD_PATTERN = re.compile(r'\b\w+\b')
    _PUNCTUATION_PATTERN = re.compile(r'[.,;:!?\-()\[\]{}"\'\\/]')
    
    # Combined code detection pattern (matches all code patterns in single pass)
    _CODE_PATTERNS_COMBINED = re.compile(
        r'\b(import|from|def|class|return|if|else|for|while|try|except|finally|with|lambda)\b|'
        r'\b(true|false|null|undefined|None)\b|'
        r'[{};()<>=\[\]]|'
        r'\.[a-zA-Z_]+|'
        r'"[^"]*"|'
        r'\'[^\']*\''
    )

    def __init__(self, cache_size: int = 256, cache_ttl: float = 300.0):
        """Initialize the text complexity analyzer.
        
        Args:
            cache_size: Maximum number of cached analysis results
            cache_ttl: Time-to-live for cached results in seconds (default: 5 minutes)
        """
        self.logger = logging.getLogger(__name__)
        
        # Complexity metrics weights
        self.weights = {
            'length': 0.3,
            'word_count': 0.2,
            'unique_words': 0.2,
            'avg_word_length': 0.1,
            'punctuation_density': 0.1,
            'code_content': 0.1
        }
        
        # Caching for analyze_text results
        self._analysis_cache: 'OrderedDict[int, tuple[Dict[str, float], float]]' = OrderedDict()
        self._cache_lock = threading.Lock()
        self._cache_size = cache_size
        self._cache_ttl = cache_ttl

    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze text complexity across multiple dimensions.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary of complexity metrics
        """
        # Fast path for empty or whitespace-only text
        if not text or not text.strip():
            return {
                'length': 0.0,
                'word_count': 0.0,
                'unique_words': 0.0,
                'avg_word_length': 0.0,
                'punctuation_density': 0.0,
                'code_content': 0.0,
                'complexity_score': 0.0
            }

        # Check cache first
        cache_key = hash(text)
        now = time.time()
        with self._cache_lock:
            if cache_key in self._analysis_cache:
                cached_value, expiration = self._analysis_cache[cache_key]
                if now < expiration:
                    # Move to end (most recently used)
                    self._analysis_cache.move_to_end(cache_key)
                    return cached_value
        
        # Perform analysis
        result = self._analyze_text_impl(text)
        
        # Cache result
        with self._cache_lock:
            # Evict oldest entry if cache is full
            if len(self._analysis_cache) >= self._cache_size:
                self._analysis_cache.popitem(last=False)
            self._analysis_cache[cache_key] = (result, now + self._cache_ttl)
        
        return result

    def _analyze_text_impl(self, text: str) -> Dict[str, float]:
        """Internal implementation of text analysis without caching.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary of complexity metrics
        """
        # Basic metrics
        length = len(text)
        words = self._WORD_PATTERN.findall(text.lower())
        word_count = len(words)
        
        # Use set for unique word counting (more efficient)
        words_set = set(words)
        unique_words = len(words_set)
        unique_word_ratio = unique_words / word_count if word_count > 0 else 0
        
        # Average word length - use generator to avoid creating intermediate list
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        
        # Punctuation density
        punctuation_count = len(self._PUNCTUATION_PATTERN.findall(text))
        punctuation_density = punctuation_count / length if length > 0 else 0
        
        # Code content detection - single pass with combined pattern
        code_matches = len(self._CODE_PATTERNS_COMBINED.findall(text))
        code_content_score = min(code_matches / word_count, 1.0) if word_count > 0 else 0
        
        # Normalize metrics to 0-1 range
        normalized_metrics = {
            'length': min(length / 10000, 1.0),  # Cap at 10k characters
            'word_count': min(word_count / 2000, 1.0),  # Cap at 2k words
            'unique_words': unique_word_ratio,
            'avg_word_length': min(avg_word_length / 15, 1.0),  # Cap at 15 chars per word
            'punctuation_density': min(punctuation_density * 10, 1.0),  # Scale up
            'code_content': code_content_score
        }
        
        # Calculate overall complexity score
        complexity_score = sum(
            normalized_metrics[metric] * self.weights[metric] 
            for metric in self.weights
        )
        
        normalized_metrics['complexity_score'] = complexity_score
        
        self.logger.debug(f"Text complexity analysis: {normalized_metrics}")
        
        return normalized_metrics

    def get_adaptive_resolutions(self, text: str, default_resolutions: Optional[List[int]] = None) -> List[int]:
        """Determine optimal SimHash resolutions based on text complexity.
        
        Args:
            text: Input text to analyze
            default_resolutions: Default resolutions to use as baseline
            
        Returns:
            List of optimal resolutions for this text
        """
        if default_resolutions is None:
            from ..const import DEFAULT_RESOLUTIONS
            default_resolutions = DEFAULT_RESOLUTIONS
        
        metrics = self.analyze_text(text)
        complexity_score = metrics['complexity_score']
        
        # Adaptive resolution selection based on complexity
        if complexity_score < 0.3:
            # Low complexity text - use fewer, smaller resolutions
            resolutions = [res for res in default_resolutions if res <= 256]
            if len(resolutions) < 2:
                resolutions = [64, 128]
        elif complexity_score < 0.6:
            # Medium complexity text - use middle range resolutions
            resolutions = [res for res in default_resolutions if res <= 512]
            if len(resolutions) < 3:
                resolutions = [64, 128, 256]
        else:
            # High complexity text - use all resolutions
            resolutions = default_resolutions.copy()
        
        self.logger.info(
            f"Adaptive resolution selection: complexity={complexity_score:.3f}, "
            f"resolutions={resolutions}"
        )
        
        return resolutions

    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        with self._cache_lock:
            self._analysis_cache.clear()
        self.logger.debug("Analysis cache cleared")
