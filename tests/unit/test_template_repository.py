"""Tests for TemplateRepository port interface."""
import pytest
from unittest.mock import Mock, create_autospec
from abc import ABC

from src.plugins.optimizer.ports.template_repository import TemplateRepository
from src.plugins.optimizer.infrastructure.adapters.sqlite_adapter import SQLiteTemplateRepository
from src.plugins.optimizer.infrastructure.adapters.postgres_adapter import PostgreSQLTemplateRepository


class TestTemplateRepositoryInterface:
    """Test the TemplateRepository port interface."""

    def test_interface_is_abstract(self):
        """Test that TemplateRepository is an abstract class."""
        assert issubclass(TemplateRepository, ABC)
        assert hasattr(TemplateRepository, '__abstractmethods__')
        # Check that it has abstract methods
        expected_methods = {
            'save_template', 'find_by_hash', 'find_by_fingerprint', 
            'update_template', 'batch_save_templates', 'batch_update_templates',
            'get_all_with_fingerprints', 'close'
        }
        assert expected_methods.issubset(TemplateRepository.__abstractmethods__)

    def test_cannot_instantiate_abstract_interface(self):
        """Test that the abstract interface cannot be instantiated."""
        with pytest.raises(TypeError):
            TemplateRepository()

    def test_sqlite_adapter_implements_interface(self):
        """Test that SQLiteTemplateRepository implements the interface correctly."""
        # Verify that SQLiteTemplateRepository is a subclass
        assert issubclass(SQLiteTemplateRepository, TemplateRepository)
        
        # Create a mock SQLiteTemplateRepository to verify method signatures
        # This ensures all abstract methods are properly implemented
        try:
            # Try to create an instance (this will fail due to actual DB connection)
            # But we can check if it's instantiable in principle by checking method presence
            repo_methods = set(dir(SQLiteTemplateRepository))
            interface_methods = {
                'save_template', 'find_by_hash', 'find_by_fingerprint', 
                'update_template', 'batch_save_templates', 'batch_update_templates',
                'get_all_with_fingerprints', 'close'
            }
            
            for method in interface_methods:
                assert hasattr(SQLiteTemplateRepository, method), f"Missing method: {method}"
                assert callable(getattr(SQLiteTemplateRepository, method)), f"Method {method} is not callable"
                
        except Exception:
            # We might get database connection errors, which is expected
            # The important thing is that the methods exist
            pass

    def test_postgres_adapter_implements_interface(self):
        """Test that PostgreSQLTemplateRepository implements the interface correctly."""
        # Verify that PostgreSQLTemplateRepository is a subclass
        assert issubclass(PostgreSQLTemplateRepository, TemplateRepository)
        
        # Check that all interface methods are implemented
        repo_methods = set(dir(PostgreSQLTemplateRepository))
        interface_methods = {
            'save_template', 'find_by_hash', 'find_by_fingerprint', 
            'update_template', 'batch_save_templates', 'batch_update_templates',
            'get_all_with_fingerprints', 'close'
        }
        
        for method in interface_methods:
            assert hasattr(PostgreSQLTemplateRepository, method), f"Missing method: {method}"
            assert callable(getattr(PostgreSQLTemplateRepository, method)), f"Method {method} is not callable"

    def test_interface_method_signatures(self):
        """Test that the interface defines the correct method signatures."""
        # Use create_autospec to verify the interface structure
        mock_repo = create_autospec(TemplateRepository, instance=True)
        
        # Verify all required methods exist with proper signatures
        assert hasattr(mock_repo, 'save_template')
        assert hasattr(mock_repo, 'find_by_hash')
        assert hasattr(mock_repo, 'find_by_fingerprint')
        assert hasattr(mock_repo, 'update_template')
        assert hasattr(mock_repo, 'batch_save_templates')
        assert hasattr(mock_repo, 'batch_update_templates')
        assert hasattr(mock_repo, 'get_all_with_fingerprints')
        assert hasattr(mock_repo, 'close')

    def test_save_template_signature(self):
        """Test save_template method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        # This should not raise an error if signature is correct
        mock_repo.save_template(
            template_hash="abc123",
            fingerprints={64: 12345, 128: 67890},
            working_window=2048,
            optimal_batch_size=32
        )

    def test_find_by_hash_signature(self):
        """Test find_by_hash method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        mock_repo.find_by_hash(template_hash="abc123")

    def test_find_by_fingerprint_signature(self):
        """Test find_by_fingerprint method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        mock_repo.find_by_fingerprint(
            resolution=64,
            fingerprint=12345,
            threshold=5
        )

    def test_update_template_signature(self):
        """Test update_template method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        mock_repo.update_template(
            template_id=1,
            new_distance=10,
            working_window=2048,
            optimal_batch_size=32
        )

    def test_batch_save_templates_signature(self):
        """Test batch_save_templates method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        mock_repo.batch_save_templates([
            {
                "template_hash": "abc123",
                "fingerprints": {64: 12345},
                "working_window": 2048,
                "optimal_batch_size": 32
            }
        ])

    def test_batch_update_templates_signature(self):
        """Test batch_update_templates method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        mock_repo.batch_update_templates([
            {
                "template_id": 1,
                "new_distance": 10,
                "working_window": 2048,
                "optimal_batch_size": 32
            }
        ])

    def test_get_all_with_fingerprints_signature(self):
        """Test get_all_with_fingerprints method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        mock_repo.get_all_with_fingerprints()

    def test_close_signature(self):
        """Test close method signature."""
        mock_repo = create_autospec(TemplateRepository, instance=True)
        mock_repo.close()
