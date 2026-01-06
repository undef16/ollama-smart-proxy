"""Generates visualizations from benchmark results."""
import logging
from pathlib import Path
from typing import Dict, Any, Union
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from .models import BenchmarkConfig, LatencyResults
from .constants import BenchmarkConstants


# Configure logging
logger = logging.getLogger(__name__)


class VisualizationGenerator:
    """Generates visualizations from benchmark results."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def plot_results(self, results: Dict[str, LatencyResults], output_path: Union[Path, str]) -> None:
        """
        Generate and save latency comparison graph.

        Args:
            results: Dictionary of results.
            output_path: Path to save plot.
        """
        metrics = ["p50", "p90", "p95"]
        fig, axs = plt.subplots(2, 3, figsize=(15, 10))

        for i, metric in enumerate(metrics):
            # Check which concurrency levels are available in the results
            available_concurrencies = [c for c in BenchmarkConstants.DEFAULT_CONCURRENCIES
                                     if f"no_proxy_conc_{c}" in results and f"with_proxy_conc_{c}" in results]
            
            if not available_concurrencies:
                logger.warning(f"No data available for {metric} metric. Skipping plot.")
                continue
                
            no_proxy = [getattr(results[f"no_proxy_conc_{c}"], metric) * 1000 for c in available_concurrencies]  # Convert to ms
            with_proxy = [getattr(results[f"with_proxy_conc_{c}"], metric) * 1000 for c in available_concurrencies]  # Convert to ms
            x = np.arange(len(available_concurrencies))
            width = 0.35

            # Bar plots on top row
            bars1 = axs[0, i].bar(x - width/2, no_proxy, width, label="Ollama")
            bars2 = axs[0, i].bar(x + width/2, with_proxy, width, label="Proxy")
            axs[0, i].set_title(f"{metric.upper()} Latency (Bar)")
            axs[0, i].set_xticks(x)
            axs[0, i].set_xticklabels([int(c) for c in available_concurrencies])
            axs[0, i].set_xlabel("Concurrency")
            axs[0, i].set_ylabel("Latency (ms)")
            axs[0, i].legend()

            # Add values on top of bars
            for bar, val in zip(bars1, no_proxy):
                axs[0, i].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val:.0f}', ha='center', va='bottom', fontsize=8)
            for bar, val in zip(bars2, with_proxy):
                axs[0, i].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val:.0f}', ha='center', va='bottom', fontsize=8)

            # Line plots on bottom row
            axs[1, i].plot([float(c) for c in available_concurrencies], no_proxy, label="Ollama", marker='o', linestyle='-')
            axs[1, i].plot([float(c) for c in available_concurrencies], with_proxy, label="Proxy", marker='s', linestyle='--')
            axs[1, i].set_title(f"{metric.upper()} Latency (Line)")
            axs[1, i].set_xlabel("Concurrency")
            axs[1, i].set_ylabel("Latency (ms)")
            axs[1, i].legend()
            axs[1, i].grid(True)

        plt.tight_layout()
        plt.savefig(output_path)
        logger.info(f"Graph saved: {output_path}")

    def create_performance_summary_visualization(self, detailed_path: Union[Path, str], performance_summary_path: Union[Path, str], output_path: Union[Path, str]) -> None:
        """
        Create performance summary visualization with percentage improvement and time saving in 2 columns.
        
        Args:
            detailed_path: Path to detailed results CSV
            performance_summary_path: Path to performance summary CSV
            output_path: Path to save the performance summary visualization
        """
        import pandas as pd
        
        # Load the performance summary data
        comp_df = pd.read_csv(performance_summary_path)
        # Filter out non-numeric test numbers to get only actual test data
        test_data = comp_df[comp_df['test_number'].apply(lambda x: str(x).isdigit())]
        
        # Convert test_number to numeric to avoid matplotlib categorical warning
        test_data = test_data.copy()
        test_data['test_number'] = pd.to_numeric(test_data['test_number'])
        
        # Create a figure with increased padding - changed to 2 rows instead of 2 columns
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))
        fig.suptitle('Performance Summary: Proxy vs Ollama', fontsize=16, y=0.95)
        ollama_color = '#1f77b4'  # Blue for Ollama
        proxy_color = '#ff7f0e'   # Orange for Proxy
        
        # Top row: Percentage improvement
        if len(test_data) > 0:
            improvements = test_data['improvement_pct']
            # Use proxy color if more values are positive, otherwise ollama color
            positive_count = sum(1 for x in improvements if x > 0)
            main_color = proxy_color # if positive_count > len(improvements) / 2 else ollama_color
            
            # For large datasets (>2000 points), consider subsampling for better performance and readability
            if len(test_data) > 2000:
                # Subsample to approximately 2000 points while maintaining the overall trend
                step = len(test_data) // 2000 + 1
                subsampled_data = test_data.iloc[::step]
                subsampled_improvements = improvements[::step]
                ax1.plot(subsampled_data['test_number'], subsampled_improvements, color=main_color, marker='', linestyle='-', linewidth=1.0)
            else:
                ax1.plot(test_data['test_number'], improvements, color=main_color, marker='', linestyle='-', linewidth=0.8)
                
            ax1.set_title('Percentage Improvement (%)', pad=20)
            ax1.set_xlabel('Test Number')
            ax1.set_ylabel('Improvement Percent')
            ax1.axhline(0, color='black', linestyle='--', alpha=0.7)
            ax1.grid(True, alpha=0.3)
        
        # Bottom row: Time saving
        if len(test_data) > 0:
            time_savings = test_data['improvement_ms']
            # Use proxy color if more values are positive, otherwise ollama color
            positive_count = sum(1 for x in time_savings if x > 0)
            main_color = ollama_color # if positive_count > len(time_savings) / 2 else ollama_color
            
            # For large datasets (>2000 points), consider subsampling for better performance and readability
            if len(test_data) > 2000:
                # Subsample to approximately 2000 points while maintaining the overall trend
                step = len(test_data) // 2000 + 1
                subsampled_data = test_data.iloc[::step]
                subsampled_time_savings = time_savings[::step]
                ax2.plot(subsampled_data['test_number'], subsampled_time_savings, color=main_color, marker='', linestyle='-', linewidth=1.0)
            else:
                ax2.plot(test_data['test_number'], time_savings, color=main_color, marker='', linestyle='-', linewidth=0.8)
                
            ax2.set_title('Time Saving (ms)', pad=20)
            ax2.set_xlabel('Test Number')
            ax2.set_ylabel('Time Saving (ms)')
            ax2.axhline(0, color='black', linestyle='--', alpha=0.7)
            ax2.grid(True, alpha=0.3)
        
        # Calculate and display summary statistics at the center bottom
        if len(test_data) > 0:
            avg_improvement_pct = test_data['improvement_pct'].mean()
            total_improvement_pct = test_data['improvement_pct'].sum()
            avg_improvement_ms = test_data['improvement_ms'].mean()
            total_improvement_ms = test_data['improvement_ms'].sum()
            num_tests = len(test_data)
            
            # Remove any background box by using text positioning without a box
            summary_text = f"SUMMARY:\nTests: {num_tests}\nAvg Improvement: {avg_improvement_pct:.2f}%\nTotal Improvement: {total_improvement_pct:.2f}%\nAvg Time Saved: {avg_improvement_ms:.2f}ms\nTotal Time Saved: {total_improvement_ms:.2f}ms"
            
            # Position the summary text in the center bottom, spanning both subplots
            # Move it down further to accommodate visual padding
            fig.text(0.5, 0.01, summary_text, ha='center', va='bottom',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8, edgecolor="none"),
                    fontsize=10, weight='bold')
        
        # Increase internal padding
        plt.tight_layout(rect=(0, 0.1, 1, 0.9))  # Make more room for the summary text at the bottom
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Performance summary visualization saved: {output_path}")

    def generate_performance_visualizations(self, bench_dir: Union[Path, str], detailed_path: Union[Path, str], performance_summary_path: Union[Path, str]) -> None:
        """
        Generate all performance visualization graphs including the new performance summary.
        
        Args:
            bench_dir: Directory to save visualizations
            detailed_path: Path to detailed results CSV
            performance_summary_path: Path to performance summary CSV
        """
        # Create performance summary visualization
        summary_viz_path = Path(bench_dir) / "performance_summary.png"
        self.create_performance_summary_visualization(detailed_path, performance_summary_path, summary_viz_path)