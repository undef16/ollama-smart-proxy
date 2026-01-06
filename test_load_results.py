#!/usr/bin/env python3
"""
Test script to verify the new load_results functionality works correctly.
This script creates sample CSV files and tests the loading functions.
"""
import pandas as pd
from pathlib import Path
import tempfile
import os
from src.benchmark.result_exporter import ResultExporter
from src.benchmark.models import LatencyResults

def test_load_results():
    """Test the load_results functionality."""
    print("Testing load_results functionality...")
    
    # Create sample data
    sample_results = {
        'with_proxy_conc_1': LatencyResults(p50=0.1, p90=0.2, p95=0.3),
        'no_proxy_conc_1': LatencyResults(p50=0.15, p90=0.25, p95=0.35),
        'with_proxy_conc_2': LatencyResults(p50=0.12, p90=0.22, p95=0.32),
        'no_proxy_conc_2': LatencyResults(p50=0.17, p90=0.27, p95=0.37)
    }
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        csv_path = temp_path / "test_results.csv"
        
        # Save the sample results to CSV
        exporter = ResultExporter()
        exporter.save_results(sample_results, csv_path)
        print(f"Saved sample results to: {csv_path}")
        
        # Load the results back
        loaded_results = exporter.load_results(csv_path)
        print(f"Loaded results from: {csv_path}")
        
        # Verify the loaded results match the original
        print("\nOriginal results:")
        for key, value in sample_results.items():
            print(f"  {key}: p50={value.p50}, p90={value.p90}, p95={value.p95}")
        
        print("\nLoaded results:")
        for key, value in loaded_results.items():
            print(f"  {key}: p50={value.p50}, p90={value.p90}, p95={value.p95}")
        
        # Check if they match
        success = True
        for key in sample_results:
            if (abs(sample_results[key].p50 - loaded_results[key].p50) > 0.0001 or
                abs(sample_results[key].p90 - loaded_results[key].p90) > 0.0001 or
                abs(sample_results[key].p95 - loaded_results[key].p95) > 0.0001):
                success = False
                break
        
        if success:
            print("\n✓ Test passed: Loaded results match original results")
        else:
            print("\n✗ Test failed: Loaded results do not match original results")
        
        return success

def test_load_detailed_results():
    """Test the load_detailed_results_from_csv functionality."""
    print("\nTesting load_detailed_results_from_csv functionality...")
    
    # Create sample detailed results
    sample_detailed_results = {
        'with_proxy_conc_1': [(0.1, 100), (0.15, 150), (0.2, 200)],
        'no_proxy_conc_1': [(0.08, 100), (0.12, 150), (0.18, 200)],
        'with_proxy_conc_2': [(0.18, 100), (0.25, 150), (0.3, 200)],
        'no_proxy_conc_2': [(0.15, 100), (0.22, 150), (0.28, 200)]
    }
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        csv_path = temp_path / "test_detailed_results.csv"
        
        # Save the sample detailed results to CSV
        exporter = ResultExporter()
        exporter.save_detailed_results_to_csv(sample_detailed_results, csv_path)
        print(f"Saved sample detailed results to: {csv_path}")
        
        # Load the detailed results back
        loaded_detailed_results = exporter.load_detailed_results_from_csv(csv_path)
        print(f"Loaded detailed results from: {csv_path}")
        
        # Verify the loaded results match the original
        print("\nOriginal detailed results:")
        for key, value in sample_detailed_results.items():
            print(f"  {key}: {value}")
        
        print("\nLoaded detailed results:")
        for key, value in loaded_detailed_results.items():
            print(f"  {key}: {value}")
        
        # Check if they match (accounting for floating point precision)
        success = True
        for key in sample_detailed_results:
            original_list = sample_detailed_results[key]
            loaded_list = loaded_detailed_results[key]
            
            if len(original_list) != len(loaded_list):
                success = False
                break
                
            for i in range(len(original_list)):
                orig_latency, orig_prompt = original_list[i]
                load_latency, load_prompt = loaded_list[i]
                
                if (abs(orig_latency - load_latency) > 0.0001 or orig_prompt != load_prompt):
                    success = False
                    break
        
        if success:
            print("\n✓ Test passed: Loaded detailed results match original results")
        else:
            print("\n✗ Test failed: Loaded detailed results do not match original results")
        
        return success

def test_load_performance_summary():
    """Test the load_performance_summary_from_csv functionality."""
    print("\nTesting load_performance_summary_from_csv functionality...")
    
    # Create sample detailed results for performance summary
    sample_detailed_results = {
        'with_proxy_conc_1': [(0.1, 100), (0.15, 150), (0.2, 200)],
        'no_proxy_conc_1': [(0.08, 100), (0.12, 150), (0.18, 200)],
        'with_proxy_conc_2': [(0.18, 100), (0.25, 150), (0.3, 200)],
        'no_proxy_conc_2': [(0.15, 100), (0.22, 150), (0.28, 200)]
    }
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        csv_path = temp_path / "test_performance_summary.csv"
        
        # Save the sample performance summary to CSV
        exporter = ResultExporter()
        exporter.save_performance_summary_to_csv(sample_detailed_results, csv_path)
        print(f"Saved sample performance summary to: {csv_path}")
        
        # Load the performance summary back
        loaded_summary = exporter.load_performance_summary_from_csv(csv_path)
        print(f"Loaded performance summary from: {csv_path}")
        
        # Verify we got a DataFrame back
        if isinstance(loaded_summary, pd.DataFrame) and not loaded_summary.empty:
            print(f"\n✓ Test passed: Loaded performance summary is a valid DataFrame with {len(loaded_summary)} rows")
            print(f" Columns: {list(loaded_summary.columns)}")
            return True
        else:
            print("\n✗ Test failed: Loaded performance summary is not a valid DataFrame")
            return False

def main():
    """Run all tests."""
    print("Testing new load functions for benchmark results...\n")
    
    test1_passed = test_load_results()
    test2_passed = test_load_detailed_results()
    test3_passed = test_load_performance_summary()
    
    print(f"\nOverall results:")
    print(f"  load_results: {'PASS' if test1_passed else 'FAIL'}")
    print(f"  load_detailed_results_from_csv: {'PASS' if test2_passed else 'FAIL'}")
    print(f"  load_performance_summary_from_csv: {'PASS' if test3_passed else 'FAIL'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    print(f"\nAll tests: {'PASS' if all_passed else 'FAIL'}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)