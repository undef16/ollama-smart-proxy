"""SimHash utilities for prompt template detection."""

import hashlib
import logging
from typing import List, Dict, Optional, Any

from .db_utils import DatabaseManager, Template
from .const import (
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
    def _hash_token(token: str, hashbits: int) -> int:
        """Hash a single token to a bit vector."""
        # Use MD5 for good distribution, take first 16 bytes (128 bits)
        h = hashlib.md5(token.encode("utf-8")).digest()[:HASH_BYTES]
        # Convert to int
        token_hash = int.from_bytes(h, byteorder="big")
        # Truncate to hashbits
        return token_hash & ((1 << hashbits) - 1)

    def _compute_fingerprint(self, tokens: List[str]) -> int:
        """Compute SimHash fingerprint."""
        if not tokens:
            return 0

        # Initialize vector
        v = [0] * self.hashbits

        # Process each token
        for token in tokens:
            token_hash = self._hash_token(token, self.hashbits)

            # Add to vector (1 for set bits, -1 for unset)
            for i in range(self.hashbits):
                bit = (token_hash >> i) & 1
                v[i] += 1 if bit else -1

        # Convert to fingerprint
        fingerprint = 0
        for i in range(self.hashbits):
            if v[i] >= 0:
                fingerprint |= 1 << i

        return fingerprint

    @staticmethod
    def hamming_distance(fp1: int, fp2: int) -> int:
        """Calculate Hamming distance between two fingerprints."""
        return bin(fp1 ^ fp2).count("1")

    @staticmethod
    def similarity(fp1: int, fp2: int, hashbits: int) -> float:
        """Calculate similarity score (0.0 to 1.0)."""
        distance = SimHash.hamming_distance(fp1, fp2)
        return 1.0 - (distance / hashbits)


class MultiResolutionSimHash:
    """Multi-resolution SimHash for template detection."""

    def __init__(self, resolutions: Optional[List[int]] = None):
        """Initialize with list of resolutions (token counts)."""
        self.resolutions = resolutions or DEFAULT_RESOLUTIONS.copy()

    def tokenize_and_shingle(self, text: str, max_tokens: int = MAX_TOKENS) -> List[str]:
        """Tokenize text and create shingles.

        Args:
            text: Input text
            max_tokens: Maximum tokens to process

        Returns:
            List of shingle tokens
        """
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

        return shingles

    def compute_fingerprints(self, text: str) -> Dict[int, int]:
        """Compute SimHash fingerprints for all resolutions.

        Args:
            text: Input text

        Returns:
            Dict mapping resolution to fingerprint
        """
        fingerprints = {}

        for resolution in self.resolutions:
            # Tokenize with resolution limit
            tokens = self.tokenize_and_shingle(text, resolution)
            if tokens:
                simhash = SimHash(tokens, hashbits=64)  # Always use 64-bit for consistency
                fingerprints[resolution] = simhash.fingerprint
            else:
                fingerprints[resolution] = 0

        return fingerprints

    def find_best_match(
        self, fingerprints: Dict[int, int], stored_templates: List[Template], thresholds: Dict[int, int]
    ) -> Dict[str, Any]:
        """Find best matching template using multi-resolution search.

        Args:
            fingerprints: Query fingerprints
            stored_templates: List of stored template dicts
            thresholds: Hamming distance thresholds per resolution

        Returns:
            Best match info or empty dict
        """
        best_match = {}
        best_score = -1

        # Search from largest to smallest resolution
        for resolution in sorted(self.resolutions, reverse=True):
            if resolution not in fingerprints:
                continue

            query_fp = fingerprints[resolution]
            threshold = thresholds.get(resolution, resolution // THRESHOLD_DIVISOR)  # Default ~6% for 64-bit

            for template in stored_templates:
                stored_fp = getattr(template, f"fingerprint_{resolution}")
                if stored_fp is not None:
                    # Convert hex string to int if necessary
                    if isinstance(stored_fp, str):
                        stored_fp = int(stored_fp, 16)
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


class TemplateMatcher:
    """High-level template matching with learning."""

    def __init__(self, db_manager: DatabaseManager, resolutions: Optional[List[int]] = None):
        """Initialize with database manager."""
        self.db = db_manager
        self.simhash = MultiResolutionSimHash(resolutions)
        self.default_thresholds = DEFAULT_THRESHOLDS

    def find_matching_template(self, text: str) -> Dict[str, Any]:
        """Find the best matching template for the input text using SimHash similarity.

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
            # Compute multi-resolution fingerprints for the input text
            fingerprints = self.simhash.compute_fingerprints(text)

            # Retrieve stored templates that have at least one fingerprint set
            # This filters out templates without fingerprints for better performance
            templates = self.db.get_templates_with_fingerprints()

            # Find the best matching template using multi-resolution search
            match = self.simhash.find_best_match(fingerprints, templates, self.default_thresholds)

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

        # Save to database
        template_id = self.db.save_template(template_hash, fingerprints, working_window, optimal_batch_size)

        return template_id
