"""Performance monitoring for RAG operations with timing decorators."""

import logging
import time
import asyncio
import threading
from collections import defaultdict, deque
from typing import Any, Dict, Callable, Optional, List, Sequence
from functools import wraps
import math

from ..logging import LoggingUtils


class PerformanceMonitor:
    """Enhanced performance monitoring for RAG operations with timing decorators and histograms."""

    # Default sampling threshold - use sampling when metrics exceed this count
    _DEFAULT_SAMPLING_THRESHOLD = 1000
    # Default sampling rate when threshold is exceeded
    _DEFAULT_SAMPLING_RATE = 0.1  # 10% sampling

    # Histogram buckets for response times (in seconds)
    _HISTOGRAM_BUCKETS = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]

    def __init__(
        self,
        max_metrics_per_key: int = 1000,
        stats_cache_ttl: float = 1.0,
        retention_period: float = 3600.0,
        sampling_threshold: int = _DEFAULT_SAMPLING_THRESHOLD,
        sampling_rate: float = _DEFAULT_SAMPLING_RATE
    ):
        """Initialize the performance monitor.

        Args:
            max_metrics_per_key: Maximum number of metrics to keep per key
            stats_cache_ttl: Time-to-live for cached stats in seconds (default: 1 second)
            retention_period: Default retention period for metrics in seconds (default: 1 hour)
            sampling_threshold: Threshold for enabling sampling
            sampling_rate: Sampling rate when threshold exceeded (0.0-1.0)
        """
        self.max_metrics_per_key = max_metrics_per_key
        self.sampling_threshold = sampling_threshold
        self.sampling_rate = sampling_rate

        # Thread-safe storage with locks
        self._lock = threading.RLock()
        self.metrics = defaultdict(lambda: deque(maxlen=max_metrics_per_key))
        self.operation_counts = defaultdict(int)
        self.failure_counts = defaultdict(int)
        self.start_time = time.time()
        self.current_operations = defaultdict(int)
        self.peak_concurrency = defaultdict(int)

        # Histograms for response times
        self.histograms = defaultdict(lambda: defaultdict(int))

        # Stats caching
        self._stats_cache_ttl = stats_cache_ttl
        self._stats_cache: Dict[str, Any] = {}
        self._stats_cache_time: Dict[str, float] = {}

        # Retention period for metric pruning
        self._retention_period = retention_period

        # Per-key retention tracking (timestamps for each metric entry)
        self._metric_timestamps: Dict[str, List[float]] = defaultdict(list)

        # Logger
        self.logger = LoggingUtils.get_rag_logger(__name__)

    def record_operation(self, operation_name: str, duration: float, success: bool = True) -> None:
        """Record a RAG operation with timing and success status."""
        with self._lock:
            self.metrics[f"{operation_name}_duration"].append(duration)
            self._metric_timestamps[f"{operation_name}_duration"].append(time.time())
            self.operation_counts[operation_name] += 1

            # Update histogram
            self._update_histogram(operation_name, duration)

            # Track current and peak concurrency
            self.current_operations[operation_name] = max(0, self.current_operations[operation_name] - 1)

            if not success:
                self.failure_counts[operation_name] += 1
                self.metrics[f"{operation_name}_failures"].append(1)
                self._metric_timestamps[f"{operation_name}_failures"].append(time.time())

            # Invalidate stats cache on new data
            self._stats_cache.clear()

    def _update_histogram(self, operation_name: str, duration: float) -> None:
        """Update histogram buckets for the given duration."""
        hist_key = f"{operation_name}_histogram"
        for i, bucket in enumerate(self._HISTOGRAM_BUCKETS):
            if duration <= bucket:
                self.histograms[hist_key][f"le_{bucket}"] += 1
                break
        else:
            # Duration exceeds all buckets
            self.histograms[hist_key]["overflow"] += 1

    def start_operation(self, operation_name: str) -> None:
        """Mark the start of an operation to track concurrency."""
        with self._lock:
            self.current_operations[operation_name] += 1
            self.peak_concurrency[operation_name] = max(
                self.peak_concurrency[operation_name],
                self.current_operations[operation_name]
            )

    def time_operation(self, operation_name: str) -> Callable:
        """Decorator to time synchronous RAG operations and record performance metrics.

        Args:
            operation_name: Name of the operation for tracking

        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.start_operation(operation_name)
                start_time = time.perf_counter()

                try:
                    result = func(*args, **kwargs)
                    duration = time.perf_counter() - start_time
                    self.record_operation(operation_name, duration, True)
                    return result

                except Exception as e:
                    duration = time.perf_counter() - start_time
                    self.record_operation(operation_name, duration, False)
                    # Let the exception propagate
                    raise
            return wrapper
        return decorator

    def time_async_operation(self, operation_name: str) -> Callable:
        """Decorator to time asynchronous RAG operations and record performance metrics.

        Args:
            operation_name: Name of the operation for tracking

        Returns:
            Decorator function for async methods
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                self.start_operation(operation_name)
                start_time = time.perf_counter()

                try:
                    result = await func(*args, **kwargs)
                    duration = time.perf_counter() - start_time
                    self.record_operation(operation_name, duration, True)
                    return result

                except Exception as e:
                    duration = time.perf_counter() - start_time
                    self.record_operation(operation_name, duration, False)
                    # Let the exception propagate
                    raise
            return wrapper
        return decorator

    def time_method(self, operation_name: Optional[str] = None) -> Callable:
        """Flexible decorator that works with both sync and async RAG methods.

        Args:
            operation_name: Optional operation name. If None, uses function name.

        Returns:
            Decorator function that adapts to sync/async methods
        """
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                actual_operation_name = operation_name or func.__name__
                return self.time_async_operation(actual_operation_name)(func)
            else:
                actual_operation_name = operation_name or func.__name__
                return self.time_operation(actual_operation_name)(func)
        return decorator

    def get_stats(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get comprehensive performance statistics including concurrency and histograms.

        Args:
            use_cache: Whether to use cached stats if available and valid

        Returns:
            Dictionary of performance statistics
        """
        cache_key = 'all_stats'
        now = time.time()

        with self._lock:
            if use_cache and cache_key in self._stats_cache:
                cache_time = self._stats_cache_time.get(cache_key, 0)
                if now - cache_time < self._stats_cache_ttl:
                    return self._stats_cache[cache_key]

            # Calculate stats
            stats = self._calculate_all_stats(now)

            # Cache result
            self._stats_cache[cache_key] = stats
            self._stats_cache_time[cache_key] = now

            return stats

    def _calculate_all_stats(self, now: float) -> Dict[str, Any]:
        """Calculate all statistics."""
        stats = {}
        uptime = now - self.start_time

        for metric_name, values in self.metrics.items():
            if values:
                # Apply sampling for large datasets
                values_list = list(values)
                if len(values_list) > self.sampling_threshold:
                    # Sample based on configured rate
                    sample_size = max(int(len(values_list) * self.sampling_rate), 2)
                    sampled_values = values_list[::len(values_list) // sample_size][:sample_size]
                else:
                    sampled_values = values_list

                stats[metric_name] = self._calculate_metric_stats(sampled_values)

        # Add histograms
        for hist_name, hist_data in self.histograms.items():
            stats[hist_name] = dict(hist_data)

        # Add operation-specific statistics
        for op_name in self.operation_counts:
            stats[f"{op_name}_concurrency"] = {
                'current': self.current_operations.get(op_name, 0),
                'peak': self.peak_concurrency.get(op_name, 0),
                'failures': self.failure_counts.get(op_name, 0),
                'success_rate': self._calculate_success_rate(op_name)
            }

        stats['uptime'] = uptime
        stats['operations'] = dict(self.operation_counts)
        stats['total_failures'] = sum(self.failure_counts.values())
        stats['overall_success_rate'] = self._calculate_overall_success_rate()
        stats['sampling_config'] = {
            'threshold': self.sampling_threshold,
            'rate': self.sampling_rate
        }

        return stats

    def _calculate_metric_stats(self, values: Sequence[float]) -> Dict[str, float]:
        """Calculate statistics for a single metric using Welford's algorithm.

        Args:
            values: Sequence of metric values

        Returns:
            Dictionary with count, avg, min, max, total, std_dev, percentiles
        """
        values_list = list(values)
        n = len(values_list)

        if n == 0:
            return {'count': 0, 'avg': 0.0, 'min': 0.0, 'max': 0.0, 'total': 0.0, 'std_dev': 0.0,
                    'p50': 0.0, 'p95': 0.0, 'p99': 0.0}

        if n == 1:
            value = values_list[0]
            return {
                'count': 1,
                'avg': value,
                'min': value,
                'max': value,
                'total': value,
                'std_dev': 0.0,
                'p50': value,
                'p95': value,
                'p99': value
            }

        # Use Welford's algorithm for numerical stability
        mean, variance, min_val, max_val, total = self._welford_stats(values_list)

        # Calculate percentiles
        sorted_values = sorted(values_list)
        p50 = sorted_values[int(n * 0.5)]
        p95 = sorted_values[int(n * 0.95)]
        p99 = sorted_values[int(n * 0.99)]

        return {
            'count': n,
            'avg': mean,
            'min': min_val,
            'max': max_val,
            'total': total,
            'std_dev': variance ** 0.5 if variance > 0 else 0.0,
            'p50': p50,
            'p95': p95,
            'p99': p99
        }

    def _welford_stats(self, values: List[float]) -> tuple:
        """Calculate mean, variance, min, max, total using Welford's algorithm.

        Args:
            values: List of values

        Returns:
            Tuple of (mean, variance, min, max, total)
        """
        n = len(values)
        if n == 0:
            return (0.0, 0.0, 0.0, 0.0, 0.0)

        # First pass: calculate mean and totals
        total = sum(values)
        mean = total / n

        min_val = min(values)
        max_val = max(values)

        # Second pass with Welford's algorithm for variance
        m2 = 0.0  # Sum of squared differences
        for x in values:
            delta = x - mean
            mean += delta / (n + 1)  # Running mean update
            m2 += delta * (x - mean)

        # Use population variance (divide by n, not n-1)
        variance = m2 / n if n > 0 else 0.0

        return (mean, variance, min_val, max_val, total)

    def _calculate_success_rate(self, operation_name: str) -> float:
        """Calculate success rate for a specific operation."""
        total = self.operation_counts.get(operation_name, 0)
        if total == 0:
            return 1.0
        failures = self.failure_counts.get(operation_name, 0)
        return 1.0 - (failures / total)

    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all operations."""
        total_operations = sum(self.operation_counts.values())
        if total_operations == 0:
            return 1.0
        total_failures = sum(self.failure_counts.values())
        return 1.0 - (total_failures / total_operations)

    def prune_old_metrics(self, max_age_seconds: Optional[float] = None) -> int:
        """Remove metrics older than max_age_seconds.

        Note: Due to deque maxlen, this is primarily for timestamp tracking.
        The actual metric values are automatically limited by maxlen.

        Args:
            max_age_seconds: Maximum age in seconds. If None, uses retention_period.

        Returns:
            Number of entries pruned (for timestamps)
        """
        if max_age_seconds is None:
            max_age_seconds = self._retention_period

        cutoff = time.time() - max_age_seconds
        pruned_count = 0

        with self._lock:
            for key, timestamps in self._metric_timestamps.items():
                # Keep only recent timestamps
                original_count = len(timestamps)
                self._metric_timestamps[key] = [ts for ts in timestamps if ts >= cutoff]
                pruned_count += original_count - len(self._metric_timestamps[key])

        return pruned_count

    def log_summary(self, logger: Optional[logging.Logger] = None) -> None:
        """Log comprehensive performance summary with enhanced metrics."""
        if logger is None:
            logger = self.logger

        stats = self.get_stats()
        logger.info(f"RAG Performance Monitor Summary (uptime: {stats['uptime']:.1f}s)")
        logger.info(f"Overall Success Rate: {stats['overall_success_rate']:.2%}")
        logger.info(f"Sampling: threshold={stats['sampling_config']['threshold']}, rate={stats['sampling_config']['rate']:.1%}")

        for op_name, count in stats['operations'].items():
            duration_key = f"{op_name}_duration"
            concurrency_key = f"{op_name}_concurrency"

            if duration_key in stats:
                duration_stats = stats[duration_key]
                concurrency_stats = stats.get(concurrency_key, {})

                logger.info(
                    f"  {op_name}: {count} calls, "
                    f"avg: {duration_stats['avg']:.4f}s, "
                    f"p95: {duration_stats['p95']:.4f}s, "
                    f"total: {duration_stats['total']:.4f}s, "
                    f"success: {concurrency_stats.get('success_rate', 1.0):.2%}, "
                    f"peak concurrency: {concurrency_stats.get('peak', 0)}"
                )
            else:
                logger.info(f"  {op_name}: {count} calls")

    def log_detailed_summary(self, logger: Optional[logging.Logger] = None) -> None:
        """Log detailed performance summary with all available metrics."""
        if logger is None:
            logger = self.logger

        stats = self.get_stats()
        logger.info("=== Detailed RAG Performance Monitor Summary ===")
        logger.info(f"Uptime: {stats['uptime']:.1f}s")
        logger.info(f"Overall Success Rate: {stats['overall_success_rate']:.2%}")
        logger.info(f"Total Operations: {sum(stats['operations'].values())}")
        logger.info(f"Total Failures: {stats['total_failures']}")
        logger.info(f"Sampling Config: threshold={stats['sampling_config']['threshold']}, rate={stats['sampling_config']['rate']:.1%}")

        for op_name in stats['operations']:
            duration_key = f"{op_name}_duration"
            concurrency_key = f"{op_name}_concurrency"
            hist_key = f"{op_name}_histogram"

            if duration_key in stats:
                duration_stats = stats[duration_key]
                concurrency_stats = stats.get(concurrency_key, {})

                logger.info(f"\nOperation: {op_name}")
                logger.info(f"  Calls: {stats['operations'][op_name]}")
                logger.info(f"  Duration - avg: {duration_stats['avg']:.6f}s, p50: {duration_stats['p50']:.6f}s, p95: {duration_stats['p95']:.6f}s, p99: {duration_stats['p99']:.6f}s")
                logger.info(f"  Duration - min: {duration_stats['min']:.6f}s, max: {duration_stats['max']:.6f}s, total: {duration_stats['total']:.6f}s")
                logger.info(f"  Concurrency - current: {concurrency_stats.get('current', 0)}, peak: {concurrency_stats.get('peak', 0)}")
                logger.info(f"  Quality - success_rate: {concurrency_stats.get('success_rate', 1.0):.2%}, failures: {concurrency_stats.get('failures', 0)}")

                if hist_key in stats:
                    hist = stats[hist_key]
                    logger.info(f"  Histogram: {dict(hist)}")

        logger.info("=== End Detailed RAG Performance Summary ===")

    def reset_metrics(self) -> None:
        """Reset all performance metrics (useful for benchmarking)."""
        with self._lock:
            self.metrics.clear()
            self.operation_counts.clear()
            self.failure_counts.clear()
            self.current_operations.clear()
            self.peak_concurrency.clear()
            self.histograms.clear()
            self._metric_timestamps.clear()
            self._stats_cache.clear()
            self._stats_cache_time.clear()
            self.start_time = time.time()

    def get_current_concurrency(self) -> Dict[str, int]:
        """Get current concurrency levels for all operations."""
        with self._lock:
            return dict(self.current_operations)

    def get_peak_concurrency(self) -> Dict[str, int]:
        """Get peak concurrency levels for all operations."""
        with self._lock:
            return dict(self.peak_concurrency)

    def get_histogram(self, operation_name: str) -> Dict[str, int]:
        """Get histogram data for a specific operation."""
        with self._lock:
            hist_key = f"{operation_name}_histogram"
            return dict(self.histograms.get(hist_key, {}))

    def get_stats_cache_info(self) -> Dict[str, Any]:
        """Get statistics about the stats cache.

        Returns:
            Dictionary with cache information
        """
        cache_key = 'all_stats'
        now = time.time()
        with self._lock:
            return {
                'cache_valid': (
                    cache_key in self._stats_cache and
                    now - self._stats_cache_time.get(cache_key, 0) < self._stats_cache_ttl
                ),
                'cache_ttl_remaining': max(
                    0,
                    self._stats_cache_ttl - (now - self._stats_cache_time.get(cache_key, 0))
                ),
                'cache_ttl': self._stats_cache_ttl
            }