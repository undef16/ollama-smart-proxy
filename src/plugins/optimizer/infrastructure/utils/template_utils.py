"""Template-related utilities."""

import hashlib
from typing import Dict, Optional

# Constants
WORKING_WINDOW_SIGNIFICANCE_THRESHOLD = 0.15  # 15%


class TemplateUtils:
    """Utility class for template-related operations."""

    @staticmethod
    def should_update_working_window(current: int, new: int, threshold: float = 0.15) -> bool:
        """Check if working_window update is significant enough."""
        if current == 0:
            return new > 0
        change_ratio = abs(new - current) / current
        return change_ratio > threshold

    @staticmethod
    def generate_text_hash(text: str) -> str:
        """Generate SHA256 hash for text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_cache_key(prefix: str, text: str, suffix: str = "") -> str:
        """Generate cache key for text-based operations."""
        text_hash = TemplateUtils.generate_text_hash(text)
        return f"{prefix}_{text_hash}{suffix}"

    @staticmethod
    def int_to_hex(value: Optional[int]) -> Optional[str]:
        """Convert integer to hex string for storage."""
        return hex(value) if value is not None else None

    @staticmethod
    def hex_to_int(hex_str: Optional[str]) -> Optional[int]:
        """Convert hex string to integer."""
        return int(hex_str, 16) if hex_str else None
