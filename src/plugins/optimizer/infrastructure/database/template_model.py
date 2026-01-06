"""Database utilities for Optimizer Agent using SQLAlchemy."""

from typing import Dict, Optional
from datetime import datetime

from sqlalchemy import Integer, String, Float, Text, TIMESTAMP, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
from ...const import DEFAULT_WORKING_WINDOW


def _hex_to_int(hex_str):
    """Convert hex string to integer."""
    if hex_str is None:
        return None
    return int(hex_str, 16)


class TemplateModel(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    working_window: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_WORKING_WINDOW)
    observation_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    avg_distance: Mapped[float] = mapped_column(Float, default=0.0)
    optimal_batch_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=32)  # New field for batch size optimization
    fingerprint_64: Mapped[Optional[str]] = mapped_column(Text, index=True)
    fingerprint_128: Mapped[Optional[str]] = mapped_column(Text, index=True)
    fingerprint_256: Mapped[Optional[str]] = mapped_column(Text, index=True)
    fingerprint_512: Mapped[Optional[str]] = mapped_column(Text)
    fingerprint_1024: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Additional indexes for performance optimization
    __table_args__ = (
        Index('idx_fingerprint_64', 'fingerprint_64'),
        Index('idx_fingerprint_128', 'fingerprint_128'),
        Index('idx_observation_count', 'observation_count'),
        {"extend_existing": True}
    )

    @property
    def fingerprint_64_int(self):
        """Get fingerprint_64 as integer (cached conversion)."""
        return _hex_to_int(self.fingerprint_64)

    @property
    def fingerprint_128_int(self):
        """Get fingerprint_128 as integer (cached conversion)."""
        return _hex_to_int(self.fingerprint_128)

    @property
    def fingerprint_256_int(self):
        """Get fingerprint_256 as integer (cached conversion)."""
        return _hex_to_int(self.fingerprint_256)

    @property
    def fingerprint_512_int(self):
        """Get fingerprint_512 as integer (cached conversion)."""
        return _hex_to_int(self.fingerprint_512)

    @property
    def fingerprint_1024_int(self):
        """Get fingerprint_1024 as integer (cached conversion)."""
        return _hex_to_int(self.fingerprint_1024)

    @property
    def fingerprints(self) -> Dict[int, int]:
        """Get fingerprints as dict."""
        fps = {}
        if self.fingerprint_64 is not None:
            fps[64] = _hex_to_int(self.fingerprint_64)
        if self.fingerprint_128 is not None:
            fps[128] = _hex_to_int(self.fingerprint_128)
        if self.fingerprint_256 is not None:
            fps[256] = _hex_to_int(self.fingerprint_256)
        if self.fingerprint_512 is not None:
            fps[512] = _hex_to_int(self.fingerprint_512)
        if self.fingerprint_1024 is not None:
            fps[1024] = _hex_to_int(self.fingerprint_1024)
        return fps
