"""Benchmark runner to orchestrate the execution of benchmarks."""
from pathlib import Path
from typing import Dict
import logging

from .result_exporter import ResultExporter

from .models import BenchmarkConfig, LatencyResults
from .ollama_benchmark import OllamaBenchmark


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Orchestrates the execution of benchmarks and manages output."""
    
    def __init__(self, config: BenchmarkConfig, run_tests: bool = True):
        self.config = config
        self.run_tests = run_tests
        self.benchmark = OllamaBenchmark(config)

    def run(self) -> None:
        """Run the complete benchmarking process."""
        try:
            # Create bench directory
            bench_dir = Path("bench")
            bench_dir.mkdir(exist_ok=True)

            # Define CSV file paths
            comparison_csv_path = bench_dir / "ollama_latency_comparison.csv"
            detailed_csv_path = bench_dir / "ollama_detailed_results.csv"
            performance_summary_path = bench_dir / "performance_summary.csv"
            
            # Try to load and generate graphs from existing CSV files first
            # This allows visualization without running new benchmarks
            if comparison_csv_path.exists():
                logger.info(f"Loading existing comparison results from: {comparison_csv_path}")
                results = ResultExporter.load_results(comparison_csv_path)
                graph_path = bench_dir / "ollama_latency_graph.png"
                self.benchmark.plot_results(results, graph_path)
                logger.info(f"Main comparison graph generated from existing data: {graph_path}")
            
            # Generate performance visualizations from existing CSV files if they exist
            if detailed_csv_path.exists() and performance_summary_path.exists():
                logger.info(f"Loading existing detailed results from: {detailed_csv_path}")
                logger.info(f"Loading existing performance summary from: {performance_summary_path}")
                
                # Generate performance visualizations from existing data
                self.benchmark.generate_performance_visualizations(bench_dir, detailed_csv_path, performance_summary_path)
                logger.info("Performance visualizations generated from existing data")
            
            # Run actual benchmarks if the flag is set to True
            if self.run_tests:
                # Prepare dataset
                logger.info("Preparing dataset...")
                prompts = self.benchmark.dataset_manager.prepare_dataset()
                
                # Run benchmarks
                logger.info("Running benchmarks...")
                results = self.benchmark.run_benchmarks(prompts)

                # Save results
                self.benchmark.save_results(results, comparison_csv_path)
                
                # Generate graphs from new results
                graph_path = bench_dir / "ollama_latency_graph.png"
                self.benchmark.plot_results(results, graph_path)

                # Generate detailed results CSV for performance analysis
                if self.benchmark.detailed_results:
                    logger.info("Generating detailed results and performance summary...")
                    
                    # Save detailed results CSV
                    self.benchmark.save_detailed_results_to_csv(detailed_csv_path)
                    
                    # Generate performance summary CSV
                    self.benchmark.save_performance_summary_to_csv(performance_summary_path)
                    
                    # Generate performance visualizations
                    self.benchmark.generate_performance_visualizations(bench_dir, detailed_csv_path, performance_summary_path)
            else:
                # If not running tests, still try to generate visualizations from existing files
                if detailed_csv_path.exists() and performance_summary_path.exists():
                    logger.info("Generating visualizations from existing data (no new tests run)")
                    self.benchmark.generate_performance_visualizations(bench_dir, detailed_csv_path, performance_summary_path)

            logger.info("Benchmark completed successfully!")
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}", stack_info=True)
            raise


