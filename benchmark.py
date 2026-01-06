# Legacy entry point for backward compatibility
# Use the new benchmark package instead

import sys
from src.benchmark import BenchmarkConfig, BenchmarkRunner


if __name__ == "__main__":
    # Check command line arguments to determine if tests should be run
    run_tests = True  # Default behavior is to run tests
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ['--no-tests', '--load-only', 'load']:
            run_tests = False

    config = BenchmarkConfig()
    runner = BenchmarkRunner(config, run_tests=run_tests)
    runner.run()
