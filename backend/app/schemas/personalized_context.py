"""Phase 6.14.5 — Personalized retrieval context contracts.

Single server-side aggregation model assembled ONLY by
``app.services.personalized_retrieval`` from the EXISTING boundaries:

* ``knowledge`` — institutional RAG chunks retrieved through the existing
  Phase 3 retrieval service (``app.services.retrieval.retrieve``), scoped to
  the authenticated student's own institution and filtered through the
  Phase 6.13.8 knowledge-visibility boundary (published knowledge sources of
  that institution only). Chunks reuse the existing Phase 4
  ``RetrievedChunk`` contract verbatim (same shape the chat boundary already
  uses), so no new chunk model is invented.
* ``academic`` — the Phase 6.14.4 ``StudentAcademicContext`` model verbatim
  (student identity labels, attendance, published academic + test results),
  produced by the existing academic-context authorization boundary.

Context separation (required by the phase contract): institutional knowledge
and private student academic data remain two DISTINCT, explicitly named
fields — they are never flattened into one anonymous list, so the later
prompt-construction phase (and the security tests) can always distinguish
"what the institution's knowledge says" from "what this student's own data
is". Only the student's own benign institution id label is carried on the
knowledge block (no other internal identifier is introduced).

Safety: every model uses ``extra="forbid"``. No passwords, auth tokens, or
database credentials exist anywhere in the tree; no other student's and no
other institution's data can enter it (identity is derived exclusively from
the authenticated ``current_user``).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generation import RetrievedChunk
from app.schemas.student_academic_context import StudentAcademicContext


class InstitutionalKnowledge(BaseModel):
    """Institution-scoped RAG knowledge authorized for this student.

    ``institution_id`` is the student's OWN server-resolved tenant — a benign
    label proving which institution's knowledge corpus the chunks came from.
    Chunks are the existing Phase 4 ``RetrievedChunk`` contract.
    """

    institution_id: UUID | None = None
    chunks: list[RetrievedChunk] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PersonalizedContext(BaseModel):
    """Secure personalized retrieval boundary for one authenticated student.

    Two explicitly separated sources:

        PersonalizedContext
        ├── knowledge: InstitutionalKnowledge   (institutional RAG chunks)
        └── academic:  StudentAcademicContext   (private student academic data:
            identity / attendance / results)
    """

    query: str = ""
    knowledge: InstitutionalKnowledge = Field(
        default_factory=InstitutionalKnowledge
    )
    academic: StudentAcademicContext = Field(
        default_factory=StudentAcademicContext
    )

    model_config = ConfigDict(extra="forbid")
