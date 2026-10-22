"""Shared admin and staff authorization; missing route policies fail closed."""

import logging

from fastapi import APIRouter, Depends, Request

from app.core.errors import AppError
from app.core.security import authorize_permissions, get_current_user, require_institution_roles


logger = logging.getLogger(__name__)


_ADMIN_ROUTE_PERMISSIONS: dict[tuple[str, str], tuple[str, ...]] = {
    ("GET", "/admin/me"): ("profile.own.read",),
    ("GET", "/admin/dashboard"): (
        "institution.read", "users.read", "students.read",
        "faculty.read", "staff.read", "notices.read",
    ),
    ("GET", "/admin/memberships/requests"): ("users.read",),
    ("POST", "/admin/memberships/requests/{request_id}/approve"): ("users.update",),
    ("POST", "/admin/memberships/requests/{request_id}/reject"): ("users.update",),
    ("GET", "/admin/memberships"): ("users.read",),
    ("POST", "/admin/memberships/{user_id}/deactivate"): ("users.update",),
    ("POST", "/admin/memberships/{user_id}/reactivate"): ("users.update",),
    ("POST", "/admin/memberships/invitations/{invitation_id}/resend"): ("users.update",),
    ("POST", "/admin/knowledge-sources"): ("ai.knowledge.create",),
    ("GET", "/admin/knowledge-sources"): ("ai.knowledge.read",),
    ("GET", "/admin/knowledge-sources/{knowledge_source_id}"): ("ai.knowledge.read",),
    ("PATCH", "/admin/knowledge-sources/{knowledge_source_id}"): ("ai.knowledge.update",),
    ("GET", "/admin/knowledge-sources/{knowledge_source_id}/documents"): ("documents.read",),
    ("GET", "/admin/documents/{document_id}"): ("documents.read",),
    ("POST", "/admin/documents"): ("documents.create",),
    ("POST", "/admin/documents/{document_id}/versions"): ("documents.update",),
    ("DELETE", "/admin/documents/{document_id}"): ("documents.delete",),
    ("GET", "/admin/faqs"): ("ai.knowledge.read",),
    ("POST", "/admin/faqs"): ("ai.knowledge.create",),
    ("GET", "/admin/faqs/{faq_id}"): ("ai.knowledge.read",),
    ("PATCH", "/admin/faqs/{faq_id}"): ("ai.knowledge.update",),
    ("POST", "/admin/faqs/{faq_id}/publish"): ("ai.knowledge.update",),
    ("DELETE", "/admin/faqs/{faq_id}"): ("ai.knowledge.delete",),
    ("GET", "/admin/notices"): ("notices.read",),
    ("POST", "/admin/notices"): ("notices.create",),
    ("GET", "/admin/notices/{notice_id}"): ("notices.read",),
    ("PATCH", "/admin/notices/{notice_id}"): ("notices.update",),
    ("DELETE", "/admin/notices/{notice_id}"): ("notices.delete",),
    ("GET", "/admin/students"): ("students.read",),
    ("GET", "/admin/student-workspace/sections"): ("students.read",),
    ("GET", "/admin/student-workspace/sections/{section_id}/students"): ("students.read", "attendance.read"),
    ("GET", "/admin/student-workspace/roster/{roster_id}/profile"): ("students.read", "attendance.read"),
    ("GET", "/admin/student-workspace/sections/{section_id}/history"): ("students.read", "attendance.read"),
    ("GET", "/admin/student-workspace/sections/{section_id}/registrations"): ("students.read",),
    ("POST", "/admin/student-workspace/sections/{section_id}/registrations"): ("students.create",),
    ("POST", "/admin/student-workspace/sections/{section_id}/registrations/{registration_id}/invitation"): ("students.create",),
    ("GET", "/admin/student-workspace/sections/{section_id}/batches"): ("students.read",),
    ("GET", "/admin/student-workspace/sections/{section_id}/subject-assignments"): ("students.read",),
    ("POST", "/admin/student-workspace/sections/{section_id}/subject-assignments/{registration_id}"): ("students.read", "students.create"),
    ("POST", "/admin/students"): ("students.create",),
    ("GET", "/admin/students/pending"): ("students.read",),
    ("POST", "/admin/students/{student_id}/approve"): ("students.approve",),
    ("POST", "/admin/students/{student_id}/reject"): ("students.reject",),
    ("GET", "/admin/students/{student_id}"): ("students.read",),
    ("PATCH", "/admin/students/{student_id}"): ("students.update",),
    ("DELETE", "/admin/students/{student_id}"): ("students.delete",),
    ("GET", "/admin/students/{student_id}/results"): ("results.read",),
    ("POST", "/admin/results"): ("results.manage",),
    ("GET", "/admin/results/{result_id}"): ("results.read",),
    ("PATCH", "/admin/results/{result_id}"): ("results.manage",),
    ("DELETE", "/admin/results/{result_id}"): ("results.manage",),
    ("POST", "/admin/results/csv-upload"): ("results.manage",),
    ("GET", "/admin/students/{student_id}/test-results"): ("results.read",),
    ("POST", "/admin/test-results"): ("results.manage",),
    ("PATCH", "/admin/test-results/{test_result_id}"): ("results.manage",),
    ("DELETE", "/admin/test-results/{test_result_id}"): ("results.manage",),
    ("GET", "/admin/students/{student_id}/attendance"): ("attendance.read",),
    ("POST", "/admin/attendance"): ("attendance.manage",),
    ("PATCH", "/admin/attendance/{attendance_id}"): ("attendance.manage",),
    ("DELETE", "/admin/attendance/{attendance_id}"): ("attendance.manage",),
    ("GET", "/admin/audit-logs"): ("audit.read",),
    ("GET", "/admin/audit-logs/{audit_id}"): ("audit.read",),
    ("GET", "/admin/permissions/delegable-staff"): ("permissions.read",),
    ("GET", "/admin/staff/{user_id}/permissions"): ("permissions.read",),
    ("POST", "/admin/staff/{user_id}/permissions"): ("permissions.manage",),
    ("DELETE", "/admin/staff/{user_id}/permissions"): ("permissions.manage",),
    ("GET", "/admin/faculty-assignments"): ("faculty.assignments.manage",),
    ("POST", "/admin/faculty-assignments"): ("faculty.assignments.manage",),
    ("DELETE", "/admin/faculty-assignments/{assignment_id}"): ("faculty.assignments.manage",),
    ("PATCH", "/admin/faculty-assignments/{assignment_id}"): ("faculty.assignments.manage",),
    ("GET", "/admin/faculty-responsibilities"): ("faculty.assignments.manage",),
    ("POST", "/admin/faculty-responsibilities"): ("faculty.assignments.manage",),
    ("PATCH", "/admin/faculty-responsibilities/{responsibility_id}"): ("faculty.assignments.manage",),
    ("DELETE", "/admin/faculty-responsibilities/{responsibility_id}"): ("faculty.assignments.manage",),
}


async def _authorize_admin_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> None:
    route = request.scope.get("route")
    route_path = getattr(route, "path", "")
    admin_path_index = route_path.rfind("/admin")
    normalized_path = route_path[admin_path_index:] if admin_path_index >= 0 else ""
    permissions = _ADMIN_ROUTE_PERMISSIONS.get((request.method, normalized_path))
    if permissions is None:
        logger.error(
            "event=authorization_policy_missing method=%s path=%s",
            request.method,
            normalized_path or "unknown",
        )
        raise AppError(
            "You do not have permission to perform this action",
            status_code=403,
            code="FORBIDDEN",
        )
    authorize_permissions(current_user, *permissions)


_ADMIN = require_institution_roles("admin")


_APPROVAL = require_institution_roles("admin", "staff")


def create_feature_router() -> APIRouter:
    """Keep the admin prefix on leaf route templates used by permission checks."""
    return APIRouter(prefix="/admin")
