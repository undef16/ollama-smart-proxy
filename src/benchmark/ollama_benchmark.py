"""Main class for running Ollama latency benchmarks with improved OOP structure."""
import logging
from pathlib import Path
from typing import List, Dict
import requests

from .models import BenchmarkConfig, LatencyResults
from .constants import BenchmarkConstants
from .request_session_manager import RequestSessionManager
from .dataset_manager import DatasetManager
from .request_executor import RequestExecutor
from .latency_analyzer import LatencyAnalyzer
from .concurrency_manager import ConcurrencyManager
from .result_exporter import ResultExporter
from .visualization_generator import VisualizationGenerator


# Configure logging
logger = logging.getLogger(__name__)


class OllamaBenchmark:
    """Main class for running Ollama latency benchmarks with improved OOP structure."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.dataset_manager = DatasetManager(config)
        self.request_session_manager = RequestSessionManager()
        self.request_executor = RequestExecutor(config)
        self.latency_analyzer = LatencyAnalyzer()
        self.concurrency_manager = ConcurrencyManager(config, self.request_executor)
        self.result_exporter = ResultExporter()
        self.visualization_generator = VisualizationGenerator(config)
        self.detailed_results = {}

    def run_benchmarks(self, prompts: List[str]) -> Dict[str, LatencyResults]:
        """
        Run benchmarks for all configurations.

        Args:
            prompts: List of prompts.

        Returns:
            Dictionary of results keyed by configuration.
        """
        session = self.request_session_manager.create_session_with_retries(BenchmarkConstants.DEFAULT_MAX_RETRIES)
        results = {}
        self.detailed_results = {}  # Store detailed results for new graph

        # Load model with call prompt "Hello" for unloading prev model
        logger.info(f"Loading {BenchmarkConstants.CLEAR_MODEL} model to unload previous model before proxy...")
        self.request_executor.send_request(session, self.config.ollama_direct_url, "Hello", use_proxy=False, model=BenchmarkConstants.CLEAR_MODEL)

        # Measure with proxy
        for conc in BenchmarkConstants.DEFAULT_CONCURRENCIES:
            logger.info(f"Measuring with proxy, concurrency {conc}...")
            detailed_data = self.concurrency_manager.measure_latencies(session, self.config.proxy_url, conc, prompts, use_proxy=True)
            # Filter out warm-up test (test_number == 1) before calculating percentiles
            detailed_data = [data for data in detailed_data if data[2] != 1]
            latencies = [data[0] for data in detailed_data] # Extract just latencies for percentiles
            
            results[f"with_proxy_conc_{conc}"] = self.latency_analyzer.compute_percentiles(latencies)
            self.detailed_results[f"with_proxy_conc_{conc}"] = detailed_data

        # Load model with call prompt "Hello" for unloading prev model
        logger.info(f"Loading {BenchmarkConstants.CLEAR_MODEL} model to unload previous model direct access...")
        self.request_executor.send_request(session, self.config.ollama_direct_url, "Hello", use_proxy=False, model=BenchmarkConstants.CLEAR_MODEL)
            
        # Measure without proxy
        for conc in BenchmarkConstants.DEFAULT_CONCURRENCIES:
            logger.info(f"Measuring without proxy, concurrency {conc}...")
            detailed_data = self.concurrency_manager.measure_latencies(session, self.config.ollama_direct_url, conc, prompts, use_proxy=False)
            # Filter out warm-up test (test_number == 1) before calculating percentiles
            detailed_data = [data for data in detailed_data if data[2] != 1]
            latencies = [data[0] for data in detailed_data]  # Extract just latencies for percentiles
            results[f"no_proxy_conc_{conc}"] = self.latency_analyzer.compute_percentiles(latencies)
            self.detailed_results[f"no_proxy_conc_{conc}"] = detailed_data

        return results

    def save_results(self, results: Dict[str, LatencyResults], output_path: Path) -> None:
        """Save results to CSV."""
        self.result_exporter.save_results(results, output_path)

    def load_results(self, input_path: Path) -> Dict[str, LatencyResults]:
        """
        Load results from CSV without executing Ollama and proxy tests.
        
        Args:
            input_path: Path to load CSV from.
            
        Returns:
            Dictionary of results keyed by configuration.
        """
        return self.result_exporter.load_results(input_path)

    def plot_results(self, results: Dict[str, LatencyResults], output_path: Path) -> None:
        """Generate and save latency comparison graph."""
        self.visualization_generator.plot_results(results, output_path)

    def save_detailed_results_to_csv(self, output_path: Path) -> None:
        """Save detailed benchmark results to CSV for Excel manipulation."""
        self.result_exporter.save_detailed_results_to_csv(self.detailed_results, output_path)

    def load_detailed_results_from_csv(self, input_path: Path) -> Dict[str, List[tuple]]:
        """
        Load detailed benchmark results from CSV without executing Ollama and proxy tests.
        
        Args:
            input_path: Path to load detailed results CSV from.
            
        Returns:
            Dictionary of detailed results.
        """
        self.detailed_results = self.result_exporter.load_detailed_results_from_csv(input_path)
        return self.detailed_results

    def save_performance_summary_to_csv(self, output_path: Path) -> None:
        """Save performance summary data to CSV for Excel manipulation, including comparison statistics."""
        self.result_exporter.save_performance_summary_to_csv(self.detailed_results, output_path)

    def load_performance_summary_from_csv(self, input_path: Path):
        """
        Load performance summary data from CSV without executing Ollama and proxy tests.
        
        Args:
            input_path: Path to load performance summary CSV from.
            
        Returns:
            DataFrame with performance summary data.
        """
        return self.result_exporter.load_performance_summary_from_csv(input_path)

    def generate_performance_visualizations(self, bench_dir: Path, detailed_path: Path, performance_summary_path: Path) -> None:
        """Generate all performance visualization graphs including the new performance summary."""
        self.visualization_generator.generate_performance_visualizations(bench_dir, detailed_path, performance_summary_path)