"""SimHash utilities for prompt template detection."""

import hashlib
import logging
import time
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import threading

from ...ports.template_repository import TemplateRepository
from ...domain.template import Template
from ...const import (
    HASH_BYTES,
    HASHBITS,
    DEFAULT_RESOLUTIONS,
    MAX_TOKENS,
    TOKEN_REGEX,
    SHINGLE_SIZE,
    THRESHOLD_DIVISOR,
    HASH_SLICE,
    DEFAULT_THRESHOLDS,
)
from .template_utils import TemplateUtils

# Import cache classes (avoid circular imports by using forward references)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..cache.tokenizer_cache import TokenizerCache
    from ..cache.fingerprint_cache import FingerprintCache
    from ..cache.template_cache import TemplateCache

# Import TextComplexityAnalyzer for runtime use
from .text_complexity_analyzer import TextComplexityAnalyzer

# Try to import NumPy for vectorized operations (optional dependency)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Try to import xxhash for faster hashing (optional dependency)
try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False


class SimHash:
    """SimHash implementation for text similarity detection."""

    def __init__(self, tokens: List[str], hashbits: int = HASHBITS):
        """Compute SimHash fingerprint for a list of tokens.

        Args:
            tokens: List of token strings
            hashbits: Number of bits for the fingerprint (64, 128, etc.)
        """
        self.hashbits = hashbits
        self.fingerprint = self._compute_fingerprint(tokens)

    @staticmethod
    def _hash_token_fast(token: str, hashbits: int) -> int:
        """Hash a single token using the fastest available method.

        Args:
            token: Token string to hash
            hashbits: Number of bits for the hash

        Returns:
            Hash value as integer
        """
        if XXHASH_AVAILABLE:
            # xxhash is 10-100x faster than MD5 for non-cryptographic use
            # Use xxhash64 for 64-bit hash, then truncate if needed
            h = xxhash.xxh64(token.encode("utf-8")).digest()[:HASH_BYTES]
        else:
            # Fallback to MD5
            h = hashlib.md5(token.encode("utf-8")).digest()[:HASH_BYTES]

        # Convert to int
        token_hash = int.from_bytes(h, byteorder="big")
        # Truncate to hashbits
        return token_hash & ((1 << hashbits) - 1)

    @staticmethod
    def _compute_fingerprint_numpy(tokens: List[str], hashbits: int) -> int:
        """Compute SimHash fingerprint using NumPy for vectorized operations.

        Args:
            tokens: List of token strings
            hashbits: Number of bits for the fingerprint

        Returns:
            Fingerprint as integer
        """
        if not tokens:
            return 0

        # Initialize vector with zeros using NumPy
        v = np.zeros(hashbits, dtype=np.int32)

        # Process all tokens
        for token in tokens:
            token_hash = SimHash._hash_token_fast(token, hashbits)

            # Vectorized bit extraction and accumulation
            # For each bit position i: if bit is 1, add +1; if bit is 0, add -1
            # This can be done by: (bits * 2 - 1)
            # where bits is an array of 0s and 1s
            bits = np.array([((token_hash >> i) & 1) for i in range(hashbits)], dtype=np.int32)
            v += (bits * 2 - 1)

        # Convert vector to fingerprint
        # Bits >= 0 become 1, bits < 0 become 0
        # Use vectorized operation: fingerprint = sum(1 << i for i where v[i] >= 0)
        mask = v >= 0
        fingerprint = np.sum(mask * (1 << np.arange(hashbits, dtype=np.uint64))).astype(np.uint64)

        return int(fingerprint)

    @staticmethod
    def _compute_fingerprint_fallback(tokens: List[str], hashbits: int) -> int:
        """Compute SimHash fingerprint using pure Python (fallback).

        Args:
            tokens: List of token strings
            hashbits: Number of bits for the fingerprint

        Returns:
            Fingerprint as integer
        """
        if not tokens:
            return 0

        # Initialize vector
        v = [0] * hashbits

        # Process each token
        for token in tokens:
            token_hash = SimHash._hash_token_fast(token, hashbits)

            # Add to vector (1 for set bits, -1 for unset)
            for i in range(hashbits):
                bit = (token_hash >> i) & 1
                v[i] += 1 if bit else -1

        # Convert to fingerprint
        fingerprint = 0
        for i in range(hashbits):
            if v[i] >= 0:
                fingerprint |= 1 << i

        return fingerprint


    @staticmethod
    def _hash_token(token: str, hashbits: int) -> int:
        """Hash a single token to a bit vector.

        Note: For better performance, use _hash_token_fast() which supports xxhash.
        """
        return SimHash._hash_token_fast(token, hashbits)

    def _compute_fingerprint(self, tokens: List[str]) -> int:
        """Compute SimHash fingerprint using the fastest available method.

        Uses NumPy for vectorized operations if available, otherwise falls back
        to optimized pure Python implementation.
        """
        if NUMPY_AVAILABLE:
            return SimHash._compute_fingerprint_numpy(tokens, self.hashbits)
        else:
            return SimHash._compute_fingerprint_fallback(tokens, self.hashbits)

    @staticmethod
    def hamming_distance(fp1: int, fp2: int) -> int:
        """Calculate Hamming distance between two fingerprints.

        Uses Python 3.8+ int.bit_count() for optimal performance.
        """
        return (fp1 ^ fp2).bit_count()

    @staticmethod
    def similarity(fp1: int, fp2: int, hashbits: int) -> float:
        """Calculate similarity score (0.0 to 1.0)."""
        distance = SimHash.hamming_distance(fp1, fp2)
        return 1.0 - (distance / hashbits)


