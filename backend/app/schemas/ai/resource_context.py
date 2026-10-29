"""Reader-safe resource context for new answers and restored conversations."""

from uuid import UUID
from pydantic import BaseModel


class ResourceChatContext(BaseModel):
    knowledge_source_id: UUID
    title: str | None = None
    available: bool = True
