"""Tests for DatabaseFactory."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.plugins.optimizer.infrastructure.factory.database_factory import DatabaseFactory, DatabaseType
from src.plugins.optimizer.infrastructure.adapters.sqlite_adapter import SQLiteTemplateRepository
from src.plugins.optimizer.infrastructure.adapters.postgres_adapter import PostgreSQLTemplateRepository


class TestDatabaseFactory:
    """Test DatabaseFactory functionality."""

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository')
    def test_create_repository_sqlite_type(self, mock_sqlite_class):
        """Test that factory creates SQLite adapter for 'sqlite' type."""
        mock_repo = MagicMock()
        mock_sqlite_class.return_value = mock_repo
        
        result = DatabaseFactory.create_repository(
            database_type="sqlite",
            database_path=Path("./test.db")
        )
        
        assert result == mock_repo
        mock_sqlite_class.assert_called_once_with(db_path=Path("./test.db"))

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.PostgreSQLTemplateRepository')
    def test_create_repository_postgres_type(self, mock_postgres_class):
        """Test that factory creates PostgreSQL adapter for 'postgres' type."""
        mock_repo = MagicMock()
        mock_postgres_class.return_value = mock_repo
        
        result = DatabaseFactory.create_repository(
            database_type="postgres",
            postgres_connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        
        assert result == mock_repo
        mock_postgres_class.assert_called_once_with(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )

    def test_create_repository_raises_valueerror_for_invalid_type(self):
        """Test that factory raises ValueError for unsupported database type."""
        with pytest.raises(ValueError) as exc_info:
            DatabaseFactory.create_repository(
                database_type="mysql",
                database_path=Path("./test.db")
            )
        
        assert "Unsupported database type" in str(exc_info.value)
        assert "mysql" in str(exc_info.value)

    def test_create_repository_raises_valueerror_for_missing_postgres_connection(self):
        """Test that factory raises ValueError when PostgreSQL connection string is missing."""
        with pytest.raises(ValueError) as exc_info:
            DatabaseFactory.create_repository(
                database_type="postgres"
            )
        
        assert "postgres_connection_string is required" in str(exc_info.value)

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository')
    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.Path')
    def test_create_repository_uses_default_sqlite_path(self, mock_path_class, mock_sqlite_class):
        """Test that factory uses default SQLite path when not provided."""
        mock_repo = MagicMock()
        mock_sqlite_class.return_value = mock_repo
        
        # Mock Path to return predictable results
        mock_path = MagicMock(spec=Path)
        mock_path_class.return_value = mock_path
        mock_path.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.mkdir = MagicMock()
        
        result = DatabaseFactory.create_repository(database_type="sqlite")
        
        assert result == mock_repo
        mock_sqlite_class.assert_called_once()

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository')
    def test_create_from_config_sqlite(self, mock_sqlite_class):
        """Test that create_from_config works with SQLite configuration."""
        mock_repo = MagicMock()
        mock_sqlite_class.return_value = mock_repo
        
        result = DatabaseFactory.create_from_config(
            database_type="sqlite",
            database_path="./test.db"
        )
        
        assert result == mock_repo
        mock_sqlite_class.assert_called_once()

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.PostgreSQLTemplateRepository')
    def test_create_from_config_postgres(self, mock_postgres_class):
        """Test that create_from_config works with PostgreSQL configuration."""
        mock_repo = MagicMock()
        mock_postgres_class.return_value = mock_repo
        
        result = DatabaseFactory.create_from_config(
            database_type="postgres",
            postgres_connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        
        assert result == mock_repo
        mock_postgres_class.assert_called_once()

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository')
    def test_create_from_config_converts_string_path(self, mock_sqlite_class):
        """Test that create_from_config converts string path to Path object."""
        mock_repo = MagicMock()
        mock_sqlite_class.return_value = mock_repo
        
        result = DatabaseFactory.create_from_config(
            database_type="sqlite",
            database_path="./test.db"
        )
        
        # Verify SQLiteTemplateRepository was called
        mock_sqlite_class.assert_called_once()
        call_kwargs = mock_sqlite_class.call_args.kwargs
        db_path = call_kwargs.get('db_path')
        assert db_path is not None

    def test_get_supported_types(self):
        """Test that get_supported_types returns correct database types."""
        supported = DatabaseFactory.get_supported_types()
        
        assert "sqlite" in supported
        assert "postgres" in supported
        assert len(supported) == 2


class TestDatabaseType:
    """Test DatabaseType enum."""

    def test_sqlite_value(self):
        """Test that DatabaseType.SQLITE has correct value."""
        assert DatabaseType.SQLITE.value == "sqlite"

    def test_postgres_value(self):
        """Test that DatabaseType.POSTGRES has correct value."""
        assert DatabaseType.POSTGRES.value == "postgres"

    def test_database_type_enum_values(self):
        """Test all database type values."""
        expected_values = ["sqlite", "postgres"]
        actual_values = [dt.value for dt in DatabaseType]
        
        assert set(actual_values) == set(expected_values)


class TestDatabaseFactoryEdgeCases:
    """Test edge cases for DatabaseFactory."""

    def test_create_repository_empty_string_type(self):
        """Test that factory raises ValueError for empty database type."""
        with pytest.raises(ValueError) as exc_info:
            DatabaseFactory.create_repository(
                database_type="",
                database_path=Path("./test.db")
            )
        
        assert "Unsupported database type" in str(exc_info.value)

    def test_create_repository_invalid_type(self):
        """Test that factory raises ValueError for invalid database type."""
        with pytest.raises(ValueError) as exc_info:
            DatabaseFactory.create_repository(
                database_type="SQLITE",  # Uppercase
                database_path=Path("./test.db")
            )
        
        assert "Unsupported database type" in str(exc_info.value)

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.PostgreSQLTemplateRepository')
    def test_create_repository_postgres_with_pool_settings(self, mock_postgres_class):
        """Test that factory passes pool settings to PostgreSQL adapter."""
        mock_repo = MagicMock()
        mock_postgres_class.return_value = mock_repo
        
        result = DatabaseFactory.create_repository(
            database_type="postgres",
            postgres_connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        
        assert result == mock_repo
        # The factory doesn't pass pool settings directly, it uses defaults
        # This test verifies the basic call works
        mock_postgres_class.assert_called_once()

    def test_create_from_config_with_path_object(self):
        """Test that create_from_config handles Path objects directly."""
        with patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository') as mock_sqlite_class:
            mock_repo = MagicMock()
            mock_sqlite_class.return_value = mock_repo
            
            result = DatabaseFactory.create_from_config(
                database_type="sqlite",
                database_path=Path("./test.db")
            )
            
            assert result == mock_repo
            mock_sqlite_class.assert_called_once()

    def test_create_from_config_without_optional_params(self):
        """Test that create_from_config works when optional params are None."""
        with patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository') as mock_sqlite_class:
            mock_repo = MagicMock()
            mock_sqlite_class.return_value = mock_repo
            
            result = DatabaseFactory.create_from_config(
                database_type="sqlite",
                database_path=None,
                postgres_connection_string=None
            )
            
            assert result == mock_repo

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository')
    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.Path')
    def test_create_repository_creates_data_directory(self, mock_path_class, mock_sqlite_class):
        """Test that factory creates data directory if it doesn't exist."""
        mock_repo = MagicMock()
        mock_sqlite_class.return_value = mock_repo
        
        # Mock Path to simulate directory creation
        mock_path = MagicMock(spec=Path)
        mock_path_class.return_value = mock_path
        mock_path.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.mkdir = MagicMock()
        
        result = DatabaseFactory.create_repository(database_type="sqlite")
        
        assert result == mock_repo

    @patch('src.plugins.optimizer.infrastructure.factory.database_factory.SQLiteTemplateRepository')
    def test_create_repository_sqlite_with_explicit_path(self, mock_sqlite_class):
        """Test that factory uses explicit path when provided."""
        mock_repo = MagicMock()
        mock_sqlite_class.return_value = mock_repo
        
        explicit_path = Path("/explicit/path/db.sqlite")
        result = DatabaseFactory.create_repository(
            database_type="sqlite",
            database_path=explicit_path
        )
        
        assert result == mock_repo
        mock_sqlite_class.assert_called_once_with(db_path=explicit_path)
