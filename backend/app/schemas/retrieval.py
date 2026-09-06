from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class RetrievalRequest(BaseModel):
    query: str = Field(strict=True)
    top_k: int = Field(default=10, strict=True)
    institution_id: UUID | None = None
    knowledge_source_id: UUID | None = None
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    processing_run_id: UUID | None = None
    model_name: str | None = None
    context: dict | None = None

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("query must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("query must not be empty")
        return normalized

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("top_k must be a positive integer")
        return value

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("model_name must not be empty")
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> "RetrievalRequest":
        if not any(
            value is not None
            for value in (
                self.institution_id,
                self.knowledge_source_id,
                self.document_id,
                self.document_version_id,
                self.processing_run_id,
            )
        ):
            raise ValueError("at least one retrieval filter is required")
        return self


class RetrievalResult(BaseModel):
    chunk_id: UUID
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    text: str
    similarity_score: float
    metadata: dict = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    results: list[RetrievalResult]