from typing import Any, Dict

from pydantic import BaseModel, Field, ConfigDict


class Document(BaseModel):
    """
    Represents a retrieved document in the RAG system.

    This entity encapsulates the content of a document retrieved from
    the knowledge base or external sources, along with its source,
    relevance score, and additional metadata.
    """

    content: str = Field(..., min_length=1, description="The textual content of the document")
    source: str = Field(..., min_length=1, description="The source identifier or URL of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata associated with the document")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True
    )