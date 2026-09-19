"""Phase 6.14.1 — Student academic profile service.

Reusable, secure backend representation of the authenticated student's
academic profile.

Security model (reuses locked Phase 6 primitives; nothing weakened):

    Authenticated JWT
        -> current_user (``get_current_user``: users.user_id +
           server-resolved institution_id tenant)
        -> students row via ``users.user_id`` (server-side only)
        -> ``assert_tenant_object`` (tenant-bound users may only see their
           own institution's row; cross-tenant rows fail closed with 403
           TENANT_MISMATCH)
        -> student-facing projection (whitelisted fields only, no internal
           database identifiers)

The caller never supplies identity: the service accepts the
``current_user`` dict only. There is NO ``student_id`` / ``user_id`` /
``institution_id`` / email / register-number / roll-number parameter, so
client-supplied academic identifiers cannot override the authenticated
identity and cross-student access is structurally impossible.

Eligibility note: unlike the Phase 6.9 data-access layer (which gates
attendance/results behind approved + active), the profile endpoint exposes
the ``approval_status`` field itself, so it must remain readable while
pending (otherwise a student could never see that they are pending). The
tenant boundary and server-side identity resolution still apply unchanged.

Label enrichment reuses the locked ``personalization`` repository label
helpers (program / academic-year / current-semester) plus the ``tenancy``
institution lookup — no new data-access architecture.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.security import assert_tenant_object
from app.db.supabase import get_admin_client
from app.repositories import admin_academics as academics_repo
from app.repositories import personalization as personalization_repo
from app.repositories import tenancy as tenancy_repo
from app.schemas.student_profile import StudentAcademicProfile


def get_academic_profile(
    current_user: dict[str, Any],
    client: Any | None = None,
) -> StudentAcademicProfile:
    """Return the authenticated student's academic profile.

    Args:
        current_user: the dict returned by ``get_current_user()`` (JWT
            ``sub`` -> users row -> server-resolved tenant). The ``user_id``
            key drives the students lookup; no other identity input exists.
        client: optional already-created Supabase client (tests inject a
            mock; production uses the service-role admin client).

    Raises:
        AppError 400 INVALID_USER_CONTEXT: authenticated context has no user_id.
        AppError 404 STUDENT_PROFILE_NOT_FOUND: no students row for the user.
        AppError 403 TENANT_MISMATCH: row belongs to another institution.
    """
    user_id = (current_user or {}).get("user_id")
    if not user_id:
        raise AppError(
            "Invalid authenticated user context",
            status_code=400,
            code="INVALID_USER_CONTEXT",
        )

    db = client or get_admin_client()
    row = academics_repo.get_student_academic_profile_row(db, str(user_id))
    if row is None:
        raise AppError(
            "No student profile is linked to this account",
            status_code=404,
            code="STUDENT_PROFILE_NOT_FOUND",
        )

    # Tenant boundary (existing Phase 6.6 primitive): the row's institution
    # must match the authenticated user's server-resolved tenant.
    assert_tenant_object(current_user, row.get("institution_id"))

    institution_id = row.get("institution_id")
    program_label = personalization_repo.get_program_label(
        db, row.get("program_id"), institution_id
    )
    academic_year_label = personalization_repo.get_academic_year_label(
        db, row.get("academic_year_id"), institution_id
    )
    semester_label = personalization_repo.get_current_semester_label(
        db, row.get("academic_year_id")
    )
    institution = (
        tenancy_repo.get_institution_by_id(db, institution_id)
        if institution_id is not None
        else None
    )
    # Defense-in-depth: a stale row pointing at another tenant's institution
    # (or a deleted institution) must never leak that tenant's name/code.
    if institution is not None and institution_id is not None:
        if str(institution.get("institution_id")) != str(institution_id):
            institution = None

    return StudentAcademicProfile(
        student_number=_as_str(row.get("student_number")),
        register_number=_as_str(row.get("register_number")),
        university_roll_number=_as_str(row.get("university_roll_number")),
        email=_as_str(row.get("email")),
        institution_name=_as_str((institution or {}).get("name")),
        institution_code=_as_str((institution or {}).get("code")),
        program_name=_as_str((program_label or {}).get("name")),
        program_code=_as_str((program_label or {}).get("code")),
        academic_year_name=_as_str((academic_year_label or {}).get("name")),
        academic_year_code=_as_str((academic_year_label or {}).get("code")),
        current_semester_name=_as_str((semester_label or {}).get("name")),
        current_semester_code=_as_str((semester_label or {}).get("code")),
        approval_status=_as_str(row.get("approval_status")),
        status=_as_str(row.get("status")),
    )


def get_academic_profile_dict(
    current_user: dict[str, Any],
    client: Any | None = None,
) -> dict[str, Any]:
    """Dict form of :func:`get_academic_profile` for the API layer."""
    return get_academic_profile(current_user, client=client).model_dump()


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        text = str(value)
    else:
        text = str(value).strip()
    return text or None
