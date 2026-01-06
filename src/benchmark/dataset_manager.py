"""Manages dataset loading and preparation."""
import logging
from typing import List
from datasets import load_dataset  # Requires: pip install datasets

from .models import BenchmarkConfig
from .constants import BenchmarkConstants
from .exceptions import DatasetLoadError


# Configure logging
logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages dataset loading and preparation."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def prepare_dataset(self) -> List[str]:
        """
        Download and prepare SWE-Bench dataset from Hugging Face.

        Returns:
            List of prepared prompts.

        Raises:
            DatasetLoadError: If dataset cannot be loaded or has insufficient data.
        """
        logger.info("Downloading SWE-Bench dataset from Hugging Face...")
        try:
            ds = load_dataset("princeton-nlp/SWE-bench", split="test")
            # ds = load_dataset("tatsu-lab/alpaca", split="train")
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise DatasetLoadError("Unable to load SWE-Bench dataset") from e

        dataset_size = len(ds)  # type: ignore
        if dataset_size < BenchmarkConstants.DEFAULT_REQUESTS:
            raise DatasetLoadError(f"Dataset has only {dataset_size} items, but {BenchmarkConstants.DEFAULT_REQUESTS} are required")

        problem_statements = ds['problem_statement'][:BenchmarkConstants.DEFAULT_REQUESTS]  # type: ignore
        # problem_statements = ds['instruction'][:BenchmarkConstants.DEFAULT_REQUESTS]  # type: ignore
        prompts = []

        for problem in problem_statements:
            prompt = f"As a senior software developer fix this software engineering issue: {problem}"
            prompts.append(prompt)

        logger.info(f"Prepared {len(prompts)} prompts from SWE-Bench.")
        return prompts