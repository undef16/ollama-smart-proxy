"""Analyzes and computes latency statistics."""
import logging
from typing import List
import numpy as np

from .models import LatencyResults


# Configure logging
logger = logging.getLogger(__name__)


class LatencyAnalyzer:
    """Analyzes and computes latency statistics."""
    
    @staticmethod
    def compute_percentiles(latencies: List[float]) -> LatencyResults:
        """
        Compute p50, p90, p95 percentiles.

        Args:
            latencies: List of latency measurements.

        Returns:
            LatencyResults dataclass with percentiles.
        """
        if not latencies:
            return LatencyResults(p50=0.0, p90=0.0, p95=0.0)

        return LatencyResults(
            p50=float(np.percentile(latencies, 50)),
            p90=float(np.percentile(latencies, 90)),
            p95=float(np.percentile(latencies, 95))
        )