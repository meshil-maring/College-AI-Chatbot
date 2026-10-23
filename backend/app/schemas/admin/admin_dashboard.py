"""Institution-scoped account, knowledge and communication summaries.

Closed models expose display fields and measured counts only. Internal
identifiers and retired academic metrics are excluded. None means that a
metric is unavailable; zero means a measured empty result.
"""

from pydantic import BaseModel, Field


class DashboardInstitution(BaseModel):
    """Safe, display-only identity of the caller's own institution.

    Branding beyond the human name/code is not projected: the Phase 7.13
    branding columns are platform-managed configuration and the University
    Admin has no branding-management surface in this application.
    """

    name: str
    code: str
    status: str


class DashboardStudents(BaseModel):
    """Student counts for ONE institution.

    ``pending_approvals`` mirrors exactly the predicate the approval queue uses
    (``approval_status = 'pending'``), so the card and the queue can never
    disagree. ``active`` is the account profile status (``status='active'``
    AND ``is_active``), NOT the approval status.
    """

    total: int = Field(ge=0)
    pending_approvals: int = Field(ge=0)
    approved: int = Field(ge=0)
    active: int = Field(ge=0)


class DashboardKnowledge(BaseModel):
    """Knowledge/document counts for ONE institution.

    ``sources_active`` uses the existing
    ``app.repositories.admin.admin_knowledge.ACTIVE_LIFECYCLE_STATUSES`` vocabulary
    (draft / under_review / approved / published) so "active" means the same
    thing here as on the Documents screen.

    ``failed_processing_runs`` is ``None`` (rendered "Unavailable") rather than
    a number. ``document_processing_runs`` has no ``institution_id`` column;
    its tenant is only reachable through a three-level nested embed
    (runs -> document_versions -> documents -> knowledge_sources) that this
    phase does not introduce. Reporting ``0`` would be a fabricated metric.
    """

    sources_total: int = Field(ge=0)
    sources_active: int = Field(ge=0)
    documents_total: int = Field(ge=0)
    failed_processing_runs: int | None = None


class DashboardRecentNotice(BaseModel):
    """One recent notice, projected to display fields only (no ``notice_id``)."""

    title: str
    category: str
    priority: str
    published_at: str | None = None


class DashboardCommunication(BaseModel):
    """FAQ / notice summary for ONE institution."""

    active_faqs: int = Field(ge=0)
    active_notices: int = Field(ge=0)
    recent_notices: list[DashboardRecentNotice] = Field(default_factory=list)


class DashboardQuickAction(BaseModel):
    """A navigation affordance pointing at an EXISTING admin screen.

    ``view`` is one of the ``AdminView`` keys already defined in
    ``frontend/src/features/admin/adminNavigation.ts``. The backend declares the
    affordance; the frontend only navigates. No action is offered whose target
    screen does not already exist.
    """

    view: str
    label: str
    description: str


class DashboardResponse(BaseModel):
    """The complete ``GET /api/v1/admin/dashboard`` payload."""

    institution: DashboardInstitution
    students: DashboardStudents
    knowledge: DashboardKnowledge
    communication: DashboardCommunication
    quick_actions: list[DashboardQuickAction] = Field(default_factory=list)
