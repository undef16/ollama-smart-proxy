# Technical Plan: Configurable Database Abstraction

## Overview

This plan outlines the implementation steps for adding configurable database support (SQLite/PostgreSQL) to the optimizer plugin using a gradual Hexagonal Architecture migration approach.

## Architecture Design

### Port Interface: TemplateRepository

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path

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
        """Find template by its hash."""
        pass

    @abstractmethod
    def find_by_fingerprint(
        self,
        resolution: int,
        fingerprint: int,
        threshold: int
    ) -> Optional[Any]:
        """Find template with similar fingerprint."""
        pass

    @abstractmethod
    def update_template(
        self,
        template_id: int,
        new_distance: float,
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
        """Batch save multiple templates."""
        pass

    @abstractmethod
    def batch_update_templates(
        self,
        updates: List[Dict[str, Any]]
    ) -> None:
        """Batch update multiple templates."""
        pass

    @abstractmethod
    def get_all_with_fingerprints(self) -> List[Any]:
        """Get all templates with fingerprints set."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass
```

### Database Factory

```python
from enum import Enum
from typing import Optional

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"

class DatabaseFactory:
    """Factory for creating database adapters based on configuration."""

    @staticmethod
    def create_repository(
        db_type: DatabaseType,
        **kwargs
    ) -> TemplateRepository:
        """Create and return the appropriate repository adapter."""
        if db_type == DatabaseType.SQLITE:
            return SQLiteTemplateRepository(**kwargs)
        elif db_type == DatabaseType.POSTGRES:
            return PostgreSQLTemplateRepository(**kwargs)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
```

## Implementation Steps

### Phase 1: Configuration Updates

1. **Update Config class** to add database configuration:
   - `database_type: str = "sqlite"`
   - `database_path: Optional[Path] = None` (for SQLite)
   - `postgres_connection_string: Optional[str] = None`

2. **Update config.json schema** with new database settings.

### Phase 2: Port Interface Definition

1. **Create TemplateRepository port** in `src/plugins/optimizer/ports/`
2. **Define abstract methods** matching current DatabaseManager operations
3. **Create domain entity** Template class

### Phase 3: SQLite Adapter Implementation

1. **Create SQLite adapter** implementing TemplateRepository
2. **Refactor existing DatabaseManager** logic into the adapter
3. **Preserve hamming_distance UDF** for SQLite similarity matching
4. **Maintain PRAGMA settings** for performance

### Phase 4: PostgreSQL Adapter Implementation

1. **Create PostgreSQL adapter** implementing TemplateRepository
2. **Implement similarity matching** using PostgreSQL's `pg_trgm` extension
3. **Replace PRAGMA statements** with PostgreSQL equivalent commands
4. **Handle connection pooling** via SQLAlchemy

### Phase 5: Factory Integration

1. **Create DatabaseFactory** class
2. **Update OptimizerAgent** to use factory for repository creation
3. **Add configuration validation** at startup

### Phase 6: Testing

1. **Create unit tests** with mocked repository
2. **Create integration tests** for SQLite
3. **Create integration tests** for PostgreSQL
4. **Verify backward compatibility**

## File Structure

```
src/plugins/optimizer/
├── ports/
│   └── __init__.py
│   └── template_repository.py  # Port interface
├── adapters/
│   ├── __init__.py
│   ├── sqlite_adapter.py       # SQLite implementation
│   └── postgres_adapter.py     # PostgreSQL implementation
├── domain/
│   ├── __init__.py
│   └── template.py             # Domain entity
├── factory/
│   ├── __init__.py
│   └── database_factory.py     # Factory for adapter creation
├── db_utils.py                 # Existing (to be refactored)
└── agent.py                    # To be updated
```

## Key Differences: SQLite vs PostgreSQL

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Similarity Matching | hamming_distance UDF | pg_trgm extension (similarity function) |
| Pruning | PRAGMA vacuum | VACUUM ANALYZE |
| Indexes | Automatic with CREATE INDEX | Same, but with different options |
| Connection | File-based | TCP connection with pooling |
| Concurrency | WAL mode | Row-level locking |

## Migration Strategy

1. **No breaking changes** - existing SQLite users unaffected
2. **Feature flag approach** - PostgreSQL opt-in via config
3. **Gradual refactoring** - keep existing code working while adding new
4. **Tests first** - add tests before refactoring each component

## Success Metrics

- [ ] All existing SQLite tests pass
- [ ] New PostgreSQL integration tests pass
- [ ] Zero regression in optimizer functionality
- [ ] Configuration validated at startup
- [ ] Clear error messages for misconfiguration
