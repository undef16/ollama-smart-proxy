"""Base adapter for template repository with shared logic."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any

from ...ports.template_repository import TemplateRepository
from ...domain.template import Template
from ...const import DEFAULT_WORKING_WINDOW, DEFAULT_RESOLUTIONS
from ...infrastructure.utils.template_utils import TemplateUtils


class BaseTemplateRepository(TemplateRepository, ABC):
    """Abstract base class for template repository adapters.
    
    Provides shared save_template() and update_template() logic.
    Subclasses must implement database-specific abstract methods.
    """
    
    # Subclass must set these
    _engine = None
    _TemplateModel = None
    
    # =========================================================================
    # Port interface methods (implemented in base class using abstract helpers)
    # =========================================================================
    
    def find_by_hash(self, template_hash: str) -> Optional[Template]:
        """Find a template by its hash."""
        return self._find_by_hash(template_hash)
    
    def save_template(
        self,
        template_hash: str,
        fingerprints: Dict[int, int],
        working_window: int,
        optimal_batch_size: Optional[int] = None
    ) -> int:
        """Save or update a template. Returns template ID.
        
        Shared logic for both SQLite and PostgreSQL adapters.
        """
        existing = self._find_by_hash(template_hash)
        
        if existing:
            return self._update_existing_template(
                template_id=existing.id,
                working_window=working_window,
                optimal_batch_size=optimal_batch_size,
                fingerprints=fingerprints
            )
        else:
            return self._create_template(
                template_hash=template_hash,
                fingerprints=fingerprints,
                working_window=working_window,
                optimal_batch_size=optimal_batch_size
            )
    
    def update_template(
        self,
        template_id: int,
        new_distance: int,
        working_window: int,
        optimal_batch_size: Optional[int] = None
    ) -> None:
        """Update template observation count and statistics.
        
        Shared logic for both SQLite and PostgreSQL adapters.
        """
        template = self._find_by_id(template_id)
        
        if template:
            # Calculate new average distance using running average formula
            new_count = template.observation_count + 1
            new_avg_distance = (
                template.avg_distance * template.observation_count + new_distance
            ) / new_count if template.observation_count > 0 else new_distance
            
            # Use utility function to check if working_window update is significant
            update_window = TemplateUtils.should_update_working_window(
                template.working_window, working_window, threshold=0.15
            )
            
            self._update_existing_template(
                template_id=template_id,
                working_window=working_window if update_window else template.working_window,
                optimal_batch_size=optimal_batch_size,
                observation_count=new_count,
                avg_distance=new_avg_distance
            )
    
    def batch_save_templates(
        self,
        templates_data: List[Dict[str, Any]]
    ) -> List[int]:
        """Batch save multiple templates efficiently.
        
        Args:
            templates_data: List of dicts with template_hash, fingerprints,
                          working_window, optimal_batch_size
            
        Returns:
            List of template IDs
        """
        if not templates_data:
            return []
        
        template_ids: List[int] = []
        
        # Collect existing template hashes for batch lookup
        template_hashes = [td['template_hash'] for td in templates_data]
        existing_map = self._find_by_hashes(template_hashes)
        
        new_templates: List[Dict[str, Any]] = []
        
        for template_data in templates_data:
            template_hash = template_data['template_hash']
            fingerprints = template_data['fingerprints']
            working_window = template_data.get('working_window', DEFAULT_WORKING_WINDOW)
            optimal_batch_size = template_data.get('optimal_batch_size', 32)
            
            existing = existing_map.get(template_hash)
            if existing:
                # Update existing template
                self._update_existing_template(
                    template_id=existing.id,
                    working_window=working_window,
                    optimal_batch_size=optimal_batch_size,
                    fingerprints=fingerprints
                )
                template_ids.append(existing.id)
            else:
                # Prepare new template data
                new_templates.append({
                    'template_hash': template_hash,
                    'working_window': working_window,
                    'optimal_batch_size': optimal_batch_size,
                    'fingerprint_64': fingerprints.get(64),
                    'fingerprint_128': fingerprints.get(128),
                    'fingerprint_256': fingerprints.get(256),
                    'fingerprint_512': fingerprints.get(512),
                    'fingerprint_1024': fingerprints.get(1024),
                    'observation_count': 0,
                    'avg_distance': 0.0,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                })
        
        # Bulk insert new templates
        if new_templates:
            new_ids = self._bulk_insert(new_templates)
            template_ids.extend(new_ids)
        
        return template_ids
    
    def batch_update_templates(
        self,
        updates: List[Dict[str, Any]]
    ) -> None:
        """Batch update multiple templates.
        
        Args:
            updates: List of dicts with template_id, new_distance,
                    working_window, optimal_batch_size
        """
        if not updates:
            return
        
        # Single query to fetch all templates at once
        template_ids = [u['template_id'] for u in updates]
        templates = self._find_by_ids(template_ids)
        
        # Apply updates
        for update_data in updates:
            template_id = update_data['template_id']
            template = templates.get(template_id)
            
            if template:
                new_count = template.observation_count
                new_avg = template.avg_distance
                
                if 'new_distance' in update_data:
                    new_count += 1
                    new_avg = (
                        template.avg_distance * template.observation_count + update_data['new_distance']
                    ) / new_count if template.observation_count > 0 else update_data['new_distance']
                
                update_window = template.working_window
                if 'working_window' in update_data:
                    ww = update_data['working_window']
                    if TemplateUtils.should_update_working_window(template.working_window, ww, threshold=0.15):
                        update_window = ww
                
                self._update_existing_template(
                    template_id=template_id,
                    working_window=update_window,
                    optimal_batch_size=update_data.get('optimal_batch_size'),
                    observation_count=new_count,
                    avg_distance=new_avg
                )
    
    # =========================================================================
    # Abstract methods that subclasses must implement
    # =========================================================================
    
    @abstractmethod
    def _find_by_hash(self, template_hash: str) -> Optional[Template]:
        """Find a template by its hash. Subclass implementation."""
        pass
    
    @abstractmethod
    def _find_by_id(self, template_id: int) -> Optional[Template]:
        """Find a template by its ID. Subclass implementation."""
        pass
    
    @abstractmethod
    def _find_by_hashes(self, template_hashes: List[str]) -> Dict[str, Template]:
        """Find multiple templates by their hashes. Subclass implementation."""
        pass
    
    @abstractmethod
    def _find_by_ids(self, template_ids: List[int]) -> Dict[int, Template]:
        """Find multiple templates by their IDs. Subclass implementation."""
        pass
    
    @abstractmethod
    def _create_template(
        self,
        template_hash: str,
        fingerprints: Dict[int, int],
        working_window: int,
        optimal_batch_size: Optional[int] = None
    ) -> int:
        """Create a new template. Subclass implementation must return template ID."""
        pass
    
    @abstractmethod
    def _update_existing_template(
        self,
        template_id: int,
        working_window: int,
        optimal_batch_size: Optional[int],
        fingerprints: Optional[Dict[int, int]] = None,
        observation_count: Optional[int] = None,
        avg_distance: Optional[float] = None
    ) -> int:
        """Update an existing template. Subclass implementation."""
        pass
    
    @abstractmethod
    def _update_fingerprints(
        self,
        template_id: int,
        fingerprints: Dict[int, int]
    ) -> None:
        """Update fingerprints for a template. Subclass implementation."""
        pass
    
    @abstractmethod
    def _commit(self) -> None:
        """Commit the current transaction. Subclass implementation."""
        pass
    
    @abstractmethod
    def _bulk_insert(self, templates_data: List[Dict[str, Any]]) -> List[int]:
        """Bulk insert new templates. Subclass implementation must return list of IDs."""
        pass
