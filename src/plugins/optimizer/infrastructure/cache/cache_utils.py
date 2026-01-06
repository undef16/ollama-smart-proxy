"""Cache invalidation utilities."""

from typing import Optional
from .template_cache import TemplateCache
from .fingerprint_cache import FingerprintCache


class CacheUtils:
    """Utility class for cache operations."""

    @staticmethod
    def invalidate_all_caches(
        template_cache: Optional[TemplateCache],
        fingerprint_cache: Optional[FingerprintCache]
    ) -> None:
        """Invalidate all template and fingerprint caches.

        Used after learning new templates to ensure consistency.
        """
        if template_cache:
            template_cache.clear()
        if fingerprint_cache:
            fingerprint_cache.invalidate_all()
