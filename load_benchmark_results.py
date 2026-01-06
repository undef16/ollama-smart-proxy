#!/usr/bin/env python3
"""
Utility to load benchmark results without executing Ollama and proxy tests.
This script loads existing benchmark CSV files from the bench directory.
"""
from pathlib import Path
import sys
from src.benchmark.result_exporter import ResultExporter


def load_benchmark_results(bench_path: str = "bench"):
    """
    Load all benchmark results from the bench directory without executing Ollama and proxy tests.
    
    Args:
        bench_path: Path to the bench directory containing CSV files.
        
    Returns:
        Dictionary containing loaded results from all CSV files.
    """
    print(f"Loading benchmark results from directory: {bench_path}")
    
    exporter = ResultExporter()
    results = exporter.load_results_from_bench_directory(bench_path)
    
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
    """Main entry point for loading benchmark results."""
    bench_path = sys.argv[1] if len(sys.argv) > 1 else "bench"
    
    results = load_benchmark_results(bench_path)
    
    if results:
        print(f"\nLoaded {len(results)} result sets from {bench_path}/ directory")
        return 0
    else:
        print(f"\nNo results found in {bench_path}/ directory")
        return 1


if __name__ == "__main__":
    exit(main())