class MultiResolutionSimHash:
    """Multi-resolution SimHash for template detection."""

    def __init__(self, resolutions: Optional[List[int]] = None, tokenizer_cache: Optional['TokenizerCache'] = None, fingerprint_cache: Optional['FingerprintCache'] = None, complexity_analyzer: Optional['TextComplexityAnalyzer'] = None):
        """Initialize with list of resolutions (token counts)."""
        self.resolutions = resolutions or DEFAULT_RESOLUTIONS.copy()
        self.tokenizer_cache = tokenizer_cache
        self.fingerprint_cache = fingerprint_cache
        self.complexity_analyzer = complexity_analyzer or TextComplexityAnalyzer()
        self.use_parallel = True  # Enable parallel computation by default
        self._thread_pool_lock = threading.Lock()
        self._max_workers = 4  # Default thread pool size
        self.logger = logging.getLogger(__name__)

    def tokenize_and_shingle(self, text: str, max_tokens: int = MAX_TOKENS) -> List[str]:
        """Tokenize text and create shingles with caching.

        Args:
            text: Input text
            max_tokens: Maximum tokens to process

        Returns:
            List of shingle tokens
        """
        # Generate hash for cache key
        text_hash = TemplateUtils.generate_text_hash(text)
        cache_key = f"tokens_{text_hash}_{max_tokens}"

        # Check tokenizer cache first
        if self.tokenizer_cache:
            cached_tokens = self.tokenizer_cache.get(cache_key)
            if cached_tokens is not None:
                return cached_tokens

        # Simple tokenization: split on whitespace and punctuation
        import re

        tokens = re.findall(TOKEN_REGEX, text.lower())

        # Limit tokens
        tokens = tokens[:max_tokens]

        # Create shingles (3-grams)
        shingles = []
        for i in range(len(tokens) - SHINGLE_SIZE + 1):
            shingle = " ".join(tokens[i: i + SHINGLE_SIZE])
            shingles.append(shingle)

        # Cache the result
        if self.tokenizer_cache:
            self.tokenizer_cache.put(cache_key, shingles)

        return shingles

    def _compute_single_fingerprint(self, text: str, resolution: int) -> tuple:
        """Compute single fingerprint for a specific resolution.

        Args:
            text: Input text
            resolution: Token resolution

        Returns:
            Tuple of (resolution, fingerprint)
        """
        tokens = self.tokenize_and_shingle(text, resolution)
        if tokens:
            simhash = SimHash(tokens, hashbits=64)  # Always use 64-bit for consistency
            return (resolution, simhash.fingerprint)
        else:
            return (resolution, 0)

    def compute_fingerprints(self, text: str, use_adaptive: bool = True) -> Dict[int, int]:
        """Compute SimHash fingerprints for all resolutions with caching and parallel processing.

        Args:
            text: Input text
            use_adaptive: Whether to use adaptive resolution selection

        Returns:
            Dict mapping resolution to fingerprint
        """
        # Generate hash for cache key
        text_hash = TemplateUtils.generate_text_hash(text)

        # Check fingerprint cache first
        if self.fingerprint_cache:
            cached_fingerprints = self.fingerprint_cache.get(text_hash)
            if cached_fingerprints is not None:
                return cached_fingerprints

        # Use adaptive resolution selection
        if use_adaptive:
            adaptive_resolutions = self.complexity_analyzer.get_adaptive_resolutions(text, self.resolutions)
            self.logger.info(f"Using adaptive resolutions: {adaptive_resolutions}")
        else:
            adaptive_resolutions = self.resolutions

        fingerprints = {}

        if self.use_parallel and len(adaptive_resolutions) > 1:
            # Parallel computation for multiple resolutions
            try:
                with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                    # Submit all fingerprint computation tasks
                    futures = [
                        executor.submit(self._compute_single_fingerprint, text, resolution)
                        for resolution in adaptive_resolutions
                    ]

                    # Collect results as they complete
                    for future in futures:
                        resolution, fingerprint = future.result()
                        fingerprints[resolution] = fingerprint

                self.logger.debug(f"Parallel fingerprint computation completed for {len(adaptive_resolutions)} resolutions")

            except Exception as e:
                self.logger.warning(f"Parallel computation failed, falling back to sequential: {e}")
                # Fall back to sequential computation
                for resolution in adaptive_resolutions:
                    resolution, fingerprint = self._compute_single_fingerprint(text, resolution)
                    fingerprints[resolution] = fingerprint
        else:
            # Sequential computation (single resolution or parallel disabled)
            for resolution in adaptive_resolutions:
                resolution, fingerprint = self._compute_single_fingerprint(text, resolution)
                fingerprints[resolution] = fingerprint

        # Cache the result
        if self.fingerprint_cache:
            self.fingerprint_cache.put(text_hash, fingerprints)

        return fingerprints

    def find_best_match(
        self, fingerprints: Dict[int, int], stored_templates: List[Template], thresholds: Dict[int, int],
        early_termination_threshold: float = 0.95
    ) -> Dict[str, Any]:
        """Find best matching template using multi-resolution search with early termination.

        Args:
            fingerprints: Query fingerprints
            stored_templates: List of stored template dicts
            thresholds: Hamming distance thresholds per resolution
            early_termination_threshold: Confidence threshold for early termination

        Returns:
            Best match info or empty dict
        """
        best_match = {}
        best_score = -1

        # Two-phase matching strategy
        # Phase 1: Fast candidate selection using 64-bit fingerprint
        candidates = self._find_candidates_phase1(fingerprints, stored_templates, thresholds)

        if not candidates:
            self.logger.debug("No candidates found in phase 1")
            return {}

        self.logger.debug(f"Phase 1 found {len(candidates)} candidates")

        # Phase 2: Detailed matching on candidates only
        # Search from largest to smallest resolution
        for resolution in sorted(self.resolutions, reverse=True):
            if resolution not in fingerprints:
                continue

            query_fp = fingerprints[resolution]
            threshold = thresholds.get(resolution, resolution // THRESHOLD_DIVISOR)  # Default ~6% for 64-bit

            for template in candidates:
                stored_fp = getattr(template, f"fingerprint_{resolution}")
                if stored_fp is not None:
                    # Convert hex string to int if necessary
                    if isinstance(stored_fp, str):
                        stored_fp = int(stored_fp, 16)

                    # Quick distance check before full computation
                    if best_score >= early_termination_threshold:
                        # Early termination if we already have a great match
                        self.logger.debug(f"Early termination at resolution {resolution}, score {best_score}")
                        return best_match

                    distance = SimHash.hamming_distance(query_fp, stored_fp)
                    if distance <= threshold:
                        # Calculate score (lower distance = higher score)
                        score = 1.0 - (distance / 64.0)
                        if score > best_score:
                            best_score = score
                            best_match = {
                                "template": template,
                                "resolution": resolution,
                                "distance": distance,
                                "score": score,
                            }

        return best_match

    def _find_candidates_phase1(self, fingerprints: Dict[int, int], stored_templates: List[Template],
                               thresholds: Dict[int, int]) -> List[Template]:
        """Phase 1: Fast candidate selection using 64-bit fingerprint.

        Args:
            fingerprints: Query fingerprints
            stored_templates: List of stored template dicts
            thresholds: Hamming distance thresholds

        Returns:
            List of candidate templates for detailed matching
        """
        candidates = []

        # Use 64-bit fingerprint for fast candidate selection
        if 64 not in fingerprints:
            return candidates

        query_fp_64 = fingerprints[64]
        threshold_64 = thresholds.get(64, 64 // THRESHOLD_DIVISOR)

        # Fast candidate selection
        for template in stored_templates:
            stored_fp_64 = getattr(template, "fingerprint_64")
            if stored_fp_64 is not None:
                # Convert hex string to int if necessary
                if isinstance(stored_fp_64, str):
                    stored_fp_64 = int(stored_fp_64, 16)

                distance = SimHash.hamming_distance(query_fp_64, stored_fp_64)
                if distance <= threshold_64:
                    candidates.append(template)

                    # Early exit if we find a perfect match
                    if distance == 0:
                        self.logger.debug("Found perfect match in phase 1")
                        return [template]

        return candidates


class TemplateMatcher:
    """High-level template matching with learning and caching."""

    def __init__(self, repository: TemplateRepository, resolutions: Optional[List[int]] = None, template_cache: Optional['TemplateCache'] = None):
        """Initialize with repository and caches."""
        self.repository = repository  # Changed from db_manager to repository
        self.template_cache = template_cache

        # Initialize caches for SimHash
        from ..cache.tokenizer_cache import TokenizerCache
        from ..cache.fingerprint_cache import FingerprintCache
        tokenizer_cache = TokenizerCache()
        fingerprint_cache = FingerprintCache()
        complexity_analyzer = TextComplexityAnalyzer()

        self.simhash = MultiResolutionSimHash(resolutions, tokenizer_cache, fingerprint_cache, complexity_analyzer)
        self.default_thresholds = DEFAULT_THRESHOLDS

        # Add logging
        self.logger = logging.getLogger(__name__)

        # Optimization configuration
        self.early_termination_threshold = 0.95
        self.use_adaptive_resolutions = True

    def find_matching_template(self, text: str) -> Dict[str, Any]:
        """Find the best matching template for the input text using SimHash similarity with caching.

        This method computes multi-resolution fingerprints for the input text,
        retrieves all stored templates from the database, and finds the template
        with the highest similarity score above the configured thresholds.

        Args:
            text: The input text to find a matching template for.

        Returns:
            A dictionary containing match information with keys:
            - 'template': The matched Template object (if found)
            - 'resolution': The resolution level used for matching
            - 'distance': Hamming distance between fingerprints
            - 'score': Similarity score (0.0 to 1.0)
            Returns an empty dict if no suitable match is found.

        Raises:
            RuntimeError: If database query fails or other critical errors occur.
        """
        # Early return for empty input to avoid unnecessary computation
        if not text or not text.strip():
            return {}

        try:
            # Generate cache key for template matching
            text_hash = TemplateUtils.generate_text_hash(text)
            cache_key = f"match_{text_hash}"

            # Check template cache first
            if self.template_cache:
                cached_match = self.template_cache.get(cache_key)
                if cached_match is not None:
                    self.logger.debug(f"Template cache hit for text: {text[:50]}...")
                    return cached_match

            # Log optimization decision
            self.logger.info(f"Starting template matching for text (length: {len(text)})")

            # Compute multi-resolution fingerprints for the input text with adaptive resolutions
            start_time = time.perf_counter()
            fingerprints = self.simhash.compute_fingerprints(text, use_adaptive=self.use_adaptive_resolutions)
            fingerprint_time = time.perf_counter() - start_time
            self.logger.debug(f"Fingerprint computation completed in {fingerprint_time:.4f}s")

            # Retrieve stored templates that have at least one fingerprint set
            # This filters out templates without fingerprints for better performance
            # Changed from db.get_templates_with_fingerprints() to repository method
            # Since the repository interface doesn't have this method, we'll need to get all templates
            # and filter in memory for now, or add the method to the interface
            templates = self.repository.get_all_with_fingerprints()
            self.logger.debug(f"Retrieved {len(templates)} templates for matching")

            # Find the best matching template using optimized multi-resolution search
            start_time = time.perf_counter()
            match = self.simhash.find_best_match(
                fingerprints,
                templates,
                self.default_thresholds,
                early_termination_threshold=self.early_termination_threshold
            )
            matching_time = time.perf_counter() - start_time
            self.logger.debug(f"Template matching completed in {matching_time:.4f}s")

            # Log optimization results
            if match:
                self.logger.info(
                    f"Found match: template_id={match['template'].id}, "
                    f"resolution={match['resolution']}, "
                    f"distance={match['distance']}, "
                    f"score={match['score']:.3f}"
                )
            else:
                self.logger.debug("No matching template found")

            # Cache the result if we found a match
            if self.template_cache and match:
                self.template_cache.put(cache_key, match)
                self.logger.debug(f"Cached template match for text: {text[:50]}...")

            return match

        except Exception as e:
            # Log the error and re-raise as RuntimeError for higher-level handling
            logger = logging.getLogger(__name__)
            logger.error(f"Error finding matching template for text: {e}")
            raise RuntimeError(f"Failed to find matching template: {str(e)}") from e

    def learn_template(self, text: str, working_window: int, optimal_batch_size: Optional[int] = None) -> int:
        """Learn new template from text.

        Args:
            text: Input text
            working_window: Optimal context window size
            optimal_batch_size: Optimal batch size (optional)

        Returns:
            Template ID
        """
        # Compute fingerprints
        fingerprints = self.simhash.compute_fingerprints(text)

        # Create template hash (hash of the text)
        template_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:HASH_SLICE]

        # Save to repository (changed from db.save_template to repository.save_template)
        template_id = self.repository.save_template(template_hash, fingerprints, working_window, optimal_batch_size)

        return template_id