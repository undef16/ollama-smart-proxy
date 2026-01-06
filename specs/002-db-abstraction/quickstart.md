# Quickstart: Configurable Database Abstraction

## Overview

This feature adds the ability to switch between SQLite and PostgreSQL databases in the optimizer plugin using a configurable abstraction layer.

## Quick Start for Developers

### 1. Understanding the Current State

The current architecture has tight coupling:
```
OptimizerAgent → DatabaseManager (SQLite only)
```

The target architecture:
```
OptimizerAgent → TemplateRepository (Port)
                      ↓
            ┌───────┴───────┐
            ↓               ↓
    SQLiteAdapter    PostgreSQLAdapter
```

### 2. Configuration

**For SQLite (default)**:
```json
{
  "database_type": "sqlite",
  "database_path": "./data/optimizer_stats.db"
}
```

**For PostgreSQL**:
```json
{
  "database_type": "postgres",
  "postgres_connection_string": "postgresql://user:password@localhost:5432/optimizer"
}
```

### 3. Implementation Order

1. **Update Config class** - Add database configuration options
2. **Create TemplateRepository port** - Define the interface
3. **Create SQLite adapter** - Implement port with existing logic
4. **Create PostgreSQL adapter** - Implement with pg_trgm
5. **Create DatabaseFactory** - Instantiate correct adapter
6. **Update OptimizerAgent** - Use repository abstraction
7. **Add tests** - Unit and integration tests

### 4. Key Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/plugins/optimizer/ports/template_repository.py` | Create | Port interface |
| `src/plugins/optimizer/adapters/sqlite_adapter.py` | Create | SQLite implementation |
| `src/plugins/optimizer/adapters/postgres_adapter.py` | Create | PostgreSQL implementation |
| `src/plugins/optimizer/domain/template.py` | Create | Domain entity |
| `src/plugins/optimizer/factory/database_factory.py` | Create | Factory class |
| `src/shared/config.py` | Modify | Add database config |
| `src/plugins/optimizer/agent.py` | Modify | Use repository |
| `src/plugins/optimizer/db_utils.py` | Modify | Refactor existing |

### 5. Testing the Implementation

**Unit Test (mocked database)**:
```python
def test_template_matching_with_mock():
    mock_repo = Mock(spec=TemplateRepository)
    mock_repo.find_by_hash.return_value = Template(...)
    agent = OptimizerAgent(repository=mock_repo)
    # ... test logic
```

**Integration Test (SQLite)**:
```python
def test_sqlite_integration():
    repo = SQLiteTemplateRepository(db_path=":memory:")
    # ... test CRUD operations
```

**Integration Test (PostgreSQL)**:
```python
@pytest.mark.postgres
def test_postgres_integration():
    repo = PostgreSQLTemplateRepository(connection_string="...")
    # ... test CRUD operations
```

### 6. Similarity Matching

**SQLite**: Uses custom `hamming_distance` UDF
**PostgreSQL**: Uses built-in `similarity()` function from `pg_trgm`

Both must return equivalent results for template matching to work correctly.

### 7. Migration Notes

- No automatic data migration between databases
- Users must manually export/import data if switching
- Consider adding a CLI tool for data migration in a future phase

### 8. Verification Checklist

- [ ] SQLite tests pass
- [ ] PostgreSQL tests pass
- [ ] Configuration validation works
- [ ] Error messages are clear
- [ ] Performance is acceptable
