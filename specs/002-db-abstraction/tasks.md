# Implementation Tasks: Configurable Database Abstraction

## Phase 1: Configuration Updates

### Task 1.1: Update Config Class
**Status**: Pending  
**Priority**: P1

**Description**: Add database configuration options to the Config class.

**Changes**:
- Add `database_type: str = "sqlite"` setting
- Add `database_path: Optional[Path] = None` for SQLite
- Add `postgres_connection_string: Optional[str] = None` for PostgreSQL
- Add environment variable support: `OLLAMA_PROXY_DATABASE_TYPE`, etc.

**Files Modified**:
- `src/shared/config.py`

**Acceptance Criteria**:
- [ ] Config accepts database_type with valid values
- [ ] Config accepts SQLite path configuration
- [ ] Config accepts PostgreSQL connection string
- [ ] Environment variables override config file
- [ ] Default values match existing behavior (SQLite)

---

### Task 1.2: Update config.json Schema
**Status**: Pending  
**Priority**: P1

**Description**: Add database configuration to the sample config file.

**Changes**:
- Add database configuration section with examples for both SQLite and PostgreSQL

**Files Modified**:
- `config.json`

**Acceptance Criteria**:
- [ ] Config file has examples for both database types
- [ ] Comments explain configuration options
- [ ] Default values are documented

---

## Phase 2: Port Interface Definition

### Task 2.1: Create TemplateRepository Port
**Status**: Pending  
**Priority**: P1

**Description**: Create the abstract base class defining template storage operations.

**New Files**:
- `src/plugins/optimizer/ports/__init__.py`
- `src/plugins/optimizer/ports/template_repository.py`

**Interface Methods**:
- `save_template(template_hash, fingerprints, working_window, optimal_batch_size) -> int`
- `find_by_hash(template_hash) -> Optional[Template]`
- `find_by_fingerprint(resolution, fingerprint, threshold) -> Optional[Template]`
- `update_template(template_id, new_distance, working_window, optimal_batch_size) -> None`
- `batch_save_templates(templates_data) -> List[int]`
- `batch_update_templates(updates) -> None`
- `get_all_with_fingerprints() -> List[Template]`
- `close() -> None`

**Acceptance Criteria**:
- [ ] Port interface defines all required operations
- [ ] Interface is abstract (no implementation)
- [ ] Type hints are correct
- [ ] Port is importable from `src.plugins.optimizer.ports`

---

### Task 2.2: Create Template Domain Entity
**Status**: Pending  
**Priority**: P1

**Description**: Create the domain entity class representing a template.

**New Files**:
- `src/plugins/optimizer/domain/__init__.py`
- `src/plugins/optimizer/domain/template.py`

**Entity Attributes**:
- `id: int`
- `template_hash: str`
- `working_window: int`
- `observation_count: int`
- `avg_distance: float`
- `optimal_batch_size: Optional[int]`
- `fingerprints: Dict[int, int]` (computed property)
- `created_at: datetime`
- `updated_at: datetime`

**Acceptance Criteria**:
- [ ] Entity has all required attributes
- [ ] Fingerprints are accessible as computed property
- [ ] Entity can be used in both adapters
- [ ] Entity is serializable to/from database rows

---

## Phase 3: SQLite Adapter Implementation

### Task 3.1: Create SQLite Adapter
**Status**: Pending  
**Priority**: P1

**Description**: Implement TemplateRepository port using SQLite.

**New Files**:
- `src/plugins/optimizer/adapters/__init__.py`
- `src/plugins/optimizer/adapters/sqlite_adapter.py`

**Implementation Details**:
- Refactor existing `DatabaseManager` logic
- Preserve `hamming_distance` UDF
- Maintain PRAGMA settings (journal_mode, synchronous, cache_size)
- Use existing Template model or map to domain entity

**Acceptance Criteria**:
- [ ] All port interface methods implemented
- [ ] hamming_distance UDF works correctly
- [ ] PRAGMA settings applied on connection
- [ ] Performance matches existing implementation
- [ ] Existing tests pass without modification

---

## Phase 4: PostgreSQL Adapter Implementation

### Task 4.1: Create PostgreSQL Adapter
**Status**: Pending  
**Priority**: P2

**Description**: Implement TemplateRepository port using PostgreSQL.

**New Files**:
- `src/plugins/optimizer/adapters/postgres_adapter.py`

**Implementation Details**:
- Use `pg_trgm` extension for similarity matching
- Replace PRAGMA with PostgreSQL equivalents (VACUUM ANALYZE)
- Handle connection pooling via SQLAlchemy
- Use parameterized queries for security

**Similarity Matching**:
```python
# PostgreSQL uses pg_trgm's similarity() function
# Instead of hamming_distance UDF
SELECT * FROM templates
WHERE fingerprint_{resolution} IS NOT NULL
AND similarity(fingerprint_{resolution}, :fingerprint) > :threshold
ORDER BY similarity(fingerprint_{resolution}, :fingerprint) DESC
LIMIT 1
```

