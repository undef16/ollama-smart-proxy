"""Database utilities for Optimizer Agent using SQLAlchemy."""

import threading
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from sqlalchemy import create_engine, Integer, String, Float, Text, TIMESTAMP, func, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from .const import (
    DEFAULT_WORKING_WINDOW,
    PRAGMA_JOURNAL_MODE,
    PRAGMA_SYNCHRONOUS,
    PRAGMA_CACHE_SIZE,
    DEFAULT_RESOLUTIONS,
)


class Base(DeclarativeBase):
    pass


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    working_window: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_WORKING_WINDOW)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_distance: Mapped[float] = mapped_column(Float, default=0.0)
    optimal_batch_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=32)  # New field for batch size optimization
    fingerprint_64: Mapped[Optional[str]] = mapped_column(Text)
    fingerprint_128: Mapped[Optional[str]] = mapped_column(Text)
    fingerprint_256: Mapped[Optional[str]] = mapped_column(Text)
    fingerprint_512: Mapped[Optional[str]] = mapped_column(Text)
    fingerprint_1024: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    @property
    def fingerprints(self) -> Dict[int, int]:
        """Get fingerprints as dict."""
        fps = {}
        if self.fingerprint_64 is not None:
            fps[64] = int(self.fingerprint_64, 16)
        if self.fingerprint_128 is not None:
            fps[128] = int(self.fingerprint_128, 16)
        if self.fingerprint_256 is not None:
            fps[256] = int(self.fingerprint_256, 16)
        if self.fingerprint_512 is not None:
            fps[512] = int(self.fingerprint_512, 16)
        if self.fingerprint_1024 is not None:
            fps[1024] = int(self.fingerprint_1024, 16)
        return fps


class DatabaseManager:
    """Thread-safe SQLite database manager for optimizer statistics using SQLAlchemy."""

    _instance: Optional["DatabaseManager"] = None
    _engine = None
    _lock = threading.Lock()

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

                    Base.metadata.create_all(cls._engine)
        return cls._instance

    def __init__(self, db_path: Path):
        if not hasattr(self, "_initialized"):
            self.db_path = db_path
            self._initialized = True

    def get_template_by_hash(self, template_hash: str) -> Optional[Template]:
        """Get template by hash."""
        with Session(self._engine) as session:
            return session.query(Template).filter(Template.template_hash == template_hash).first()

    def get_template_by_fingerprint(self, resolution: int, fingerprint: int, threshold: int) -> Optional[Template]:
        """Find template with similar fingerprint."""
        col_name = f"fingerprint_{resolution}"
        with Session(self._engine) as session:
            templates = session.query(Template).filter(getattr(Template, col_name).isnot(None)).all()
            for template in templates:
                stored_fp_hex = getattr(template, col_name)
                if stored_fp_hex is not None:
                    stored_fp = int(stored_fp_hex, 16)
                    distance = bin(stored_fp ^ fingerprint).count("1")
                    if distance <= threshold:
                        return template
        return None

    def save_template(
        self, template_hash: str, fingerprints: Dict[int, int], working_window: int = DEFAULT_WORKING_WINDOW, optimal_batch_size: Optional[int] = None
    ) -> int:
        """Save or update template."""
        with Session(self._engine) as session:
            existing = session.query(Template).filter(Template.template_hash == template_hash).first()
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
                template = Template(
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
            template = session.query(Template).filter(Template.id == template_id).first()
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

    def get_templates_with_fingerprints(self) -> list[Template]:
        """Get all templates that have at least one fingerprint set."""
        with Session(self._engine) as session:
            return (
                session.query(Template)
                .filter(
                    Template.fingerprint_64.isnot(None)
                    | Template.fingerprint_128.isnot(None)
                    | Template.fingerprint_256.isnot(None)
                    | Template.fingerprint_512.isnot(None)
                    | Template.fingerprint_1024.isnot(None)
                )
                .all()
            )

    def close(self) -> None:
        """Close the database engine."""
        if self._engine:
            self._engine.dispose()
