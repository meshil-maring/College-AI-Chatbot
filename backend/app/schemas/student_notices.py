"""Phase 6.16 — Student-facing notice contracts.

Student-safe projection over the EXISTING ``notices`` table (Phase Admin-1;
``is_published`` added by the Phase Admin-2 amendment). No new table, no new
column, no new vocabulary: only rows the institution has already published are
projected.

Scope rules (enforced server-side in ``app.services.student_notices``):

* the institution filter is ALWAYS the authenticated student's own institution
  (resolved from the JWT chain); the service exposes no identity parameter, so
  a client-supplied value can never widen the scope;
* only ``is_active = true``, ``is_published = true`` rows are projected;
* expired rows (``expires_at`` in the past) are never projected.

Excluded by design: ``institution_id`` (internal tenant identifier),
``created_by`` (internal user identifier), ``is_active``/``is_published``
(admin workflow detail) and ``updated_at`` (admin audit detail).
``notice_id`` is retained as the stable list key — the same choice the locked
Phase 6.11 student notification contract makes with ``notification_id`` — and
is never rendered by the UI (see the Phase 6.16 frontend tests).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentNotice(BaseModel):
    """One published notice for the authenticated student's institution."""

    notice_id: UUID
    title: str
    content: str
    category: str
    priority: str
    is_pinned: bool = False
    published_at: datetime | None = None
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class StudentNoticeList(BaseModel):
    """The authenticated student's institution notices (pinned first, newest)."""

    items: list[StudentNotice] = Field(default_factory=list)
    total: int = 0

    model_config = ConfigDict(extra="forbid")