**Acceptance Criteria**:
- [ ] All port interface methods implemented
- [ ] Similarity matching works with pg_trgm
- [ ] Connection pooling is configured
- [ ] Error handling is appropriate
- [ ] Integration tests pass

---

## Phase 5: Factory Integration

### Task 5.1: Create Database Factory
**Status**: Pending  
**Priority**: P1

**Description**: Create factory class to instantiate the correct adapter.

**New Files**:
- `src/plugins/optimizer/factory/__init__.py`
- `src/plugins/optimizer/factory/database_factory.py`

**Factory Logic**:
- Read database_type from config
- Validate required settings for each type
- Instantiate appropriate adapter
- Return configured repository

**Acceptance Criteria**:
- [ ] Factory creates SQLite adapter for "sqlite" type
- [ ] Factory creates PostgreSQL adapter for "postgres" type
- [ ] Invalid database type raises ValueError
- [ ] Missing configuration raises appropriate error

---

### Task 5.2: Update OptimizerAgent
**Status**: Pending  
**Priority**: P1

**Description**: Refactor OptimizerAgent to use the repository abstraction.

**Files Modified**:
- `src/plugins/optimizer/agent.py`

**Changes**:
- Inject TemplateRepository in constructor
- Replace `self.db` calls with repository calls
- Remove direct DatabaseManager instantiation
- Add factory usage for repository creation

**Before**:
```python
self.db = DatabaseManager(db_path)
```

**After**:
```python
self.repository = DatabaseFactory.create_repository(
    database_type=config.database_type,
    **config.get_database_kwargs()
)
```

**Acceptance Criteria**:
- [ ] OptimizerAgent uses repository interface
- [ ] DatabaseManager instantiation is removed
- [ ] All existing functionality works
- [ ] Dependency injection enables testing

---

## Phase 6: Testing

### Task 6.1: Create Unit Tests
**Status**: Pending  
**Priority**: P2

**New Files**:
- `tests/unit/test_template_repository.py`
- `tests/unit/test_sqlite_adapter.py`
- `tests/unit/test_postgres_adapter.py`

**Test Coverage**:
- Port interface compliance
- SQLite adapter operations
- PostgreSQL adapter operations
- Factory logic
- Error handling

**Acceptance Criteria**:
- [ ] Unit tests mock the database
- [ ] Tests run without database connection
- [ ] All critical paths are tested

---

### Task 6.2: Create Integration Tests
**Status**: Pending  
**Priority**: P2

**New Files**:
- `tests/integration/test_sqlite_integration.py`
- `tests/integration/test_postgres_integration.py` (conditional)

**Test Coverage**:
- Real database operations
- Similarity matching
- Batch operations
- Concurrent access (PostgreSQL)

**Acceptance Criteria**:
- [ ] SQLite integration tests pass
- [ ] PostgreSQL integration tests pass (when PostgreSQL available)
- [ ] Tests verify data persistence
- [ ] Tests verify similarity matching accuracy

---

### Task 6.3: Verify Backward Compatibility
**Status**: Pending  
**Priority**: P1

**Description**: Ensure existing users experience no regression.

**Testing**:
- Run existing test suite
- Test with existing config.json
- Verify SQLite behavior unchanged

**Acceptance Criteria**:
- [ ] All existing tests pass
- [ ] SQLite behavior is identical
- [ ] No breaking changes to API

---

## Phase 7: Documentation

### Task 7.1: Update README
**Status**: Pending  
**Priority**: P3

**Files Modified**:
- `src/plugins/optimizer/README.md`

**Content**:
- Database configuration section
- SQLite setup instructions
- PostgreSQL setup instructions
- Migration guide (if needed)

---

## Task Dependencies

```
Phase 1 (Config) → Phase 2 (Port) → Phase 3 (SQLite) → Phase 5 (Factory)
                                                              ↓
Phase 4 (PostgreSQL) ────────────────────────────────────────┘
                               ↓
Phase 6 (Tests) ────────────────┴──────────────────────────────→ Phase 7 (Docs)
```

## Estimated Effort

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1 | 2 | 2 hours |
| Phase 2 | 2 | 3 hours |
| Phase 3 | 1 | 4 hours |
| Phase 4 | 1 | 6 hours |
| Phase 5 | 2 | 3 hours |
| Phase 6 | 3 | 6 hours |
| Phase 7 | 1 | 1 hour |
| **Total** | **12** | **~25 hours** |

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PostgreSQL similarity matching differs from SQLite | High | Extensive testing of similarity threshold values |
| Performance regression with abstraction layer | Medium | Benchmark tests before/after |
| Breaking existing functionality | High | Comprehensive backward compatibility testing |
