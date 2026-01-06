"""Batch operations for database template management with transaction support."""

import logging
import time
from typing import Dict, List, Any
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .const import DEFAULT_WORKING_WINDOW, DEFAULT_RESOLUTIONS
from .performance_monitor import PerformanceMonitor


class BatchOperationsManager:
    """Batch operations manager for template database operations with transaction management."""

    def __init__(self, db_engine, performance_monitor: PerformanceMonitor):
        """Initialize batch operations manager.
        
        Args:
            db_engine: SQLAlchemy database engine
            performance_monitor: Performance monitor instance for tracking operations
        """
        self._engine = db_engine
        self.performance_monitor = performance_monitor
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Create a session factory for transaction management
        self.Session = sessionmaker(bind=self._engine)

    def _setup_logging(self) -> None:
        """Setup logging configuration for batch operations."""
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    @contextmanager
    def _transaction_context(self, operation_name: str):
        """Context manager for transaction management with performance monitoring.
        
        Args:
            operation_name: Name of the operation for performance tracking
            
        Yields:
            Database session within transaction context
        """
        session = self.Session()
        start_time = time.perf_counter()
        success = False
        
        try:
            yield session
            session.commit()
            success = True
            self.logger.debug(f"{operation_name}: Transaction committed successfully")
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"{operation_name}: Transaction rolled back due to error: {e}")
            raise
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"{operation_name}: Transaction rolled back due to unexpected error: {e}")
            raise
            
        finally:
            duration = time.perf_counter() - start_time
            self.performance_monitor.record_operation(operation_name, duration, success)
            session.close()
            self.logger.info(f"{operation_name}: Completed in {duration:.4f}s (success: {success})")

    def batch_save_templates(self, templates_data: List[Dict[str, Any]]) -> List[int]:
        """Batch save multiple templates efficiently with transaction management.
        
        Args:
            templates_data: List of template data dictionaries containing:
                - template_hash: Template hash string
                - fingerprints: Dictionary of resolution -> fingerprint
                - working_window: Working window size (optional)
                - optimal_batch_size: Optimal batch size (optional)
                
        Returns:
            List of template IDs that were created/updated
        """
        # Lazy import to avoid circular dependency
        from .db_utils import Template
        
        if not templates_data:
            self.logger.warning("batch_save_templates: Empty templates_data provided")
            return []
        
        template_ids = []
        
        with self._transaction_context('batch_save_templates') as session:
            for template_data in templates_data:
                template_hash = template_data['template_hash']
                fingerprints = template_data['fingerprints']
                working_window = template_data.get('working_window', DEFAULT_WORKING_WINDOW)
                optimal_batch_size = template_data.get('optimal_batch_size', 32)
                
                # Check if template exists
                existing = session.query(Template).filter(Template.template_hash == template_hash).first()
                
                if existing:
                    # Update existing template
                    existing.working_window = working_window
                    existing.optimal_batch_size = optimal_batch_size
                    existing.updated_at = datetime.now()
                    for res in DEFAULT_RESOLUTIONS:
                        if res in fingerprints:
                            setattr(existing, f"fingerprint_{res}", hex(fingerprints[res]))
                    template_ids.append(existing.id)
                    self.logger.debug(f"Updated existing template {existing.id} for hash {template_hash}")
                    
                else:
                    # Create new template
                    template = Template(
                        template_hash=template_hash,
                        working_window=working_window,
                        optimal_batch_size=optimal_batch_size,
                        fingerprint_64=hex(fingerprints[64]) if 64 in fingerprints else None,
                        fingerprint_128=hex(fingerprints[128]) if 128 in fingerprints else None,
                        fingerprint_256=hex(fingerprints[256]) if 256 in fingerprints else None,
                        fingerprint_512=hex(fingerprints[512]) if 512 in fingerprints else None,
                        fingerprint_1024=hex(fingerprints[1024]) if 1024 in fingerprints else None,
                    )
                    session.add(template)
                    session.flush()  # Get the ID immediately
                    template_ids.append(template.id)
                    self.logger.debug(f"Created new template {template.id} for hash {template_hash}")
        
        self.logger.info(f"Batch saved {len(templates_data)} templates, created/updated {len(template_ids)} templates")
        return template_ids

    def batch_update_templates(self, updates: List[Dict[str, Any]]) -> None:
        """Batch update multiple templates efficiently using SQLAlchemy bulk operations.
        
        Args:
            updates: List of update dictionaries containing:
                - template_id: ID of template to update
                - new_distance: New distance value (optional)
                - working_window: New working window (optional)
                - optimal_batch_size: New optimal batch size (optional)
        """
        # Lazy import to avoid circular dependency
        from .db_utils import Template
        
        if not updates:
            self.logger.warning("batch_update_templates: Empty updates provided")
            return
        
        with self._transaction_context('batch_update_templates') as session:
            updated_count = 0
            
            for update_data in updates:
                template_id = update_data['template_id']
                template = session.query(Template).filter(Template.id == template_id).first()
                
                if template:
                    # Apply updates
                    if 'new_distance' in update_data:
                        template.observation_count += 1
                        template.avg_distance = (
                            template.avg_distance * (template.observation_count - 1) + update_data['new_distance']
                        ) / template.observation_count
                        
                    if 'working_window' in update_data:
                        working_window = update_data['working_window']
                        # Only update working_window if new value differs significantly (15% threshold)
                        if working_window < template.working_window * 0.85 or working_window > template.working_window * 1.15:
                            template.working_window = working_window
                            
                    if 'optimal_batch_size' in update_data:
                        template.optimal_batch_size = update_data['optimal_batch_size']
                        
                    template.updated_at = datetime.now()
                    updated_count += 1
                    self.logger.debug(f"Updated template {template_id} with new parameters")
                else:
                    self.logger.warning(f"Template {template_id} not found for update")
            
            self.logger.info(f"Batch updated {updated_count}/{len(updates)} templates successfully")

    def batch_learn_templates(self, requests_data: List[Dict[str, Any]], matcher) -> List[int]:
        """Batch learn templates from multiple requests efficiently.
        
        Args:
            requests_data: List of request data dictionaries containing:
                - prompt_text: The prompt text to learn from
                - working_window: The working window size to use
                - optimal_batch_size: The optimal batch size to use (optional)
            matcher: TemplateMatcher instance for computing fingerprints
                
        Returns:
            List of template IDs that were created
        """
        if not requests_data:
            self.logger.warning("batch_learn_templates: Empty requests_data provided")
            return []
        
        templates_data = []
        
        for request_data in requests_data:
            prompt_text = request_data.get('prompt_text', '')
            working_window = request_data.get('working_window', DEFAULT_WORKING_WINDOW)
            optimal_batch_size = request_data.get('optimal_batch_size', 32)
            
            if prompt_text and prompt_text.strip():
                try:
                    # Compute fingerprints for the prompt text
                    fingerprints = matcher.simhash.compute_fingerprints(prompt_text)
                    
                    # Generate template hash (using the same method as TemplateMatcher.learn_template)
                    import hashlib
                    from .const import HASH_SLICE
                    template_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:HASH_SLICE]
                    
                    templates_data.append({
                        'template_hash': template_hash,
                        'fingerprints': fingerprints,
                        'working_window': working_window,
                        'optimal_batch_size': optimal_batch_size
                    })
                    
                except Exception as e:
                    self.logger.error(f"Failed to process request for batch learning: {e}")
                    continue
            else:
                self.logger.warning("batch_learn_templates: Empty prompt_text in request data")
        
        if not templates_data:
            self.logger.warning("batch_learn_templates: No valid templates generated from requests")
            return []
        
        # Use batch_save_templates to save all templates efficiently
        return self.batch_save_templates(templates_data)

    def get_batch_operation_stats(self) -> Dict[str, Any]:
        """Get statistics for batch operations.
        
        Returns:
            Dictionary containing batch operation statistics
        """
        stats = self.performance_monitor.get_stats()
        
        # Filter for batch operations
        batch_stats = {}
        for key, value in stats.items():
            if 'batch_' in key or 'batch' in key:
                batch_stats[key] = value
        
        return {
            'batch_operations': batch_stats,
            'total_operations': stats.get('operations', {}),
            'uptime': stats.get('uptime', 0)
        }

    def log_batch_performance_summary(self) -> None:
        """Log comprehensive performance summary for batch operations."""
        stats = self.get_batch_operation_stats()
        
        self.logger.info("=== Batch Operations Performance Summary ===")
        self.logger.info(f"Uptime: {stats['uptime']:.1f}s")
        
        for op_name, op_stats in stats['batch_operations'].items():
            if 'duration' in op_name:
                self.logger.info(
                    f"{op_name.replace('_duration', '')}: "
                    f"{op_stats['count']} calls, "
                    f"avg: {op_stats['avg']:.4f}s, "
                    f"min: {op_stats['min']:.4f}s, "
                    f"max: {op_stats['max']:.4f}s, "
                    f"total: {op_stats['total']:.4f}s"
                )
        
        self.logger.info("=== End Batch Operations Summary ===")

    def perform_batch_maintenance(self) -> None:
        """Perform database maintenance operations optimized for batch processing."""
        start_time = time.perf_counter()
        
        try:
            with self._transaction_context('batch_maintenance') as session:
                # Execute VACUUM to optimize database file
                session.execute(text("PRAGMA vacuum"))
                
                # Execute ANALYZE to update statistics
                session.execute(text("PRAGMA analyze"))
                
                # Execute OPTIMIZE to further optimize the database
                session.execute(text("PRAGMA optimize"))
                
                self.logger.info("Batch maintenance: Database optimization completed")
            
            duration = time.perf_counter() - start_time
            self.logger.info(f"Batch maintenance completed in {duration:.4f}s")
            
        except SQLAlchemyError as e:
            duration = time.perf_counter() - start_time
            self.logger.error(f"Batch maintenance failed after {duration:.4f}s: {e}")
            raise

    def validate_batch_data(self, batch_data: List[Dict[str, Any]], data_type: str = 'templates') -> bool:
        """Validate batch data before processing.
        
        Args:
            batch_data: Data to validate
            data_type: Type of data being validated
                
        Returns:
            True if data is valid, False otherwise
        """
        if not batch_data:
            self.logger.warning(f"validate_batch_data: Empty {data_type} data")
            return False
        
        required_fields = {
            'templates': ['template_hash', 'fingerprints'],
            'updates': ['template_id'],
            'requests': ['prompt_text']
        }
        
        data_required_fields = required_fields.get(data_type, [])
        
        for i, item in enumerate(batch_data):
            if not isinstance(item, dict):
                self.logger.error(f"validate_batch_data: Item {i} is not a dictionary")
                return False
            
            for field in data_required_fields:
                if field not in item:
                    self.logger.error(f"validate_batch_data: Missing required field '{field}' in item {i}")
                    return False
        
        self.logger.debug(f"validate_batch_data: {data_type} data validation passed for {len(batch_data)} items")
        return True
