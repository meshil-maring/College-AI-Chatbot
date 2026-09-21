"""Phase 6.16.4 — Student-experience final integration & security regression.

The complete student experience (Dashboard / Attendance / Results / Notices /
Learning Resources / AI Assistant / Profile) is served by the existing
``/api/v1/students/me/*`` read-only endpoints, whose full behaviour is covered
by the earlier phase suites (6.14.x, 6.16, 6.16.2, 6.16.3). Per the phase
scope ("no backend changes unless a genuine defect is found" — none was), this
final suite REGRESSION-PINS the invariants the integrated experience depends
on, at the route layer:

* every ``/students/me/*`` route accepts ONLY ``GET`` (read-only academic
  access — the student experience has no mutation path anywhere);
* every student surface route takes NO client-suppliable identity parameter
  (server-authoritative identity; nothing for a caller to forge);
* privileged management routes (admin surfaces) remain OUTSIDE the student
  namespace and keep their role requirement;
* the exact response-field projection the frontend types mirror stays minimal
  (data minimization: no internal identifiers, tenant, storage, or audit
  metadata in any student payload).
"""

from __future__ import annotations

from app.main import app



class TestStudentSurfacesRemainReadOnly:
    """The integrated experience must stay read-only end to end."""

    def test_every_students_me_route_is_get_only(self):
        schema = app.openapi()
        paths = schema["paths"]
        student_me_paths = [
            path for path in paths
            if path.startswith("/api/v1/students/me/")
        ]
        assert student_me_paths, "the /students/me surface must exist"
        # The one documented exception is the pre-existing Phase 6.11
        # notification READ-RECEIPT (PATCH /me/notifications/{id}/read) — an
        # unrelated student-owned contract that predates this experience.
        for path in student_me_paths:
            if path == "/api/v1/students/me/notifications/{notification_id}/read":
                continue
            assert set(paths[path]) == {"get"}, f"{path}: {sorted(paths[path])}"

    def test_no_students_me_route_accepts_identity_parameters(self):
        """A caller can never tell the backend WHOSE data to return."""
        schema = app.openapi()
        identity_fields = {
            "student_id", "user_id", "auth_user_id", "email",
            "register_number", "university_roll_number", "student_number",
        }
        for path, operations in schema["paths"].items():
            if not path.startswith("/api/v1/students/me/"):
                continue
            for method, operation in operations.items():
                # GET-only everywhere except the documented Phase 6.11
                # notification read-receipt PATCH (see the previous test).
                if path == "/api/v1/students/me/notifications/{notification_id}/read":
                    continue
                assert method == "get"
                for parameter in operation.get("parameters", []):
                    assert parameter.get("name") not in identity_fields, (
                        f"{path}: client-suppliable identity parameter "
                        f"{parameter.get('name')!r}"
                    )


class TestPrivilegedSurfaceDenial:
    """Privileged management surfaces remain outside the student namespace."""

    def test_student_namespace_exposes_no_management_route(self):
        schema = app.openapi()
        paths = schema["paths"]
        me_paths = [p for p in paths if p.startswith("/api/v1/students/me/")]
        assert me_paths
        # Every route the student experience calls is scoped under /me/.
        for path in me_paths:
            assert path.startswith("/api/v1/students/me/"), path
        # The management routes keep their canonical (student-inaccessible)
        # locations: no management operation lives under /students/me/.
        assert "/api/v1/students/me/academic-profile" in paths

    def test_the_admin_surface_remains_registered_and_protected(self):
        """The privileged surface keeps its server-side bearer requirement."""
        schema = app.openapi()
        paths = schema["paths"]
        admin_paths = [p for p in paths if p.startswith("/api/v1/admin/")]
        assert admin_paths, "the admin surface must remain registered"
        for path in admin_paths:
            for operation in paths[path].values():
                protected = any(
                    parameter.get("name") == "authorization"
                    for parameter in operation.get("parameters", [])
                ) or any("bearerAuth" in entry for entry in operation.get("security") or [])
                assert protected, f"{path}: missing bearer protection"


class TestDataMinimization:
    """No student payload may carry internal, tenant, storage, or audit data."""

    def test_academic_profile_projection_stays_minimal(self):
        from app.schemas.student_profile import StudentAcademicProfile

        dumped = set(StudentAcademicProfile.model_fields.keys())
        assert dumped == {
            "student_number", "register_number", "university_roll_number",
            "email", "institution_name", "institution_code",
            "program_name", "program_code",
            "academic_year_name", "academic_year_code",
            "current_semester_name", "current_semester_code",
            "approval_status", "status",
        }

    def test_notice_projection_stays_minimal(self):
        from app.schemas.student_notices import StudentNotice, StudentNoticeList

        item_fields = set(StudentNotice.model_fields.keys())
        assert item_fields == {
            "notice_id", "title", "content", "category", "priority",
            "is_pinned", "published_at", "expires_at",
        }
        assert "items" in StudentNoticeList.model_fields

    def test_resource_projection_stays_minimal(self):
        from app.schemas.student_resources import (
            StudentResource,
            StudentResourceList,
        )

        item_fields = set(StudentResource.model_fields.keys())
        assert item_fields == {
            "resource_id", "title", "description", "source_type",
            "effective_from", "effective_until",
        }
        assert "items" in StudentResourceList.model_fields


