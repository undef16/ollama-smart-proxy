"""Handles exporting benchmark results to various formats."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd
import numpy as np
from .models import LatencyResults


# Configure logging
logger = logging.getLogger(__name__)


class ResultExporter:
    """Handles exporting benchmark results to various formats."""
    
    @staticmethod
    def save_results(results: Dict[str, Any], output_path: Union[Path, str]) -> None:
        """
        Save results to CSV.

        Args:
            results: Dictionary of results.
            output_path: Path to save CSV.
        """
        df = pd.DataFrame({k: v.__dict__ for k, v in results.items()}).T
        df.to_csv(output_path)
        logger.info(f"CSV saved: {output_path}")

    @staticmethod
    def load_results(input_path: Union[Path, str]) -> Dict[str, LatencyResults]:
        """
        Load results from CSV without executing Ollama and proxy tests.

        Args:
            input_path: Path to load CSV from.

        Returns:
            Dictionary of results keyed by configuration.
        """
        df = pd.read_csv(input_path, index_col=0)
        results = {}
        
        for idx, row in df.iterrows():
            # Create LatencyResults object from row data
            latency_results = LatencyResults(
                p50=row['p50_latency'] if 'p50_latency' in row else row.get('p50', 0.0),
                p90=row['p90_latency'] if 'p90_latency' in row else row.get('p90', 0.0),
                p95=row['p95_latency'] if 'p95_latency' in row else row.get('p95', 0.0)
            )
            results[idx] = latency_results
        
        logger.info(f"Results loaded from CSV: {input_path}")
        return results

    @staticmethod
    def save_detailed_results_to_csv(detailed_results: Dict[str, List[tuple]], output_path: Union[Path, str]) -> None:
        """
        Save detailed benchmark results to CSV for Excel manipulation.

        Args:
            detailed_results: Dictionary of detailed results.
            output_path: Path to save detailed results CSV.
        """
        if not detailed_results:
            logger.warning("No detailed results available for saving")
            return

        # Flatten all detailed results for analysis
        all_test_data = []
        for config_name, results in detailed_results.items():
            # Extract concurrency from config name (e.g., "with_proxy_conc_5" -> 5)
            import re
            concurrency_match = re.search(r'conc_(\d+)', config_name)
            concurrency = int(concurrency_match.group(1)) if concurrency_match else 0
            
            for result in results:
                latency, prompt_length, test_number = result
                # Determine if this is proxy or ollama test
                is_proxy = 'with_proxy' in config_name
                # Test numbers are already adjusted (test 1 was filtered in ollama_benchmark.py)
                # So tests 2,3,4,5 become 1,2,3,4 - just use test_number directly
                all_test_data.append({
                    'test_number': test_number - 1,
                    'prompt_length': prompt_length,
                    'latency_ms': latency * 1000,  # Convert to ms
                    'concurrency': concurrency,
                    'config': config_name,
                    'is_proxy': is_proxy,
                    'config_type': 'Proxy' if is_proxy else 'Ollama'
                })

        if not all_test_data:
            logger.warning("No test data available for detailed CSV export")
            return

        df = pd.DataFrame(all_test_data)
        # Sort by concurrency and test_number before saving
        df = df.sort_values(by=['concurrency', 'test_number'])
        df.to_csv(output_path, index=False)
        logger.info(f"Detailed results saved to CSV: {output_path}")

    @staticmethod
    def load_detailed_results_from_csv(input_path: Union[Path, str]) -> Dict[str, List[tuple]]:
        """
        Load detailed benchmark results from CSV without executing Ollama and proxy tests.

        Args:
            input_path: Path to load detailed results CSV from.

        Returns:
            Dictionary of detailed results with tuples (latency, prompt_length, test_number).
        """
        df = pd.read_csv(input_path)
        detailed_results = {}
        
        for _, row in df.iterrows():
            config = row['config']
            latency = row['latency_ms'] / 1000  # Convert from ms back to seconds
            prompt_length = row['prompt_length']
            # Restore original test_number from adjusted value (add back the warm-up skip)
            test_number = int(row['test_number']) + 1
            
            if config not in detailed_results:
                detailed_results[config] = []
            
            detailed_results[config].append((latency, prompt_length, test_number))
        
        logger.info(f"Detailed results loaded from CSV: {input_path}")
        return detailed_results

    @staticmethod
    def save_performance_summary_to_csv(detailed_results: Dict[str, List[tuple]], output_path: Union[Path, str]) -> None:
        """
        Save performance summary data to CSV for Excel manipulation, including comparison statistics.

        Args:
            detailed_results: Dictionary of detailed results.
            output_path: Path to save performance summary CSV.
        """
        if not detailed_results:
            logger.warning("No detailed results available for saving")
            return

        # Flatten all detailed results for analysis
        all_test_data = []
        for config_name, results in detailed_results.items():
            # Extract concurrency from config name (e.g., "with_proxy_conc_5" -> 5)
            import re
            concurrency_match = re.search(r'conc_(\d+)', config_name)
            concurrency = int(concurrency_match.group(1)) if concurrency_match else 0
            
            for result in results:
                latency, prompt_length, test_number = result
                # Determine if this is proxy or ollama test
                is_proxy = 'with_proxy' in config_name
                # Test numbers are already adjusted (test 1 was filtered in ollama_benchmark.py)
                # So tests 2,3,4,5 become 1,2,3,4 - just use test_number directly
                all_test_data.append({
                    'test_number': test_number - 1,
                    'prompt_length': prompt_length,
                    'latency_ms': latency * 1000,  # Convert to ms
                    'concurrency': concurrency,
                    'config': config_name,
                    'is_proxy': is_proxy,
                    'config_type': 'Proxy' if is_proxy else 'Ollama'
                })

        if not all_test_data:
            logger.warning("No test data available for performance summary")
            return

        df = pd.DataFrame(all_test_data)

        # Create performance comparison data
        comparison_data = []
        for test_num in df['test_number'].unique():
            test_df = df[df['test_number'] == test_num]
            ollama_tests = test_df[test_df['config_type'] == 'Ollama']
            proxy_tests = test_df[test_df['config_type'] == 'Proxy']
            
            if len(ollama_tests) > 0 and len(proxy_tests) > 0:
                ollama_latency = ollama_tests['latency_ms'].mean()
                proxy_latency = proxy_tests['latency_ms'].mean()
                improvement = ((ollama_latency - proxy_latency) / ollama_latency) * 100 if ollama_latency > 0 else 0
                ms_improvement = ollama_latency - proxy_latency
                
                comparison_data.append({
                    'test_number': test_num,
                    'ollama_latency_ms': ollama_latency,
                    'proxy_latency_ms': proxy_latency,
                    'improvement_pct': improvement,
                    'improvement_ms': ms_improvement
                })
        
        if comparison_data:
            comp_df = pd.DataFrame(comparison_data)
            
            # Calculate summary statistics
            total_pct_improvement = comp_df['improvement_pct'].sum()
            avg_pct_improvement = comp_df['improvement_pct'].mean()
            total_ms_improvement = comp_df['improvement_ms'].sum()
            avg_ms_improvement = comp_df['improvement_ms'].mean()
            best_improvement_pct = comp_df['improvement_pct'].max()
            worst_improvement_pct = comp_df['improvement_pct'].min()
            std_dev_improvement_pct = comp_df['improvement_pct'].std()
            
            # Add 4 empty padding rows before the summary
            padding_rows = []
            for i in range(4):
                padding_row = {
                    'test_number': np.nan,
                    'ollama_latency_ms': np.nan,
                    'proxy_latency_ms': np.nan,
                    'improvement_pct': np.nan,
                    'improvement_ms': np.nan
                }
                padding_rows.append(padding_row)
            
            # Add summary row to the comparison data
            summary_row = {
                'test_number': 'SUMMARY',
                'ollama_latency_ms': avg_pct_improvement, # Using this column for summary identifier
                'proxy_latency_ms': len(comp_df),
                'improvement_pct': total_pct_improvement,
                'improvement_ms': total_ms_improvement
            }
            padding_df = pd.DataFrame(padding_rows)
            comp_df = pd.concat([comp_df, padding_df, pd.DataFrame([summary_row])], ignore_index=True)
            
            comp_df.to_csv(output_path, index=False)
            logger.info(f"Performance summary saved to CSV: {output_path}")

    @staticmethod
    def load_results_from_bench_directory(bench_path: Union[Path, str] = "bench") -> Dict[str, Any]:
        """
        Load all benchmark results from the bench directory without executing Ollama and proxy tests.

        Args:
            bench_path: Path to the bench directory containing CSV files.

        Returns:
            Dictionary containing loaded results from all CSV files.
        """
        bench_path = Path(bench_path)
        results = {}
        
        # Load main results if they exist
        main_csv = bench_path / "ollama_latency_comparison.csv"
        if main_csv.exists():
            results['main_results'] = ResultExporter.load_results(main_csv)
            logger.info(f"Main results loaded from: {main_csv}")
        
        # Load detailed results if they exist
        detailed_csv = bench_path / "ollama_detailed_results.csv"
        if detailed_csv.exists():
            results['detailed_results'] = ResultExporter.load_detailed_results_from_csv(detailed_csv)
            logger.info(f"Detailed results loaded from: {detailed_csv}")
        
        # Load performance summary if it exists
        perf_summary_csv = bench_path / "performance_summary.csv"
        if perf_summary_csv.exists():
            results['performance_summary'] = ResultExporter.load_performance_summary_from_csv(perf_summary_csv)
            logger.info(f"Performance summary loaded from: {perf_summary_csv}")
        
        if not results:
            logger.warning(f"No benchmark CSV files found in directory: {bench_path}")
        
        return results

    @staticmethod
    def load_performance_summary_from_csv(input_path: Union[Path, str]) -> pd.DataFrame:
        """
        Load performance summary data from CSV without executing Ollama and proxy tests.

        Args:
            input_path: Path to load performance summary CSV from.

        Returns:
            DataFrame with performance summary data.
        """
        df = pd.read_csv(input_path)
        logger.info(f"Performance summary loaded from CSV: {input_path}")
        return df