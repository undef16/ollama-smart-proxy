"""Database utilities for Optimizer Agent using SQLAlchemy."""

import threading
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ...const import (
    DEFAULT_WORKING_WINDOW,
    PRAGMA_JOURNAL_MODE,
    PRAGMA_SYNCHRONOUS,
    PRAGMA_CACHE_SIZE,
    DEFAULT_RESOLUTIONS,
)
from .base import Base
from ..cache.query_cache import QueryCache
from ..performance_monitor import PerformanceMonitor

from .template_model import TemplateModel

class DatabaseManager:
    """Thread-safe SQLite database manager for optimizer statistics using SQLAlchemy."""

    _instance: Optional["DatabaseManager"] = None
    _engine = None
    _lock = threading.Lock()

    @staticmethod
    def _register_hamming_distance(connection):
        """Register the hamming_distance SQLite custom function."""
        connection.create_function("hamming_distance", 2, lambda a, b: bin(a ^ b).count("1") if a is not None and b is not None else None)

    def __new__(cls, db_path: Path) -> "DatabaseManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-check locking
                    cls._instance = super().__new__(cls)
                    cls._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

                    # Set SQLite pragmas on connect
                    @event.listens_for(cls._engine, "connect")
                    def set_sqlite_pragma(dbapi_connection, connection_record):
                        dbapi_connection.execute(PRAGMA_JOURNAL_MODE)
                        dbapi_connection.execute(PRAGMA_SYNCHRONOUS)
                        dbapi_connection.execute(PRAGMA_CACHE_SIZE)
                        # Register the hamming_distance UDF for SQL-level fingerprint matching
                        DatabaseManager._register_hamming_distance(dbapi_connection)

                    Base.metadata.create_all(cls._engine)
        return cls._instance

    def __init__(self, db_path: Path):
        if not hasattr(self, "_initialized"):
            self.db_path = db_path
            self._initialized = True
            
            # Initialize performance monitoring and caching
            self.logger = logging.getLogger(__name__)
            self.query_cache = QueryCache(max_size=512, default_ttl=300)
            self.performance_monitor = PerformanceMonitor()
            self._setup_logging()
            
            
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.info("DatabaseManager initialized with performance optimizations")

    def _time_operation(self, operation_name: str):
        """Decorator to time database operations and record performance metrics."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    duration = time.perf_counter() - start_time
                    self.performance_monitor.record_operation(operation_name, duration, True)
                    return result
                except Exception as e:
                    duration = time.perf_counter() - start_time
                    self.performance_monitor.record_operation(operation_name, duration, False)
                    self.logger.error(f"Error in {operation_name}: {e}")
                    raise
            return wrapper
        return decorator
    
    def get_template_by_hash(self, template_hash: str) -> Optional[TemplateModel]:
        """Get template by hash with caching."""
        cache_key = f"template_by_hash:{template_hash}"

        # Try cache first
        cached_result = self.query_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Cache miss, query database
        with Session(self._engine) as session:
            template = session.query(TemplateModel).filter(TemplateModel.template_hash == template_hash).first()

            # Cache the result
            if template:
                self.query_cache.put(cache_key, template)

            return template
    
    def _get_template_by_id_internal(self, template_id: int) -> Optional[TemplateModel]:
        """Internal method to get template by ID (used by lazy loader)."""
        with Session(self._engine) as session:
            return session.query(TemplateModel).filter(TemplateModel.id == template_id).first()
    
    def _get_template_fingerprints_internal(self, template_id: int) -> Optional[TemplateModel]:
        """Internal method to get only fingerprint data for lazy loading."""
        with Session(self._engine) as session:
            # Only load fingerprint columns to save memory
            return session.query(TemplateModel).filter(TemplateModel.id == template_id).first()

    def get_template_by_fingerprint(self, resolution: int, fingerprint: int, threshold: int) -> Optional[TemplateModel]:
        """Find template with similar fingerprint using optimized query with caching and SQL-level filtering."""
        cache_key = f"fingerprint_{resolution}:{fingerprint}:{threshold}"

        # Try cache first
        cached_result = self.query_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        col_name = f"fingerprint_{resolution}"

        # Use SQL-level filtering with hamming_distance UDF instead of loading all templates
        with Session(self._engine) as session:
            # Get the column attribute
            col = getattr(TemplateModel, col_name)

            # Use raw SQL with the hamming_distance UDF for efficient filtering
            # This filters at the database level instead of loading all templates
            query = text(f"""
                SELECT * FROM templates
                WHERE {col_name} IS NOT NULL
                AND hamming_distance(cast({col_name} as integer), :fingerprint) <= :threshold
                LIMIT 1
            """)

            result = session.execute(query, {"fingerprint": fingerprint, "threshold": threshold})
            row = result.fetchone()

            if row:
                # Convert row to TemplateModel object
                template = session.query(TemplateModel).filter(TemplateModel.id == row[0]).first()
                if template:
                    # Cache the result
                    self.query_cache.put(cache_key, template)
                    return template

        return None
    
    def get_templates_with_fingerprints_optimized(self) -> list[TemplateModel]:
        """Get all templates that have at least one fingerprint set (optimized with caching)."""
        cache_key = "templates_with_fingerprints"

        # Try cache first
        cached_result = self.query_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        with Session(self._engine) as session:
            templates = (
                session.query(TemplateModel)
                .filter(
                    TemplateModel.fingerprint_64.isnot(None)
                    | TemplateModel.fingerprint_128.isnot(None)
                    | TemplateModel.fingerprint_256.isnot(None)
                    | TemplateModel.fingerprint_512.isnot(None)
                    | TemplateModel.fingerprint_1024.isnot(None)
                )
                .all()
            )

            # Cache the result
            self.query_cache.put(cache_key, templates, ttl=60)  # Shorter TTL for this query
            return templates
    
    def perform_database_maintenance(self) -> None:
        """Perform database maintenance operations for optimal performance."""
        start_time = time.perf_counter()
        
        try:
            with Session(self._engine) as session:
                # Execute VACUUM to optimize database file
                session.execute(text("PRAGMA vacuum"))
                
                # Execute ANALYZE to update statistics
                session.execute(text("PRAGMA analyze"))
                
                session.commit()
            
            duration = time.perf_counter() - start_time
            self.performance_monitor.record_operation('database_maintenance', duration)
            self.logger.info(f"Database maintenance completed in {duration:.4f}s")
            
        except SQLAlchemyError as e:
            duration = time.perf_counter() - start_time
            self.performance_monitor.record_operation('database_maintenance', duration, False)
            self.logger.error(f"Database maintenance failed after {duration:.4f}s: {e}")
            raise
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        return self.query_cache.get_stats()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance monitoring statistics."""
        return self.performance_monitor.get_stats()
    
    def log_performance_summary(self) -> None:
        """Log performance summary."""
        self.performance_monitor.log_summary(self.logger)
    
    def log_detailed_performance_summary(self) -> None:
        """Log detailed performance summary with all metrics."""
        self.performance_monitor.log_detailed_summary(self.logger)
    

    def save_template(
        self, template_hash: str, fingerprints: Dict[int, int], working_window: int = DEFAULT_WORKING_WINDOW, optimal_batch_size: Optional[int] = None
    ) -> int:
        """Save or update template."""
        with Session(self._engine) as session:
            existing = session.query(TemplateModel).filter(TemplateModel.template_hash == template_hash).first()
            if existing:
                existing.working_window = working_window
                existing.optimal_batch_size = optimal_batch_size
                existing.updated_at = datetime.now()
                for res in DEFAULT_RESOLUTIONS:
                    if res in fingerprints:
                        setattr(existing, f"fingerprint_{res}", hex(fingerprints[res]))
                session.commit()
                return existing.id
            else:
                template = TemplateModel(
                    template_hash=template_hash,
                    working_window=working_window,
                    optimal_batch_size=optimal_batch_size if optimal_batch_size is not None else 32,  # Default batch size to avoid NOT NULL constraint
                    fingerprint_64=hex(fingerprints[64]) if 64 in fingerprints else None,
                    fingerprint_128=hex(fingerprints[128]) if 128 in fingerprints else None,
                    fingerprint_256=hex(fingerprints[256]) if 256 in fingerprints else None,
                    fingerprint_512=hex(fingerprints[512]) if 512 in fingerprints else None,
                    fingerprint_1024=hex(fingerprints[1024]) if 1024 in fingerprints else None,
                )
                session.add(template)
                session.commit()
                return template.id

    def update_template(self, template_id: int, new_distance: float, working_window: int, optimal_batch_size: Optional[int] = None) -> None:
        """Update template observation count, average distance, and working window if new value is greater."""
        with Session(self._engine) as session:
            template = session.query(TemplateModel).filter(TemplateModel.id == template_id).first()
            if template:
                template.observation_count += 1
                template.avg_distance = (
                    template.avg_distance * (template.observation_count - 1) + new_distance
                ) / template.observation_count
                # Only update working_window if new value is greater or less 15% than current value
                if working_window < template.working_window *.85 or working_window > template.working_window * 1.15:
                    template.working_window = working_window
                # Always set optimal_batch_size, using default if None is provided
                template.optimal_batch_size = optimal_batch_size if optimal_batch_size is not None else 32
                template.updated_at = datetime.now()
                session.commit()
    
    def batch_update_templates(self, updates: List[Dict[str, Any]]) -> None:
        """Batch update multiple templates efficiently using SQLAlchemy bulk operations."""
        if not updates:
            return

        start_time = time.perf_counter()
        try:
            # Collect all template IDs first
            template_ids = [u['template_id'] for u in updates]

            with Session(self._engine) as session:
                # Single query to fetch all templates at once
                templates = {t.id: t for t in session.query(TemplateModel).filter(TemplateModel.id.in_(template_ids)).all()}

                # Apply updates using O(1) dictionary lookup
                for update_data in updates:
                    template_id = update_data['template_id']
                    template = templates.get(template_id)
                    if template:
                        # Apply updates
                        if 'new_distance' in update_data:
                            template.observation_count += 1
                            template.avg_distance = (
                                template.avg_distance * (template.observation_count - 1) + update_data['new_distance']
                            ) / template.observation_count

                        if 'working_window' in update_data:
                            working_window = update_data['working_window']
                            if working_window < template.working_window *.85 or working_window > template.working_window * 1.15:
                                template.working_window = working_window

                        if 'optimal_batch_size' in update_data:
                            template.optimal_batch_size = update_data['optimal_batch_size']

                        template.updated_at = datetime.now()

                session.commit()

            duration = time.perf_counter() - start_time
            self.performance_monitor.record_operation('batch_update_templates', duration)
            self.logger.info(f"Batch updated {len(updates)} templates in {duration:.4f}s")

        except SQLAlchemyError as e:
            duration = time.perf_counter() - start_time
            self.performance_monitor.record_operation('batch_update_templates', duration, False)
            self.logger.error(f"Batch update failed after {duration:.4f}s: {e}")
            raise
    
    def batch_save_templates(self, templates_data: List[Dict[str, Any]]) -> List[int]:
        """Batch save multiple templates efficiently using bulk operations."""
        if not templates_data:
            return []
        
        start_time = time.perf_counter()
        template_ids = []
        
        try:
            with Session(self._engine) as session:
                # Separate new templates from updates for bulk operations
                new_templates = []
                existing_updates = []
                
                # Collect existing template hashes for batch lookup
                template_hashes = [td['template_hash'] for td in templates_data]
                existing_map = {t.template_hash: t for t in session.query(TemplateModel).filter(TemplateModel.template_hash.in_(template_hashes)).all()}

                for template_data in templates_data:
                    template_hash = template_data['template_hash']
                    fingerprints = template_data['fingerprints']
                    working_window = template_data.get('working_window', DEFAULT_WORKING_WINDOW)
                    optimal_batch_size = template_data.get('optimal_batch_size', 32)

                    existing = existing_map.get(template_hash)
                    if existing:
                        # Update existing template
                        existing.working_window = working_window
                        existing.optimal_batch_size = optimal_batch_size
                        existing.updated_at = datetime.now()
                        for res in DEFAULT_RESOLUTIONS:
                            if res in fingerprints:
                                setattr(existing, f"fingerprint_{res}", hex(fingerprints[res]))
                        template_ids.append(existing.id)
                    else:
                        # Prepare new template data for bulk insert
                        new_templates.append({
                            'template_hash': template_hash,
                            'working_window': working_window,
                            'optimal_batch_size': optimal_batch_size,
                            'fingerprint_64': hex(fingerprints[64]) if 64 in fingerprints else None,
                            'fingerprint_128': hex(fingerprints[128]) if 128 in fingerprints else None,
                            'fingerprint_256': hex(fingerprints[256]) if 256 in fingerprints else None,
                            'fingerprint_512': hex(fingerprints[512]) if 512 in fingerprints else None,
                            'fingerprint_1024': hex(fingerprints[1024]) if 1024 in fingerprints else None,
                            'observation_count': 0,
                            'avg_distance': 0.0,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now(),
                        })

                # Bulk insert new templates
                if new_templates:
                    # Use SQLAlchemy's bulk_insert_mappings for better performance
                    from sqlalchemy import insert
                    result = session.execute(
                        insert(TemplateModel).returning(TemplateModel.id),
                        new_templates
                    )
                    new_ids = [row[0] for row in result]
                    template_ids.extend(new_ids)
                
                session.commit()
            
            duration = time.perf_counter() - start_time
            self.performance_monitor.record_operation('batch_save_templates', duration)
            self.logger.info(f"Batch saved {len(templates_data)} templates in {duration:.4f}s")
            
            return template_ids
            
        except SQLAlchemyError as e:
            duration = time.perf_counter() - start_time
            self.performance_monitor.record_operation('batch_save_templates', duration, False)
            self.logger.error(f"Batch save failed after {duration:.4f}s: {e}")
            raise

    def get_templates_with_fingerprints(self) -> list[TemplateModel]:
        """Get all templates that have at least one fingerprint set."""
        with Session(self._engine) as session:
            return (
                session.query(TemplateModel)
                .filter(
                    TemplateModel.fingerprint_64.isnot(None)
                    | TemplateModel.fingerprint_128.isnot(None)
                    | TemplateModel.fingerprint_256.isnot(None)
                    | TemplateModel.fingerprint_512.isnot(None)
                    | TemplateModel.fingerprint_1024.isnot(None)
                )
                .all()
            )

    @staticmethod
    def _hex_to_int_cached(hex_str: Optional[str]) -> Optional[int]:
        """Convert hex string to integer with caching for performance."""
        if hex_str is None:
            return None
        # Use int() directly - Python caches small integers, and the conversion
        # itself is fast. The key optimization is avoiding repeated calls in loops.
        return int(hex_str, 16)

    def close(self) -> None:
        """Close the database engine."""
        if self._engine:
            self._engine.dispose()
