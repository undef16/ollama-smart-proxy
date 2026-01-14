"""SQLite adapter implementation for TemplateRepository port."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import Session

from ...ports.template_repository import TemplateRepository
from ...domain.template import Template
from ...const import (
    DEFAULT_WORKING_WINDOW,
    PRAGMA_JOURNAL_MODE,
    PRAGMA_SYNCHRONOUS,
    PRAGMA_CACHE_SIZE,
    DEFAULT_RESOLUTIONS,
)
from ...infrastructure.database.template_model import TemplateModel, Base
from .base_adapter import BaseTemplateRepository


class SQLiteTemplateRepository(BaseTemplateRepository):
    """SQLite implementation of TemplateRepository port interface."""
    
    _TemplateModel = TemplateModel
    
    def __init__(self, db_path: Path, check_same_thread: bool = False):
        """Initialize SQLite template repository.

        Args:
            db_path: Path to SQLite database file
            check_same_thread: For SQLite thread safety (default False)
        """
        self.db_path = db_path
        # Ensure the directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": check_same_thread}
        )
        self._register_sqlite_pragmas()
        Base.metadata.create_all(self._engine)
    
    # =========================================================================
    # Database-specific setup methods
    # =========================================================================
    
    @staticmethod
    def _register_hamming_distance(connection):
        """Register the hamming_distance SQLite custom function for similarity matching."""
        def hamming_distance_func(a, b):
            # Convert hex strings to integers if needed
            try:
                if isinstance(a, str):
                    a = int(a, 16) if a.startswith('0x') else int(a, 16)
                if isinstance(b, str):
                    b = int(b, 16) if b.startswith('0x') else int(b, 16)
            except (ValueError, TypeError):
                # If conversion fails, return None
                return None
            return bin(a ^ b).count("1") if a is not None and b is not None else None

        connection.create_function(
            "hamming_distance",
            2,
            hamming_distance_func
        )
    
    def _register_sqlite_pragmas(self):
        """Set SQLite PRAGMAs on connection and register UDFs."""
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            # Get the raw sqlite3 connection
            raw_conn = dbapi_connection.connection if hasattr(dbapi_connection, 'connection') else dbapi_connection
            # Use raw string for SQLite PRAGMAs
            raw_conn.execute(PRAGMA_JOURNAL_MODE)
            raw_conn.execute(PRAGMA_SYNCHRONOUS)
            raw_conn.execute(PRAGMA_CACHE_SIZE)
            self._register_hamming_distance(raw_conn)
    
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
        """Create a new template in SQLite."""
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
        """Update an existing template in SQLite."""
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
        """Update fingerprints for a template in SQLite."""
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
        """Commit the current transaction in SQLite."""
        # Session context handles commit, this is for direct commits if needed
        pass
    
    def _bulk_insert(self, templates_data: List[Dict[str, Any]]) -> List[int]:
        """Bulk insert new templates into SQLite."""
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
        """Find a template with similar fingerprint using similarity matching.
        
        Args:
            resolution: 64, 128, 256, 512, or 1024
            fingerprint: The fingerprint to match
            threshold: Hamming distance threshold
            
        Returns:
            Matching Template domain entity or None if not found
        """
        col_name = f"fingerprint_{resolution}"
        
        with Session(self._engine) as session:
            # Use SQL-level filtering with hamming_distance UDF
            query = text(f"""
                SELECT id, template_hash, working_window, observation_count, avg_distance, 
                       optimal_batch_size, fingerprint_64, fingerprint_128, fingerprint_256, 
                       fingerprint_512, fingerprint_1024, created_at, updated_at
                FROM templates 
                WHERE {col_name} IS NOT NULL 
                AND hamming_distance({col_name}, :fingerprint) <= :threshold
                LIMIT 1
            """)
            
            result = session.execute(query, {"fingerprint": fingerprint, "threshold": threshold})
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
        """Close the database connection."""
        if self._engine:
            self._engine.dispose()
