"""Adapters for database storage implementations."""

from .base_adapter import BaseTemplateRepository
from .sqlite_adapter import SQLiteTemplateRepository

__all__ = ["BaseTemplateRepository", "SQLiteTemplateRepository"]
