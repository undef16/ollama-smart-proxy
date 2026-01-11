from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer, ConfigDict


class Query(BaseModel):
    """
    Represents a user query in the RAG system.

    This entity encapsulates the details of a query submitted by a user,
    including the query text, timestamp, and a unique identifier.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the query")
    text: str = Field(..., min_length=1, description="The text content of the user query")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the query was created")

    model_config = ConfigDict(validate_assignment=True)

    @field_serializer('id')
    def serialize_uuid(self, uuid_value: UUID) -> str:
        return str(uuid_value)

    @field_serializer('timestamp')
    def serialize_datetime(self, dt_value: datetime) -> str:
        return dt_value.isoformat()