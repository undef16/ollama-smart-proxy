"""Integration tests with PostgreSQL database.

These tests use testcontainers to spin up a real PostgreSQL instance
when Docker is available, or skip gracefully if neither Docker nor
a local PostgreSQL instance is available.
"""

import pytest
from typing import Dict, Any


class TestPostgreSQLIntegration:
    """Integration tests with real PostgreSQL database."""
    
    def test_full_crud_workflow(self, postgres_repo):
        """Test complete CRUD workflow with real PostgreSQL database."""
        # Create
        template_id = postgres_repo.save_template(
            template_hash="test_hash_123",
            fingerprints={64: 12345, 128: 67890},
            working_window=2048,
            optimal_batch_size=32
        )
        assert template_id is not None
        
        # Read
        template = postgres_repo.find_by_hash("test_hash_123")
        assert template is not None
        assert template.template_hash == "test_hash_123"
        assert template.working_window == 2048
        assert template.fingerprints[64] == 12345
        assert template.fingerprints[128] == 67890
        
        # Update
        postgres_repo.update_template(
            template_id=template_id,
            new_distance=5.0,
            working_window=4096,
            optimal_batch_size=64
        )
        
        # Verify update
        updated = postgres_repo.find_by_hash("test_hash_123")
        assert updated.working_window == 4096
        assert updated.optimal_batch_size == 64
        assert updated.observation_count == 1
        assert updated.avg_distance == 5.0
    
    def test_fingerprint_matching_with_pg_trgm(self, postgres_repo):
        """Test similarity matching with pg_trgm extension."""
        # Create template with known fingerprint
        postgres_repo.save_template(
            template_hash="pg_template1",
            fingerprints={64: 0x12345678},
            working_window=2048
        )
        
        # Find similar template (should use pg_trgm similarity)
        found = postgres_repo.find_by_fingerprint(
            resolution=64,
            fingerprint=0x12345678,
            threshold=5
        )
        assert found is not None
        assert found.template_hash == "pg_template1"
    
    def test_batch_operations(self, postgres_repo):
        """Test batch save and update operations with PostgreSQL."""
        templates_data = [
            {
                'template_hash': f'pg_batch_hash_{i}',
                'fingerprints': {64: i * 1000},
                'working_window': 2048 + i * 100,
                'optimal_batch_size': 32
            }
            for i in range(10)
        ]
        
        # Batch save
        ids = postgres_repo.batch_save_templates(templates_data)
        assert len(ids) == 10
        
        # Verify all were saved
        for i in range(10):
            template = postgres_repo.find_by_hash(f'pg_batch_hash_{i}')
            assert template is not None
            assert template.working_window == 2048 + i * 100
            assert template.fingerprints[64] == i * 1000
    
    def test_batch_update_operations(self, postgres_repo):
        """Test batch update operations with PostgreSQL."""
        # First, create some templates
        template_ids = []
        for i in range(5):
            template_id = postgres_repo.save_template(
                template_hash=f'pg_update_test_{i}',
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
        postgres_repo.batch_update_templates(updates)
        
        # Verify updates
        for i in range(5):
            template = postgres_repo.find_by_hash(f'pg_update_test_{i}')
            assert template is not None
            assert template.working_window == 3000 + i * 100
            assert template.optimal_batch_size == 64
            assert template.observation_count == 1
            assert template.avg_distance == float(i * 2)
    
    def test_get_all_with_fingerprints(self, postgres_repo):
        """Test retrieving all templates with fingerprints from PostgreSQL."""
        # Save templates with fingerprints
        postgres_repo.save_template(
            template_hash="pg_template_with_fingerprint",
            fingerprints={64: 12345},
            working_window=2048
        )
        
        # Save template without fingerprints
        postgres_repo.save_template(
            template_hash="pg_template_without_fingerprint",
            fingerprints={},
            working_window=2048
        )
        
        # Get all with fingerprints
        templates = postgres_repo.get_all_with_fingerprints()
        assert len(templates) >= 1
        # Find our template in the results
        template_hashes = [t.template_hash for t in templates]
        assert "pg_template_with_fingerprint" in template_hashes
    
    def test_multiple_resolutions_fingerprint_storage(self, postgres_repo):
        """Test storing and retrieving fingerprints at multiple resolutions in PostgreSQL."""
        # Save template with multiple resolution fingerprints
        postgres_repo.save_template(
            template_hash="pg_multi_res_template",
            fingerprints={64: 0x1234, 128: 0x567890AB, 256: 0x11112222},
            working_window=2048
        )
        
        # Retrieve and verify all fingerprints
        template = postgres_repo.find_by_hash("pg_multi_res_template")
        assert template is not None
        assert template.fingerprints[64] == 0x1234
        assert template.fingerprints[128] == 0x567890AB
        assert template.fingerprints[256] == 0x11112222
    
    def test_vacuum_analyze(self, postgres_repo):
        """Test VACUUM ANALYZE operation."""
        # Create a template
        postgres_repo.save_template(
            template_hash="vacuum_test",
            fingerprints={64: 12345},
            working_window=2048
        )
        
        # Run vacuum analyze - should not raise an exception
        postgres_repo.vacuum_analyze()
    
    def test_template_not_found(self, postgres_repo):
        """Test that find_by_hash returns None for non-existent template."""
        template = postgres_repo.find_by_hash("pg_non_existent_hash")
        assert template is None
    
    def test_update_nonexistent_template(self, postgres_repo):
        """Test that update_template handles non-existent template gracefully."""
        # Should not raise an exception
        postgres_repo.update_template(
            template_id=99999,
            new_distance=5.0,
            working_window=4096,
            optimal_batch_size=64
        )
    
    def test_empty_batch_operations(self, postgres_repo):
        """Test batch operations with empty lists in PostgreSQL."""
        # Batch save empty list
        ids = postgres_repo.batch_save_templates([])
        assert ids == []
        
        # Batch update empty list
        postgres_repo.batch_update_templates([])
        # Should not raise an exception
    
    def test_update_existing_template(self, postgres_repo):
        """Test that updating an existing template adds new fingerprints."""
        # Create initial template
        postgres_repo.save_template(
            template_hash="pg_update_test",
            fingerprints={64: 0x1234},
            working_window=2048
        )
        
        # Update with additional fingerprint
        postgres_repo.save_template(
            template_hash="pg_update_test",
            fingerprints={64: 0x1234, 128: 0x5678},
            working_window=2048
        )
        
        # Verify both fingerprints are stored
        template = postgres_repo.find_by_hash("pg_update_test")
        assert template is not None
        assert template.fingerprints[64] == 0x1234
        assert template.fingerprints[128] == 0x5678
