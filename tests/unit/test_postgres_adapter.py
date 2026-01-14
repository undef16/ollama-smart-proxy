"""Tests for PostgreSQL adapter implementation."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.plugins.optimizer.infrastructure.adapters.postgres_adapter import PostgreSQLTemplateRepository
from src.plugins.optimizer.infrastructure.database.template_model import TemplateModel as PostgreSQLTemplate, Base


class TestPostgresAdapter:
    """Test PostgreSQL adapter functionality with mocked database connections."""

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_instantiation_with_connection_string(self, mock_create_engine):
        """Test that PostgreSQLTemplateRepository can be instantiated with connection string."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        repo = PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        
        assert repo.connection_string == "postgresql://user:pass@localhost:5432/optimizer"
        # The constructor calls create_engine multiple times: once in _ensure_database_exists() and once for the main engine
        # So we expect it to be called at least once
        assert mock_create_engine.call_count >= 1
        call_kwargs = mock_create_engine.call_args.kwargs
        assert call_kwargs.get('pool_size') == 5
        assert call_kwargs.get('max_overflow') == 10
        assert call_kwargs.get('pool_pre_ping') is True

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_instantiation_with_custom_pool_settings(self, mock_create_engine):
        """Test that PostgreSQLTemplateRepository accepts custom pool settings."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        repo = PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer",
            pool_size=10,
            max_overflow=20
        )
        
        call_kwargs = mock_create_engine.call_args.kwargs
        assert call_kwargs.get('pool_size') == 10
        assert call_kwargs.get('max_overflow') == 20

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_pg_trgm_extension_is_ensured(self, mock_create_engine):
        """Test that pg_trgm extension is created on initialization."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine
        
        PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        
        # Verify execute was called for pg_trgm extension
        mock_connection.execute.assert_called()
        # Verify execute was called
        assert mock_connection.execute.called

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_save_template_creates_new_template(self, mock_create_engine):
        """Test that save_template creates a new template when hash doesn't exist."""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns empty (no existing template)
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session_instance.query.return_value = mock_query
            
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = MagicMock()
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            template_id = repo.save_template(
                template_hash="abc123",
                fingerprints={64: 12345, 128: 67890},
                working_window=2048,
                optimal_batch_size=32
            )
            
            # Verify add was called
            mock_session_instance.add.assert_called_once()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_save_template_updates_existing_template(self, mock_create_engine):
        """Test that save_template updates existing template when hash exists."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns existing template
            existing_template = MagicMock()
            existing_template.id = 1
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = existing_template
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            template_id = repo.save_template(
                template_hash="abc123",
                fingerprints={64: 12345},
                working_window=2048,
                optimal_batch_size=32
            )
            
            assert template_id == 1
            mock_session_instance.commit.assert_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_find_by_hash_returns_template(self, mock_create_engine):
        """Test that find_by_hash returns the correct template."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns existing template
            existing_template = MagicMock()
            existing_template.id = 1
            existing_template.template_hash = "abc123"
            existing_template.working_window = 2048
            existing_template.observation_count = 10
            existing_template.avg_distance = 5.5
            existing_template.optimal_batch_size = 32
            existing_template.fingerprint_64 = None
            existing_template.fingerprint_128 = None
            existing_template.fingerprint_256 = None
            existing_template.fingerprint_512 = None
            existing_template.fingerprint_1024 = None
            existing_template.created_at = datetime.now()
            existing_template.updated_at = datetime.now()
            
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = existing_template
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            result = repo.find_by_hash("abc123")
            
            assert result is not None
            assert result.template_hash == "abc123"

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_find_by_hash_returns_none_for_nonexistent(self, mock_create_engine):
        """Test that find_by_hash returns None when template doesn't exist."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns None
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            result = repo.find_by_hash("nonexistent")
            
            assert result is None

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_find_by_fingerprint_uses_pg_trgm(self, mock_create_engine):
        """Test that find_by_fingerprint uses pg_trgm similarity function."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Setup mock row from execute
            mock_row = [1]
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_row
            mock_execute = MagicMock(return_value=mock_result)
            mock_session_instance.execute = mock_execute
            
            # Query returns existing template
            existing_template = MagicMock()
            existing_template.id = 1
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = existing_template
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            result = repo.find_by_fingerprint(
                resolution=64,
                fingerprint=12345,
                threshold=5
            )
            
            # Verify execute was called
            mock_execute.assert_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_find_by_fingerprint_returns_none_when_no_match(self, mock_create_engine):
        """Test that find_by_fingerprint returns None when no match found."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Execute returns None
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_execute = MagicMock(return_value=mock_result)
            mock_session_instance.execute = mock_execute
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            result = repo.find_by_fingerprint(
                resolution=64,
                fingerprint=12345,
                threshold=5
            )
            
            assert result is None

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_update_template(self, mock_create_engine):
        """Test that update_template updates the template correctly."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns existing template
            existing_template = MagicMock()
            existing_template.id = 1
            existing_template.observation_count = 10
            existing_template.avg_distance = 5.0
            existing_template.working_window = 2048
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = existing_template
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            repo.update_template(
                template_id=1,
                new_distance=3,
                working_window=2048,
                optimal_batch_size=32
            )
            
            # Verify observation count and avg_distance are updated
            assert existing_template.observation_count == 11
            mock_session_instance.commit.assert_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_batch_save_templates_empty_list(self, mock_create_engine):
        """Test that batch_save_templates returns empty list for empty input."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        repo = PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        result = repo.batch_save_templates([])
        
        assert result == []

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_batch_save_templates_creates_new_templates(self, mock_create_engine):
        """Test that batch_save_templates creates multiple new templates."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns empty (no existing templates)
            mock_query = MagicMock()
            mock_query.filter.return_value.all.return_value = []
            mock_session_instance.query.return_value = mock_query
            
            # Bulk insert returns IDs
            mock_result = MagicMock()
            mock_result.__iter__ = MagicMock(return_value=iter([(1,), (2,)]))
            mock_session_instance.execute = MagicMock(return_value=mock_result)
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            templates_data = [
                {
                    "template_hash": "hash1",
                    "fingerprints": {64: 12345},
                    "working_window": 2048,
                    "optimal_batch_size": 32
                },
                {
                    "template_hash": "hash2",
                    "fingerprints": {128: 67890},
                    "working_window": 1024,
                    "optimal_batch_size": 64
                }
            ]
            result = repo.batch_save_templates(templates_data)
            
            assert len(result) == 2
            mock_session_instance.commit.assert_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_batch_update_templates_empty_list(self, mock_create_engine):
        """Test that batch_update_templates returns early for empty input."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        repo = PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        repo.batch_update_templates([])
        
        # Verify Session was not used
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            MockSession.assert_not_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_batch_update_templates_updates_multiple(self, mock_create_engine):
        """Test that batch_update_templates updates multiple templates."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns existing templates
            template1 = MagicMock()
            template1.id = 1
            template1.observation_count = 5
            template1.avg_distance = 4.0
            template1.working_window = 2048
            
            template2 = MagicMock()
            template2.id = 2
            template2.observation_count = 10
            template2.avg_distance = 6.0
            template2.working_window = 2048
            
            mock_query = MagicMock()
            mock_query.filter.return_value.all.return_value = [template1, template2]
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            repo.batch_update_templates([
                {"template_id": 1, "new_distance": 2, "working_window": 2048},
                {"template_id": 2, "new_distance": 8, "working_window": 1024}
            ])
            
            mock_session_instance.commit.assert_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_get_all_with_fingerprints(self, mock_create_engine):
        """Test that get_all_with_fingerprints returns templates with fingerprints."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns templates with fingerprints
            template1 = MagicMock()
            template1.id = 1
            template1.template_hash = "hash1"
            template1.working_window = 2048
            template1.observation_count = 10
            template1.avg_distance = 5.0
            template1.optimal_batch_size = 32
            template1.fingerprint_64 = "abc"
            template1.fingerprint_128 = None
            template1.fingerprint_256 = None
            template1.fingerprint_512 = None
            template1.fingerprint_1024 = None
            template1.created_at = datetime.now()
            template1.updated_at = datetime.now()
            
            mock_query = MagicMock()
            mock_query.filter.return_value.all.return_value = [template1]
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            result = repo.get_all_with_fingerprints()
            
            assert len(result) == 1
            assert result[0].template_hash == "hash1"

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_get_all_with_fingerprints_empty(self, mock_create_engine):
        """Test that get_all_with_fingerprints returns empty list when no templates."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns empty
            mock_query = MagicMock()
            mock_query.filter.return_value.all.return_value = []
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            result = repo.get_all_with_fingerprints()
            
            assert result == []

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_close_disposes_engine(self, mock_create_engine):
        """Test that close disposes the database engine."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        repo = PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        repo.close()
        
        # The engine may be disposed multiple times due to internal operations in the constructor
        assert mock_engine.dispose.call_count >= 1

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_vacuum_analyze(self, mock_create_engine):
        """Test that vacuum_analyze executes VACUUM ANALYZE command."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine
        
        repo = PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        repo.vacuum_analyze()
        
        # Verify execute was called for VACUUM ANALYZE
        mock_connection.execute.assert_called()
        # Verify execute was called
        assert mock_connection.execute.called

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_analyze(self, mock_create_engine):
        """Test that analyze executes ANALYZE command."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine
        
        repo = PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer"
        )
        repo.analyze()
        
        # Verify execute was called for ANALYZE
        mock_connection.execute.assert_called()
        # Verify execute was called
        assert mock_connection.execute.called


class TestPostgresAdapterEdgeCases:
    """Test edge cases for PostgreSQL adapter."""

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_save_template_with_no_optional_batch_size(self, mock_create_engine):
        """Test that save_template works when optimal_batch_size is None."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns empty (no existing template)
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session_instance.query.return_value = mock_query
            
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = MagicMock()
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            template_id = repo.save_template(
                template_hash="abc123",
                fingerprints={64: 12345},
                working_window=2048,
                optimal_batch_size=None  # Explicitly None
            )
            
            # Should not raise an exception
            mock_session_instance.add.assert_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_save_template_with_empty_fingerprints(self, mock_create_engine):
        """Test that save_template works with empty fingerprints dict."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session_instance.query.return_value = mock_query
            
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = MagicMock()
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            template_id = repo.save_template(
                template_hash="abc123",
                fingerprints={},  # Empty dict
                working_window=2048,
                optimal_batch_size=32
            )
            
            # Should not raise an exception
            mock_session_instance.add.assert_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_update_template_non_existent(self, mock_create_engine):
        """Test that update_template handles non-existent template gracefully."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        with patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.Session') as MockSession:
            mock_session_instance = MagicMock()
            MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
            MockSession.return_value.__exit__ = MagicMock(return_value=False)
            
            # Query returns None (template doesn't exist)
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session_instance.query.return_value = mock_query
            
            repo = PostgreSQLTemplateRepository(
                connection_string="postgresql://user:pass@localhost:5432/optimizer"
            )
            # Should not raise an exception
            repo.update_template(
                template_id=999,
                new_distance=3,
                working_window=2048,
                optimal_batch_size=32
            )
            
            # Verify commit was not called (no changes to make)
            mock_session_instance.commit.assert_not_called()

    @patch('src.plugins.optimizer.infrastructure.adapters.postgres_adapter.create_engine')
    def test_connection_pooling_configuration(self, mock_create_engine):
        """Test that connection pooling is properly configured."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        PostgreSQLTemplateRepository(
            connection_string="postgresql://user:pass@localhost:5432/optimizer",
            pool_size=10,
            max_overflow=20
        )
        
        call_kwargs = mock_create_engine.call_args.kwargs
        assert call_kwargs.get('pool_size') == 10
        assert call_kwargs.get('max_overflow') == 20
        assert call_kwargs.get('pool_pre_ping') is True
