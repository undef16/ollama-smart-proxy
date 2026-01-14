"""PostgreSQL adapter implementation for TemplateRepository port."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from ...ports.template_repository import TemplateRepository
from ...domain.template import Template
from ...const import (
    DEFAULT_WORKING_WINDOW,
    DEFAULT_RESOLUTIONS,
)
from ...infrastructure.database.template_model import TemplateModel, Base
from .base_adapter import BaseTemplateRepository


class PostgreSQLTemplateRepository(BaseTemplateRepository):
    """PostgreSQL implementation of TemplateRepository port interface."""
    
    _TemplateModel = TemplateModel
    
    def __init__(self, connection_string: str, pool_size: int = 5, max_overflow: int = 10):
        """Initialize PostgreSQL template repository.

        Args:
            connection_string: PostgreSQL connection URI (postgresql://user:pass@host:port/db)
            pool_size: Number of connections to maintain in the pool
            max_overflow: Additional connections allowed beyond pool_size
        """
        self.connection_string = connection_string
        self._ensure_database_exists()
        self._engine = create_engine(
            connection_string,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Enable connection health checks
        )
        self._ensure_pg_trgm_extension()
        Base.metadata.create_all(self._engine)
    
    # =========================================================================
    # Database-specific setup methods
    # =========================================================================

    def _ensure_database_exists(self):
        """Ensure the target database exists, creating it if necessary."""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Parse the connection string
            parsed = urlparse(self.connection_string)
            db_name = parsed.path.lstrip('/')

            logger.info(f"Checking database existence for: {db_name}")

            if not db_name:
                raise ValueError("Database name not found in connection string")

            # Create connection string for the admin database (postgres)
            admin_url = parsed._replace(path='/postgres')
            admin_connection_string = urlunparse(admin_url)

            logger.debug(f"Admin connection string: {admin_connection_string.replace(parsed.password or '', '***')}")

            # Try to connect to the target database first
            try:
                logger.info(f"Attempting to connect to target database: {db_name}")
                test_engine = create_engine(self.connection_string)
                test_engine.dispose()
                logger.info(f"Database {db_name} already exists")
                return  # Database exists
            except OperationalError as e:
                logger.info(f"Database {db_name} does not exist (OperationalError: {e}), will attempt to create it")

            # Connect to admin database and create the target database
            logger.info(f"Connecting to admin database to create {db_name}")
            admin_engine = create_engine(admin_connection_string)
            with admin_engine.connect() as conn:
                # Use text() to safely execute the CREATE DATABASE statement
                logger.info(f"Executing: CREATE DATABASE {db_name}")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                conn.commit()
                logger.info(f"Successfully created database: {db_name}")
            admin_engine.dispose()

        except Exception as e:
            # Log the error but don't fail - the database might already exist or creation might not be allowed
            logger = logging.getLogger(__name__)
            logger.error(f"Could not ensure database exists: {e}", exc_info=True)

    def _ensure_pg_trgm_extension(self):
        """Ensure pg_trgm extension is enabled."""
        with self._engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            conn.commit()
    
    # =========================================================================
    # Domain conversion methods
    # =========================================================================
    
    def _to_template_domain(self, template: TemplateModel) -> Template:
        """Convert TemplateModel to Template domain entity."""
        return Template(
            id=template.id,
            template_hash=template.template_hash,
            working_window=template.working_window,
            observation_count=template.observation_count,
            avg_distance=template.avg_distance,
            optimal_batch_size=template.optimal_batch_size,
            fingerprint_64=template.fingerprint_64,
            fingerprint_128=template.fingerprint_128,
            fingerprint_256=template.fingerprint_256,
            fingerprint_512=template.fingerprint_512,
            fingerprint_1024=template.fingerprint_1024,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
    
    # =========================================================================
    # Abstract method implementations
    # =========================================================================
    
    def _find_by_hash(self, template_hash: str) -> Optional[Template]:
        """Find a template by its hash."""
        with Session(self._engine) as session:
            template = session.query(TemplateModel).filter(
                TemplateModel.template_hash == template_hash
            ).first()
            return self._to_template_domain(template) if template else None
    
    def _find_by_id(self, template_id: int) -> Optional[Template]:
        """Find a template by its ID."""
        with Session(self._engine) as session:
            template = session.query(TemplateModel).filter(
                TemplateModel.id == template_id
            ).first()
            return self._to_template_domain(template) if template else None
    
    def _find_by_hashes(self, template_hashes: List[str]) -> Dict[str, Template]:
        """Find multiple templates by their hashes."""
        with Session(self._engine) as session:
            templates = session.query(TemplateModel).filter(
                TemplateModel.template_hash.in_(template_hashes)
            ).all()
            return {t.template_hash: self._to_template_domain(t) for t in templates}
    
    def _find_by_ids(self, template_ids: List[int]) -> Dict[int, Template]:
        """Find multiple templates by their IDs."""
        with Session(self._engine) as session:
            templates = session.query(TemplateModel).filter(
                TemplateModel.id.in_(template_ids)
            ).all()
            return {t.id: self._to_template_domain(t) for t in templates}
    
    def _create_template(
        self,
        template_hash: str,
        fingerprints: Dict[int, int],
        working_window: int,
        optimal_batch_size: Optional[int] = None
    ) -> int:
        """Create a new template in PostgreSQL."""
        with Session(self._engine) as session:
            template = TemplateModel(
                template_hash=template_hash,
                working_window=working_window,
                optimal_batch_size=optimal_batch_size if optimal_batch_size is not None else 32,
                fingerprint_64=hex(fingerprints[64])[2:] if 64 in fingerprints and fingerprints[64] is not None else None,
                fingerprint_128=hex(fingerprints[128])[2:] if 128 in fingerprints and fingerprints[128] is not None else None,
                fingerprint_256=hex(fingerprints[256])[2:] if 256 in fingerprints and fingerprints[256] is not None else None,
                fingerprint_512=hex(fingerprints[512])[2:] if 512 in fingerprints and fingerprints[512] is not None else None,
                fingerprint_1024=hex(fingerprints[1024])[2:] if 1024 in fingerprints and fingerprints[1024] is not None else None,
            )
            session.add(template)
            session.commit()
            return template.id
    
    def _update_existing_template(
        self,
        template_id: int,
        working_window: int,
        optimal_batch_size: Optional[int],
        fingerprints: Optional[Dict[int, int]] = None,
        observation_count: Optional[int] = None,
        avg_distance: Optional[float] = None
    ) -> int:
        """Update an existing template in PostgreSQL."""
        with Session(self._engine) as session:
            template = session.query(TemplateModel).filter(
                TemplateModel.id == template_id
            ).first()

            if template:
                if observation_count is not None:
                    template.observation_count = observation_count
                if avg_distance is not None:
                    template.avg_distance = avg_distance

                template.working_window = working_window
                template.optimal_batch_size = optimal_batch_size if optimal_batch_size is not None else 32
                template.updated_at = datetime.now()

                if fingerprints:
                    for res in DEFAULT_RESOLUTIONS:
                        if res in fingerprints:
                            setattr(template, f"fingerprint_{res}", hex(fingerprints[res])[2:])

                session.commit()

            return template_id
    
    def _update_fingerprints(self, template_id: int, fingerprints: Dict[int, int]) -> None:
        """Update fingerprints for a template in PostgreSQL."""
        with Session(self._engine) as session:
            template = session.query(TemplateModel).filter(
                TemplateModel.id == template_id
            ).first()

            if template:
                for res in DEFAULT_RESOLUTIONS:
                    if res in fingerprints:
                        setattr(template, f"fingerprint_{res}", hex(fingerprints[res])[2:])
                template.updated_at = datetime.now()
                session.commit()
    
    def _commit(self) -> None:
        """Commit the current transaction in PostgreSQL."""
        # Session context handles commit, this is for direct commits if needed
        pass
    
    def _bulk_insert(self, templates_data: List[Dict[str, Any]]) -> List[int]:
        """Bulk insert new templates into PostgreSQL."""
        # Convert fingerprints to hex format for storage
        processed_data = []
        for template_data in templates_data:
            processed_item = template_data.copy()
            # Check if there's a 'fingerprints' dict to expand
            if 'fingerprints' in processed_item:
                fingerprints = processed_item['fingerprints']
                # Expand the 'fingerprints' dict to individual fingerprint columns
                for res in [64, 128, 256, 512, 1024]:
                    if isinstance(fingerprints, dict) and res in fingerprints and fingerprints[res] is not None:
                        processed_item[f'fingerprint_{res}'] = hex(fingerprints[res])[2:]
                    else:
                        processed_item[f'fingerprint_{res}'] = None
                # Remove the original 'fingerprints' key since it's not a column in TemplateModel
                del processed_item['fingerprints']
            else:
                # If no 'fingerprints' dict, convert individual fingerprint values to hex
                for res in [64, 128, 256, 512, 1024]:
                    key = f'fingerprint_{res}'
                    if key in processed_item and processed_item[key] is not None:
                        processed_item[key] = hex(processed_item[key])[2:]
            processed_data.append(processed_item)

        with Session(self._engine) as session:
            from sqlalchemy import insert
            result = session.execute(
                insert(TemplateModel).returning(TemplateModel.id),
                processed_data
            )
            new_ids = [row[0] for row in result]
            session.commit()
            return new_ids
    
    # =========================================================================
    # Port interface methods (not in base class)
    # =========================================================================
    
    def find_by_fingerprint(
        self,
        resolution: int,
        fingerprint: int,
        threshold: int
    ) -> Optional[Template]:
        """Find a template with similar fingerprint using pg_trgm similarity matching.
        
        pg_trgm uses text similarity (0-1) where 1 is identical. We convert the hamming
        distance threshold to a similarity threshold for matching.
        
        Args:
            resolution: 64, 128, 256, 512, or 1024
            fingerprint: The fingerprint to match (integer)
            threshold: Maximum hamming distance threshold
            
        Returns:
            Matching Template domain entity or None if not found
        """
        col_name = f"fingerprint_{resolution}"
        fingerprint_hex = hex(fingerprint)[2:]
        
        # Convert hamming distance threshold to similarity threshold
        # Lower hamming distance = higher similarity
        # Similarity = 1 - (hamming_distance / max_bits)
        # We invert it for pg_trgm: if threshold is small, we need high similarity
        max_bits = resolution
        similarity_threshold = 1.0 - (threshold / max_bits)
        # Ensure minimum similarity threshold for pg_trgm to work effectively
        similarity_threshold = max(0.3, min(0.9, similarity_threshold))
        
        with Session(self._engine) as session:
            # Use pg_trgm similarity function for fuzzy matching
            query = text(f"""
                SELECT * FROM templates
                WHERE {col_name} IS NOT NULL
                AND {col_name} % :fingerprint_hex
                ORDER BY similarity({col_name}, :fingerprint_hex) DESC
                LIMIT 1
            """)

            result = session.execute(query, {"fingerprint_hex": fingerprint_hex})
            row = result.fetchone()

            if row:
                template = session.query(TemplateModel).filter(
                    TemplateModel.id == row[0]
                ).first()
                return self._to_template_domain(template) if template else None
        
        return None
    
    def get_all_with_fingerprints(self) -> List[Template]:
        """Get all templates that have at least one fingerprint set.
        
        Returns:
            List of Template domain entities
        """
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
            return [self._to_template_domain(t) for t in templates]
    
    def close(self) -> None:
        """Close the database connection and dispose of the engine."""
        if self._engine:
            self._engine.dispose()
    
    def vacuum_analyze(self) -> None:
        """Run VACUUM ANALYZE to update statistics for query planner.
        
        PostgreSQL equivalent of SQLite's PRAGMA vacuum and PRAGMA analyze.
        """
        # VACUUM cannot run inside a transaction block
        from psycopg2 import sql
        conn = self._engine.raw_connection()
        try:
            # Set isolation level to AUTOCOMMIT for VACUUM to work
            old_isolation_level = conn.isolation_level
            conn.set_isolation_level(0)  # 0 = AUTOCOMMIT
            try:
                cursor = conn.cursor()
                cursor.execute("VACUUM ANALYZE templates")
                cursor.close()
            finally:
                conn.set_isolation_level(old_isolation_level)
        finally:
            conn.close()
    
    def analyze(self) -> None:
        """Run ANALYZE to update statistics for query planner.
        
        PostgreSQL equivalent of SQLite's PRAGMA analyze.
        """
        # ANALYZE cannot run inside a transaction block
        conn = self._engine.raw_connection()
        try:
            # Set isolation level to AUTOCOMMIT for ANALYZE to work
            old_isolation_level = conn.isolation_level
            conn.set_isolation_level(0)  # 0 = AUTOCOMMIT
            try:
                cursor = conn.cursor()
                cursor.execute("ANALYZE templates")
                cursor.close()
            finally:
                conn.set_isolation_level(old_isolation_level)
        finally:
            conn.close()
