"""Shared Phase 7.21 dashboard contract helpers for backend tests.

Not a test module (no ``test_`` prefix, no ``test_`` functions) — it only
builds valid ``DashboardResponse`` instances so patched reads and contract
tests cannot drift from the real schema.
"""

from __future__ import annotations

from app.schemas.admin_dashboard import (
    DashboardAcademics,
    DashboardCommunication,
    DashboardInstitution,
    DashboardKnowledge,
    DashboardQuickAction,
    DashboardRecentNotice,
    DashboardResponse,
    DashboardStudents,
)


def build_dashboard(
    *,
    name: str = "Test Institution",
    code: str = "TESTINST",
    status: str = "active",
    total_students: int = 0,
    pending_approvals: int = 0,
    approved: int = 0,
    active_students: int = 0,
    sources_total: int = 0,
    sources_active: int = 0,
    documents_total: int = 0,
    failed_processing_runs: int | None = None,
    active_faqs: int = 0,
    active_notices: int = 0,
    recent_notices: list[DashboardRecentNotice] | None = None,
    attendance_records: int = 0,
    test_results: int = 0,
    results: int = 0,
    quick_actions: list[DashboardQuickAction] | None = None,
) -> DashboardResponse:
    """Build a fully-specified ``DashboardResponse`` with sensible defaults."""
    return DashboardResponse(
        institution=DashboardInstitution(name=name, code=code, status=status),
        students=DashboardStudents(
            total=total_students,
            pending_approvals=pending_approvals,
            approved=approved,
            active=active_students,
        ),
        knowledge=DashboardKnowledge(
            sources_total=sources_total,
            sources_active=sources_active,
            documents_total=documents_total,
            failed_processing_runs=failed_processing_runs,
        ),
        communication=DashboardCommunication(
            active_faqs=active_faqs,
            active_notices=active_notices,
            recent_notices=list(recent_notices or []),
        ),
        academics=DashboardAcademics(
            attendance_records=attendance_records,
            test_results=test_results,
            results=results,
        ),
        quick_actions=list(quick_actions or []),
    )
