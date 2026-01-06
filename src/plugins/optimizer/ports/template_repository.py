"""Port interface for template storage operations."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class TemplateRepository(ABC):
    """Port interface for template storage operations."""

    @abstractmethod
    def save_template(
        self,
        template_hash: str,
        fingerprints: Dict[int, int],
        working_window: int,
        optimal_batch_size: Optional[int] = None
    ) -> int:
        """Save or update a template. Returns template ID."""
        pass

    @abstractmethod
    def find_by_hash(self, template_hash: str) -> Optional[Any]:
        """Find a template by its hash. Returns None if not found."""
        pass

    @abstractmethod
    def find_by_fingerprint(
        self,
        resolution: int,
        fingerprint: int,
        threshold: int
    ) -> Optional[Any]:
        """Find a template with similar fingerprint using similarity matching.
        
        Args:
            resolution: 64, 128, 256, 512, or 1024
            fingerprint: The fingerprint to match
            threshold: Hamming distance threshold
            
        Returns:
            The matching template or None if not found.
        """
        pass

    @abstractmethod
    def update_template(
        self,
        template_id: int,
        new_distance: int,
        working_window: int,
        optimal_batch_size: Optional[int] = None
    ) -> None:
        """Update template observation count and statistics."""
        pass

    @abstractmethod
    def batch_save_templates(
        self,
        templates_data: List[Dict[str, Any]]
    ) -> List[int]:
        """Batch save multiple templates efficiently.
        
        Args:
            templates_data: List of dicts with template_hash, fingerprints,
                          working_window, optimal_batch_size
            
        Returns:
            List of template IDs.
        """
        pass

    @abstractmethod
    def batch_update_templates(
        self,
        updates: List[Dict[str, Any]]
    ) -> None:
        """Batch update multiple templates.
        
        Args:
            updates: List of dicts with template_id, new_distance,
                    working_window, optimal_batch_size
        """
        pass

    @abstractmethod
    def get_all_with_fingerprints(self) -> List[Any]:
        """Get all templates that have at least one fingerprint set."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass
