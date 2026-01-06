"""Integration tests with real SQLite database."""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

from src.plugins.optimizer.infrastructure.adapters.sqlite_adapter import SQLiteTemplateRepository
from src.plugins.optimizer.domain.template import Template


class TestSQLiteIntegration:
    """Integration tests with real SQLite database."""
    
    @pytest.fixture
    def sqlite_repo(self, tmp_path):
        """Create a repository with a temporary database file."""
        db_path = tmp_path / "test_optimizer.db"
        repo = SQLiteTemplateRepository(db_path=db_path)
        yield repo
        repo.close()
    
    def test_full_crud_workflow(self, sqlite_repo):
        """Test complete CRUD workflow with real database."""
        # Create
        template_id = sqlite_repo.save_template(
            template_hash="test_hash_123",
            fingerprints={64: 12345, 128: 67890},
            working_window=2048,
            optimal_batch_size=32
        )
        assert template_id is not None
        
        # Read
        template = sqlite_repo.find_by_hash("test_hash_123")
        assert template is not None
        assert template.template_hash == "test_hash_123"
        assert template.working_window == 2048
        assert template.fingerprints[64] == 12345
        assert template.fingerprints[128] == 67890
        
        # Update
        sqlite_repo.update_template(
            template_id=template_id,
            new_distance=5.0,
            working_window=4096,
            optimal_batch_size=64
        )
        
        # Verify update
        updated = sqlite_repo.find_by_hash("test_hash_123")
        assert updated.working_window == 4096
        assert updated.optimal_batch_size == 64
        assert updated.observation_count == 1
        assert updated.avg_distance == 5.0
    
    def test_fingerprint_matching_exact_match(self, sqlite_repo):
        """Test similarity matching with hamming_distance for exact match."""
        # Create template with known fingerprint (using smaller value for SQLite integer compatibility)
        sqlite_repo.save_template(
            template_hash="template1",
            fingerprints={64: 0x12345678},  # Use smaller value
            working_window=2048
        )
        
        # Find similar template (exact match)
        found = sqlite_repo.find_by_fingerprint(
            resolution=64,
            fingerprint=0x12345678,
            threshold=0
        )
        assert found is not None
        assert found.template_hash == "template1"
        assert found.fingerprints[64] == 0x12345678
    
    def test_fingerprint_matching_threshold_match(self, sqlite_repo):
        """Test similarity matching with hamming_distance within threshold."""
        # Create template with known fingerprint (using smaller value)
        sqlite_repo.save_template(
            template_hash="template2",
            fingerprints={64: 0x12345678},
            working_window=2048
        )
        
        # Find similar template with 1-bit difference (within threshold 1)
        similar_fingerprint = 0x12345678 ^ 0x00000001  # 1 bit difference
        found = sqlite_repo.find_by_fingerprint(
            resolution=64,
            fingerprint=similar_fingerprint,
            threshold=1
        )
        assert found is not None
        assert found.template_hash == "template2"
        assert found.fingerprints[64] == 0x12345678
    
    def test_fingerprint_matching_no_match(self, sqlite_repo):
        """Test similarity matching with hamming_distance that should not match."""
        # Create template with known fingerprint
        sqlite_repo.save_template(
            template_hash="template3",
            fingerprints={64: 0x1234567890ABCDEF},
            working_window=2048
        )
        
        # Find similar template with large difference (outside threshold)
        different_fingerprint = 0x000000000  # Maximum difference
        found = sqlite_repo.find_by_fingerprint(
            resolution=64,
            fingerprint=different_fingerprint,
            threshold=10  # Even with threshold of 10, this should be too different
        )
        assert found is None
    
    def test_batch_operations(self, sqlite_repo):
        """Test batch save and update operations."""
        templates_data = [
            {
                'template_hash': f'batch_hash_{i}',
                'fingerprints': {64: i * 1000},
                'working_window': 2048 + i * 100,
                'optimal_batch_size': 32
            }
            for i in range(10)
        ]
        
        # Batch save
        ids = sqlite_repo.batch_save_templates(templates_data)
        assert len(ids) == 10
        
        # Verify all were saved
        for i in range(10):
            template = sqlite_repo.find_by_hash(f'batch_hash_{i}')
            assert template is not None
            assert template.working_window == 2048 + i * 100
            assert template.fingerprints[64] == i * 1000
    
    def test_batch_update_operations(self, sqlite_repo):
        """Test batch update operations."""
        # First, create some templates
        template_ids = []
        for i in range(5):
            template_id = sqlite_repo.save_template(
                template_hash=f'update_test_{i}',
                fingerprints={64: i * 1000},
                working_window=2048,
                optimal_batch_size=32
            )
            template_ids.append(template_id)
        
        # Prepare batch updates
        updates = [
            {
                'template_id': template_ids[i],
                'new_distance': float(i * 2),
                'working_window': 3000 + i * 100,
                'optimal_batch_size': 64
            }
            for i in range(5)
        ]
        
        # Batch update
        sqlite_repo.batch_update_templates(updates)
        
        # Verify updates
        for i in range(5):
            template = sqlite_repo.find_by_hash(f'update_test_{i}')
            assert template is not None
            assert template.working_window == 3000 + i * 100
            assert template.optimal_batch_size == 64
            assert template.observation_count == 1
            assert template.avg_distance == float(i * 2)
    
    def test_concurrent_access_persistence(self, tmp_path):
        """Test data persistence across repository instances."""
        db_path = tmp_path / "concurrent_test.db"
        
        # Save data with first repository instance
        repo1 = SQLiteTemplateRepository(db_path=db_path)
        template_id = repo1.save_template(
            template_hash="persistent_hash",
            fingerprints={64: 99999},
            working_window=4096,
            optimal_batch_size=128
        )
        repo1.close()
        
        # Access same data with second repository instance
        repo2 = SQLiteTemplateRepository(db_path=db_path)
        template = repo2.find_by_hash("persistent_hash")
        assert template is not None
        assert template.template_hash == "persistent_hash"
        assert template.fingerprints[64] == 99999
        assert template.working_window == 4096
        assert template.optimal_batch_size == 128
        repo2.close()
    
    def test_get_all_with_fingerprints(self, sqlite_repo):
        """Test retrieving all templates with fingerprints."""
        # Save templates with fingerprints
        sqlite_repo.save_template(
            template_hash="template_with_fingerprint",
            fingerprints={64: 12345},
            working_window=2048
        )
        
        # Save template without fingerprints
        sqlite_repo.save_template(
            template_hash="template_without_fingerprint",
            fingerprints={},
            working_window=2048
        )
        
        # Get all with fingerprints
        templates = sqlite_repo.get_all_with_fingerprints()
        assert len(templates) == 1
        assert templates[0].template_hash == "template_with_fingerprint"
        assert templates[0].fingerprints[64] == 12345
    
    def test_multiple_resolutions_fingerprint_storage(self, sqlite_repo):
        """Test storing and retrieving fingerprints at multiple resolutions."""
        # Save template with multiple resolution fingerprints
        template_id = sqlite_repo.save_template(
            template_hash="multi_res_template",
            fingerprints={64: 0x1234, 128: 0x567890ABCDEF1234, 256: 0x1111222233334444},
            working_window=2048
        )
        
        # Retrieve and verify all fingerprints
        template = sqlite_repo.find_by_hash("multi_res_template")
        assert template is not None
        assert template.fingerprints[64] == 0x1234
        assert template.fingerprints[128] == 0x567890ABCDEF1234
        assert template.fingerprints[256] == 0x1111222233334444
    
    def test_template_not_found(self, sqlite_repo):
        """Test that find_by_hash returns None for non-existent template."""
        template = sqlite_repo.find_by_hash("non_existent_hash")
        assert template is None
    
    def test_update_nonexistent_template(self, sqlite_repo):
        """Test that update_template handles non-existent template gracefully."""
        # Should not raise an exception
        sqlite_repo.update_template(
            template_id=99999,
            new_distance=5.0,
            working_window=4096,
            optimal_batch_size=64
        )
    
    def test_empty_batch_operations(self, sqlite_repo):
        """Test batch operations with empty lists."""
        # Batch save empty list
        ids = sqlite_repo.batch_save_templates([])
        assert ids == []
        
        # Batch update empty list
        sqlite_repo.batch_update_templates([])
        # Should not raise an exception
    
    def test_update_existing_template(self, sqlite_repo):
        """Test updating an existing template adds new fingerprints."""
        # Create initial template
        template_id = sqlite_repo.save_template(
            template_hash="update_test",
            fingerprints={64: 0x1234},
            working_window=2048
        )
        
        # Update with additional fingerprint
        sqlite_repo.save_template(
            template_hash="update_test",
            fingerprints={64: 0x1234, 128: 0x5678},
            working_window=2048
        )
        
        # Verify both fingerprints are stored
        template = sqlite_repo.find_by_hash("update_test")
        assert template is not None
        assert template.fingerprints[64] == 0x1234
        assert template.fingerprints[128] == 0x5678
