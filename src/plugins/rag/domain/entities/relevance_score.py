from pydantic import BaseModel, Field, ConfigDict


class RelevanceScore(BaseModel):
    """
    Represents the relevance evaluation of a document.

    This entity encapsulates the score assigned to a document's relevance
    to a query, along with a boolean indicator and reasoning.
    """

    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score between 0.0 and 1.0")
    is_relevant: bool = Field(..., description="Boolean indicating if the document is considered relevant")
    reasoning: str = Field(..., min_length=1, description="Explanation for the relevance assessment")

    model_config = ConfigDict(validate_assignment=True)