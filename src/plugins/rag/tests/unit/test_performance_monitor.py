"""Unit tests for RAG performance monitor."""

import time
import pytest
from unittest.mock import Mock

from src.plugins.rag.infrastructure.monitoring import PerformanceMonitor


class TestPerformanceMonitor:
    """Test cases for the RAG PerformanceMonitor."""

    def test_initialization(self):
        """Test that PerformanceMonitor initializes correctly."""
        monitor = PerformanceMonitor()
        assert monitor.max_metrics_per_key == 1000
        assert monitor.sampling_threshold == 1000
        assert monitor.sampling_rate == 0.1
        assert len(monitor.metrics) == 0
        assert len(monitor.operation_counts) == 0

    def test_record_operation_success(self):
        """Test recording a successful operation."""
        monitor = PerformanceMonitor()

        monitor.start_operation("test_op")
        time.sleep(0.01)  # Small delay
        monitor.record_operation("test_op", 0.01, success=True)

        stats = monitor.get_stats()
        assert "test_op_duration" in stats
        assert stats["operations"]["test_op"] == 1
        assert stats["test_op_concurrency"]["success_rate"] == 1.0

    def test_record_operation_failure(self):
        """Test recording a failed operation."""
        monitor = PerformanceMonitor()

        monitor.start_operation("test_op")
        monitor.record_operation("test_op", 0.01, success=False)

        stats = monitor.get_stats()
        assert stats["operations"]["test_op"] == 1
        assert stats["test_op_concurrency"]["failures"] == 1
        assert stats["test_op_concurrency"]["success_rate"] == 0.0

    def test_histogram_tracking(self):
        """Test histogram bucket tracking."""
        monitor = PerformanceMonitor()

        # Record operations with different durations
        monitor.record_operation("test_op", 0.001, True)  # < 0.001
        monitor.record_operation("test_op", 0.005, True)  # 0.001-0.005
        monitor.record_operation("test_op", 0.05, True)   # 0.005-0.01
        monitor.record_operation("test_op", 10.0, True)   # > 1.0

        hist = monitor.get_histogram("test_op")
        assert hist["le_0.001"] >= 1
        assert hist["le_0.005"] >= 1
        assert hist["le_0.05"] >= 1
        assert hist["le_10.0"] >= 1

    def test_time_operation_decorator(self):
        """Test the time_operation decorator."""
        monitor = PerformanceMonitor()

        @monitor.time_operation("decorated_op")
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()
        assert result == "result"

        stats = monitor.get_stats()
        assert "decorated_op_duration" in stats
        assert stats["operations"]["decorated_op"] == 1

    def test_sampling_configuration(self):
        """Test sampling configuration."""
        monitor = PerformanceMonitor(sampling_threshold=5, sampling_rate=0.5)
        assert monitor.sampling_threshold == 5
        assert monitor.sampling_rate == 0.5

    def test_thread_safety(self):
        """Test that operations are thread-safe."""
        import threading

        monitor = PerformanceMonitor()
        results = []

        def worker(worker_id):
            for i in range(10):
                monitor.start_operation(f"worker_{worker_id}")
                time.sleep(0.001)
                monitor.record_operation(f"worker_{worker_id}", 0.001, True)
            results.append(f"worker_{worker_id}_done")

        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 3
        stats = monitor.get_stats()
        assert sum(stats["operations"].values()) == 30  # 3 workers * 10 operations each

    def test_reset_metrics(self):
        """Test resetting metrics."""
        monitor = PerformanceMonitor()

        monitor.record_operation("test_op", 0.01, True)
        assert len(monitor.metrics) > 0

        monitor.reset_metrics()
        assert len(monitor.metrics) == 0
        assert len(monitor.operation_counts) == 0

    def test_stats_calculation(self):
        """Test comprehensive stats calculation."""
        monitor = PerformanceMonitor()

        # Record multiple operations
        for i in range(10):
            monitor.record_operation("test_op", 0.01 * i, True)

        stats = monitor.get_stats()
        duration_stats = stats["test_op_duration"]

        assert duration_stats["count"] == 10
        assert duration_stats["avg"] > 0
        assert duration_stats["min"] == 0.0
        assert duration_stats["max"] == 0.09
        assert "p50" in duration_stats
        assert "p95" in duration_stats
        assert "p99" in duration_stats