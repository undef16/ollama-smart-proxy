from dataclasses import dataclass
from typing import List

@dataclass
class ModelResponse:
    """Data structure for model responses."""
    model: str
    response: str

@dataclass
class ScoreResult:
    """Data structure for scoring results."""
    response: str
    scores: List[float]

    @property
    def average_score(self) -> float:
        """Calculate the average score."""
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)