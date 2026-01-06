#!/usr/bin/env python3
"""
Utility to load benchmark results from CSV files and generate visualizations without running tests.
This script loads existing benchmark CSV files from the bench directory and creates visualizations.
"""
from pathlib import Path
import sys
import logging

from src.benchmark.result_exporter import ResultExporter
from src.benchmark.visualization_generator import VisualizationGenerator
from src.benchmark.models import BenchmarkConfig


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_and_visualize_results(bench_path: str = "bench"):
    """
    Load benchmark results from CSV files and generate visualizations without running tests.
    
    Args:
        bench_path: Path to the bench directory containing CSV files.
        
    Returns:
        Dictionary containing loaded results from all CSV files.
    """
    print(f"Loading benchmark results from directory: {bench_path}")
    
    # Create bench directory path
    bench_dir = Path(bench_path)
    
    # Initialize visualization generator
    config = BenchmarkConfig()
    viz_gen = VisualizationGenerator(config)
    
    # Check for required CSV files
    comparison_csv = bench_dir / "ollama_latency_comparison.csv"
    detailed_csv = bench_dir / "ollama_detailed_results.csv"
    perf_summary_csv = bench_dir / "performance_summary.csv"
    
    # Load and generate main comparison graph if the comparison CSV exists
    if comparison_csv.exists():
        print(f"Loading main comparison results from: {comparison_csv}")
        results = ResultExporter.load_results(comparison_csv)
        
        # Generate main comparison graph
        graph_path = bench_dir / "ollama_latency_graph.png"
        viz_gen.plot_results(results, graph_path)
        print(f"Main comparison graph generated: {graph_path}")
    else:
        print(f"Main comparison CSV not found: {comparison_csv}")
    
    # Generate performance visualizations if both detailed results and performance summary exist
    if detailed_csv.exists() and perf_summary_csv.exists():
        print(f"Loading detailed results from: {detailed_csv}")
        print(f"Loading performance summary from: {perf_summary_csv}")
        
        # Generate performance visualizations
        viz_gen.generate_performance_visualizations(bench_dir, detailed_csv, perf_summary_csv)
        print("Performance visualizations generated successfully!")
    else:
        print(f"Detailed results CSV not found: {detailed_csv}") if not detailed_csv.exists() else print("")
        print(f"Performance summary CSV not found: {perf_summary_csv}") if not perf_summary_csv.exists() else print("")
    
    # Load all results for return
    results = ResultExporter.load_results_from_bench_directory(bench_path)
    
    if results:
        print("\nSuccessfully loaded benchmark results:")
        for key, value in results.items():
            if key == 'main_results':
                print(f"  - Main results: {len(value)} configurations")
            elif key == 'detailed_results':
                print(f"  - Detailed results: {len(value)} configurations")
            elif key == 'performance_summary':
                print(f"  - Performance summary: {len(value)} rows")
    else:
        print(f"\nNo benchmark CSV files found in directory: {bench_path}")
        print("Expected files:")
        print("  - ollama_latency_comparison.csv")
        print("  - ollama_detailed_results.csv")
        print("  - performance_summary.csv")
    
    return results


def main():
    """Main entry point for loading benchmark results and generating visualizations."""
    bench_path = sys.argv[1] if len(sys.argv) > 1 else "bench"
    
    results = load_and_visualize_results(bench_path)
    
    if results:
        print(f"\nLoaded and visualized results from {bench_path}/ directory")
        return 0
    else:
        print(f"\nNo results found in {bench_path}/ directory")
        return 1


if __name__ == "__main__":
    exit(main())