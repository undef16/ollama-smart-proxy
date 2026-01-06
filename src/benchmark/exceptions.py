"""Custom exceptions for the benchmarking system."""


class BenchmarkExecutionError(Exception):
    """Custom exception for benchmark execution failures."""
    pass


class DatasetLoadError(Exception):
    """Exception raised when dataset loading fails."""
    pass


class RequestError(Exception):
    """Exception raised when a request fails."""
    pass


class InvalidResponseFormatError(Exception):
    """Exception raised when response format is invalid."""
    pass