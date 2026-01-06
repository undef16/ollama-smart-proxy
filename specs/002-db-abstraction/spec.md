# Feature Specification: Configurable Database Abstraction

**Feature Branch**: `002-db-abstraction`
**Created**: 2026-01-06
**Status**: Draft
**Input**: User description: "Make database configurable between SQLite and PostgreSQL with gradual Hexagonal Architecture migration"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Database Type via Config File (Priority: P1)

As a system administrator, I want to configure the database type (SQLite or PostgreSQL) through the configuration file, so that I can choose the appropriate database for my deployment environment.

**Why this priority**: Core requirement that enables the entire feature - without configuration, there's no way to switch databases.

**Independent Test**: Can be fully tested by setting database type in config.json and verifying the application connects to the correct database type.

**Acceptance Scenarios**:

1. **Given** config.json contains `"database_type": "sqlite"`, **When** the application starts, **Then** it creates a SQLite database connection.
2. **Given** config.json contains `"database_type": "postgres"`, **When** the application starts, **Then** it creates a PostgreSQL database connection.
3. **Given** config.json has no database_type setting, **When** the application starts, **Then** it defaults to SQLite for backward compatibility.

---

### User Story 2 - Preserve SQLite Functionality (Priority: P1)

As an existing user of the optimizer plugin, I want the SQLite database to continue working exactly as before after the refactoring, so that I don't lose any functionality or data.

**Why this priority**: Critical for backward compatibility - existing users must not experience regression.

**Independent Test**: Can be tested by running the optimizer plugin with SQLite (default config) and verifying all existing functionality works.

**Acceptance Scenarios**:

1. **Given** the optimizer plugin is configured for SQLite, **When** a prompt is processed with /opt, **Then** template matching works with existing fingerprints.
2. **Given** SQLite database contains existing templates, **When** the application starts, **Then** it loads and uses the stored templates.
3. **Given** new templates are learned, **When** the application restarts, **Then** the templates persist in the SQLite database.

---

### User Story 3 - Connect to PostgreSQL Database (Priority: P2)

As a user deploying in a production environment, I want to connect the optimizer plugin to a PostgreSQL database, so that I can use enterprise-grade database features like connection pooling and concurrent access.

**Why this priority**: Enables production deployment with PostgreSQL, which offers better concurrency and reliability than SQLite.

**Independent Test**: Can be tested by configuring PostgreSQL connection settings and verifying template operations work correctly.

**Acceptance Scenarios**:

1. **Given** PostgreSQL is running with correct credentials, **When** the application starts, **Then** it establishes a connection to the PostgreSQL database.
2. **Given** PostgreSQL connection is configured, **When** templates are saved, **Then** they are stored in the PostgreSQL database.
3. **Given** PostgreSQL is unavailable at startup, **When** the application starts, **Then** it logs an appropriate error and fails gracefully.

---

### User Story 4 - Abstraction Layer Enables Testing (Priority: P3)

As a developer, I want to be able to mock the database layer for unit tests, so that I can test the optimizer logic without requiring a real database.

**Why this priority**: Improves testability and enables faster test execution without database dependencies.

**Independent Test**: Can be tested by running unit tests that mock the repository interface and verify optimizer behavior.

**Acceptance Scenarios**:

1. **Given** unit tests use a mock repository, **When** tests execute, **Then** they run without needing a database connection.
2. **Given** tests verify template matching, **When** mock returns test data, **Then** the optimizer uses the mock data correctly.

---

### Edge Cases

- What happens when PostgreSQL connection string is malformed?
- How does the system handle database migration from SQLite to PostgreSQL?
- What if the database file path for SQLite is invalid or not writable?
- How does the system behave when switching database types with existing data?
- What happens if hamming_distance calculation differs between SQLite and PostgreSQL?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support configuring database type through config.json with values "sqlite" or "postgres".
- **FR-002**: System MUST default to SQLite when no database_type is specified for backward compatibility.
- **FR-003**: System MUST support SQLite database file path configuration.
- **FR-004**: System MUST support PostgreSQL connection string configuration including host, port, database, user, and password.
- **FR-005**: System MUST provide a TemplateRepository port interface that abstracts database operations.
- **FR-006**: System MUST implement SQLite adapter that provides the same functionality as the current DatabaseManager.
- **FR-007**: System MUST implement PostgreSQL adapter with equivalent functionality to SQLite adapter.
- **FR-008**: System MUST use database factory pattern to instantiate the appropriate adapter based on configuration.
- **FR-009**: System MUST maintain the hamming_distance similarity matching capability in PostgreSQL.
- **FR-010**: System MUST log database connection status at startup.
- **FR-011**: System MUST fail gracefully with appropriate error messages when database connection fails.

### Key Entities *(include if feature involves data)*

- **TemplateRepository**: Port interface defining operations for template storage and retrieval (save, find_by_hash, find_by_fingerprint, update, batch_operations).
- **Template**: Domain entity representing a prompt template with fingerprints, working_window, and observation statistics.
- **DatabaseConfig**: Configuration entity for database connection settings.
- **DatabaseFactory**: Factory class that creates the appropriate database adapter based on configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can switch between SQLite and PostgreSQL by changing one configuration value.
- **SC-002**: Template matching accuracy remains identical between SQLite and PostgreSQL implementations (hamming_distance equivalence).
- **SC-003**: Existing SQLite users experience zero regression in functionality.
- **SC-004**: New PostgreSQL users can successfully deploy the optimizer plugin with their PostgreSQL database.
- **SC-005**: Unit tests can run without database dependencies by mocking the repository interface.
- **SC-006**: Database connection configuration is validated at startup with clear error messages for misconfiguration.

## Assumptions

- PostgreSQL will use the `pg_trgm` extension for similarity matching instead of the custom hamming_distance UDF used in SQLite.
- SQLite database file will be stored in the plugin's data directory by default.
- Connection pooling will be managed by SQLAlchemy for PostgreSQL.
- Database schema will be created automatically on first connection (autogenerate migrations).
- No automatic data migration from SQLite to PostgreSQL is required in this phase - users will start fresh or manually migrate.

## Out of Scope

- Automatic data migration between SQLite and PostgreSQL.
- Database schema versioning and migration tools.
- Multi-database support in a single instance.
- Connection pooling configuration tuning.
- Database backup and restore functionality.

## Dependencies

- SQLAlchemy 2.x for database abstraction.
- psycopg2-binary or asyncpg for PostgreSQL connections.
- Existing Config class for configuration management.
- Existing OptimizerAgent that will be refactored to use the abstraction.
