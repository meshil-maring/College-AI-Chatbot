"""Phase 6.16 — Student-facing learning-resource contracts.

Student-safe projection over the EXISTING ``knowledge_sources`` table
(Phase 3.x metadata model, Phase Admin-1 admin surface). A "learning resource"
is a knowledge source the student's own institution has PUBLISHED
(``lifecycle_status = 'published'``) — the same publication boundary the locked
Phase 6.13.8 public-knowledge boundary applies to institution knowledge.

Two source types already have a dedicated student surface and are therefore
excluded so the dashboard never duplicates a section:

* ``notice``  → the Notices section (``/students/me/notices``);
* ``faq``     → answered inline by the AI assistant.

Both names come from the locked ``app.services.public_chat.PUBLIC_SOURCE_TYPES``
vocabulary — no new vocabulary is invented here.

Scope rules (enforced server-side in ``app.services.student_resources``):
the institution filter is ALWAYS the authenticated student's own institution;
the endpoint accepts no identity parameter.

Excluded by design — every storage / pipeline / tenant detail:
``storage_bucket``, ``storage_object_key``, ``file_checksum``,
``document_id``, ``document_version_id``, ``institution_id``,
``created_by_user_id``. No download URL (signed or otherwise) is produced in
this phase.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentResource(BaseModel):
    """One published learning resource for the student's own institution."""

    resource_id: UUID
    title: str
    description: str | None = None
    source_type: str
    effective_from: str | None = None
    effective_until: str | None = None

    model_config = ConfigDict(extra="forbid")


class StudentResourceList(BaseModel):
    """The authenticated student's institution learning resources (newest first)."""

    items: list[StudentResource] = Field(default_factory=list)
    total: int = 0

    model_config = ConfigDict(extra="forbid")
