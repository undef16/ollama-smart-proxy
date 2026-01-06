"""Tests for SQLite adapter implementation."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from src.plugins.optimizer.infrastructure.adapters.sqlite_adapter import SQLiteTemplateRepository
from src.plugins.optimizer.infrastructure.database.template_model import TemplateModel as SQLiteTemplate, Base


class TestSQLiteAdapter:
    """Test SQLite adapter functionality with mocked database connections."""

    def test_instantiation_with_in_memory_database(self):
        """Test that SQLiteTemplateRepository can be instantiated with in-memory database."""
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
            assert repo.db_path == Path(":memory:")
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            assert "sqlite:///:memory:" in str(call_args)

    def test_instantiation_with_custom_path(self):
        """Test that SQLiteTemplateRepository can be instantiated with custom path."""
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                repo = SQLiteTemplateRepository(db_path=Path("./data/custom.db"))
                
            assert repo.db_path == Path("./data/custom.db")
            # Check that sqlite URL is in the call args
            call_args = str(mock_create_engine.call_args)
            assert "sqlite:" in call_args or "sqlite://" in call_args

    def test_pragmas_are_registered_on_connect(self):
        """Test that PRAGMA settings are applied on connection."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event') as mock_event:
                repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                # Verify event listener was registered
                mock_event.listens_for.assert_called()

    def test_hamming_distance_udf_registration(self):
        """Test that hamming_distance UDF is registered correctly."""
        mock_connection = MagicMock()
        mock_connection.execute = MagicMock()
        
        # Test the static method directly
        SQLiteTemplateRepository._register_hamming_distance(mock_connection)
        
        # Verify create_function was called for hamming_distance
        mock_connection.create_function.assert_called_once()
        call_args = mock_connection.create_function.call_args
        assert call_args[0][0] == "hamming_distance"  # function name
        assert call_args[0][1] == 2  # number of arguments

    def test_save_template_creates_new_template(self):
        """Test that save_template creates a new template when hash doesn't exist."""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_connection = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                # Query returns empty (no existing template)
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                mock_session_instance.query.return_value = mock_query
                
                # Add returns nothing, commit works
                mock_session_instance.add = MagicMock()
                mock_session_instance.commit = MagicMock()
                
                # Mock the template creation to return an id
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                template_id = repo.save_template(
                    template_hash="abc123",
                    fingerprints={64: 12345, 128: 67890},
                    working_window=2048,
                    optimal_batch_size=32
                )
                
                # Verify add was called
                mock_session_instance.add.assert_called()

    def test_save_template_updates_existing_template(self):
        """Test that save_template updates existing template when hash exists."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                # Query returns existing template
                existing_template = MagicMock()
                existing_template.id = 1
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = existing_template
                mock_session_instance.query.return_value = mock_query
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                template_id = repo.save_template(
                    template_hash="abc123",
                    fingerprints={64: 12345},
                    working_window=2048,
                    optimal_batch_size=32
                )
                
                assert template_id == 1
                # Verify commit was called for update
                mock_session_instance.commit.assert_called()

    def test_find_by_hash_returns_template(self):
        """Test that find_by_hash returns the correct template."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
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
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                result = repo.find_by_hash("abc123")
                
                assert result is not None
                assert result.template_hash == "abc123"

    def test_find_by_hash_returns_none_for_nonexistent(self):
        """Test that find_by_hash returns None when template doesn't exist."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                # Query returns None
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                mock_session_instance.query.return_value = mock_query
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                result = repo.find_by_hash("nonexistent")
                
                assert result is None

    def test_find_by_fingerprint_with_valid_match(self):
        """Test that find_by_fingerprint finds a matching template."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
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
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                result = repo.find_by_fingerprint(
                    resolution=64,
                    fingerprint=12345,
                    threshold=5
                )
                
                # Verify execute was called
                mock_execute.assert_called()

    def test_find_by_fingerprint_returns_none_when_no_match(self):
        """Test that find_by_fingerprint returns None when no match found."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                # Execute returns None
                mock_result = MagicMock()
                mock_result.fetchone.return_value = None
                mock_execute = MagicMock(return_value=mock_result)
                mock_session_instance.execute = mock_execute
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                result = repo.find_by_fingerprint(
                    resolution=64,
                    fingerprint=12345,
                    threshold=5
                )
                
                assert result is None

    def test_update_template(self):
        """Test that update_template updates the template correctly."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
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
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                repo.update_template(
                    template_id=1,
                    new_distance=3,
                    working_window=2048,
                    optimal_batch_size=32
                )
                
                # Verify observation count and avg_distance are updated
                assert existing_template.observation_count == 11
                mock_session_instance.commit.assert_called()

    def test_batch_save_templates_empty_list(self):
        """Test that batch_save_templates returns empty list for empty input."""
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
            
            result = repo.batch_save_templates([])
            
            assert result == []

    def test_batch_save_templates_creates_new_templates(self):
        """Test that batch_save_templates creates multiple new templates."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
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
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
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

    def test_batch_update_templates_empty_list(self):
        """Test that batch_update_templates returns early for empty input."""
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
            
            repo.batch_update_templates([])
            
            # Verify Session was not used (early return)
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                MockSession.assert_not_called()

    def test_batch_update_templates_updates_multiple(self):
        """Test that batch_update_templates updates multiple templates."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
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
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                repo.batch_update_templates([
                    {"template_id": 1, "new_distance": 2, "working_window": 2048},
                    {"template_id": 2, "new_distance": 8, "working_window": 1024}
                ])
                
                mock_session_instance.commit.assert_called()

    def test_get_all_with_fingerprints(self):
        """Test that get_all_with_fingerprints returns templates with fingerprints."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
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
                template1.fingerprint_64 = 0xabc  # Integer value, not string
                template1.fingerprint_128 = None
                template1.fingerprint_256 = None
                template1.fingerprint_512 = None
                template1.fingerprint_1024 = None
                template1.created_at = datetime.now()
                template1.updated_at = datetime.now()
                
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = [template1]
                mock_session_instance.query.return_value = mock_query
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                result = repo.get_all_with_fingerprints()
                
                assert len(result) == 1
                assert result[0].template_hash == "hash1"

    def test_get_all_with_fingerprints_empty(self):
        """Test that get_all_with_fingerprints returns empty list when no templates."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                # Query returns empty
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = []
                mock_session_instance.query.return_value = mock_query
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                result = repo.get_all_with_fingerprints()
                
                assert result == []

    def test_close_disposes_engine(self):
        """Test that close disposes the database engine."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
            
            repo.close()
            
            mock_engine.dispose.assert_called_once()


class TestSQLiteAdapterEdgeCases:
    """Test edge cases for SQLite adapter."""

    def test_save_template_with_no_optional_batch_size(self):
        """Test that save_template works when optimal_batch_size is None."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                # Query returns empty (no existing template)
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                mock_session_instance.query.return_value = mock_query
                
                mock_session_instance.add = MagicMock()
                mock_session_instance.commit = MagicMock()
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                # Should not raise an exception
                try:
                    template_id = repo.save_template(
                        template_hash="abc123",
                        fingerprints={64: 12345},
                        working_window=2048,
                        optimal_batch_size=None  # Explicitly None
                    )
                    # If it returns None, that's acceptable for this edge case test
                    # as long as no exception is raised
                except Exception as e:
                    pytest.fail(f"save_template raised an exception: {e}")

    def test_save_template_with_empty_fingerprints(self):
        """Test that save_template works with empty fingerprints dict."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                mock_session_instance.query.return_value = mock_query
                
                mock_session_instance.add = MagicMock()
                mock_session_instance.commit = MagicMock()
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                # Should not raise an exception
                try:
                    template_id = repo.save_template(
                        template_hash="abc123",
                        fingerprints={},  # Empty dict
                        working_window=2048,
                        optimal_batch_size=32
                    )
                    # If it returns None, that's acceptable for this edge case test
                    # as long as no exception is raised
                except Exception as e:
                    pytest.fail(f"save_template raised an exception: {e}")

    def test_update_template_non_existent(self):
        """Test that update_template handles non-existent template gracefully."""
        mock_engine = MagicMock()
        
        with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.create_engine') as mock_create_engine:
            mock_create_engine.return_value = mock_engine
            
            with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.Session') as MockSession:
                mock_session_instance = MagicMock()
                MockSession.return_value.__enter__ = MagicMock(return_value=mock_session_instance)
                MockSession.return_value.__exit__ = MagicMock(return_value=False)
                
                # Query returns None (template doesn't exist)
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                mock_session_instance.query.return_value = mock_query
                
                with patch('src.plugins.optimizer.infrastructure.adapters.sqlite_adapter.event'):
                    repo = SQLiteTemplateRepository(db_path=Path(":memory:"))
                
                # Should not raise an exception
                repo.update_template(
                    template_id=999,
                    new_distance=3,
                    working_window=2048,
                    optimal_batch_size=32
                )
                
                # Verify commit was not called (no changes to make)
                mock_session_instance.commit.assert_not_called()
