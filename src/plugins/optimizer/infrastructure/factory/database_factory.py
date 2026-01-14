"""Database factory for creating database adapters based on configuration."""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from ..adapters.sqlite_adapter import SQLiteTemplateRepository
from ..adapters.postgres_adapter import PostgreSQLTemplateRepository
from ...ports.template_repository import TemplateRepository


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class DatabaseFactory:
    """Factory for creating database adapters based on configuration."""
    
    @staticmethod
    def create_repository(
        database_type: str = "sqlite",
        database_path: Optional[Path] = None,
        postgres_connection_string: Optional[str] = None
    ) -> TemplateRepository:
        """Create and return the appropriate repository adapter.

        Args:
            database_type: Type of database ("sqlite" or "postgres")
            database_path: Path to SQLite database file
            postgres_connection_string: PostgreSQL connection string

        Returns:
            TemplateRepository implementation instance

        Raises:
            ValueError: If database type is unsupported or config is invalid
        """
        import logging
        logger = logging.getLogger(__name__)

        if database_type == DatabaseType.SQLITE.value:
            if database_path is None:
                # Use default path in plugin directory
                plugin_dir = Path(__file__).parent.parent
                data_dir = plugin_dir / "data"
                data_dir.mkdir(exist_ok=True)
                database_path = data_dir / "optimizer_stats.db"
                logger.info(f"Using default SQLite path: {database_path}")
            logger.info(f"Creating SQLiteTemplateRepository with path: {database_path}")
            return SQLiteTemplateRepository(db_path=database_path)

        elif database_type == DatabaseType.POSTGRES.value:
            if postgres_connection_string is None:
                raise ValueError(
                    "postgres_connection_string is required for PostgreSQL database type"
                )
            logger.info(f"Creating PostgreSQLTemplateRepository with connection string: {postgres_connection_string.replace(postgres_connection_string.split('@')[0].split(':')[-1] if '@' in postgres_connection_string else '', '***')}")
            return PostgreSQLTemplateRepository(connection_string=postgres_connection_string)

        else:
            supported_types = ", ".join(dt.value for dt in DatabaseType)
            raise ValueError(
                f"Unsupported database type: {database_type}. "
                f"Supported types: {supported_types}"
            )
    
    @staticmethod
    def create_from_config(
        database_type: str,
        database_path: Optional[Union[Path, str]] = None,
        postgres_connection_string: Optional[str] = None
    ) -> TemplateRepository:
        """Create repository from configuration settings.

        Args:
            database_type: Type of database ("sqlite" or "postgres")
            database_path: Path to SQLite database file (can be Path or str)
            postgres_connection_string: PostgreSQL connection string

        Returns:
            TemplateRepository implementation instance

        Raises:
            ValueError: If database type is unsupported or config is invalid
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"DatabaseFactory.create_from_config called with type: {database_type}")

        # Convert string path to Path if needed
        if database_path is not None and isinstance(database_path, str):
            database_path = Path(database_path)
            logger.info(f"Converted database_path to Path: {database_path}")

        logger.info("Calling DatabaseFactory.create_repository")
        repo = DatabaseFactory.create_repository(
            database_type=database_type,
            database_path=database_path,
            postgres_connection_string=postgres_connection_string
        )
        logger.info(f"Repository created successfully: {type(repo).__name__}")
        return repo
    
    @staticmethod
    def get_supported_types() -> List[str]:
        """Return list of supported database types.
        
        Returns:
            List of supported database type strings
        """
        return [dt.value for dt in DatabaseType]
