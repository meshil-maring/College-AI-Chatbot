"""Phase 6.16 — Student notice service.

Reusable, tenant-scoped, read-only student view of the institution's published
notices. This is the student-side counterpart of the existing admin notice
listing; it introduces NO notice table, column, status, priority or category —
it only projects rows an administrator already published.

Security model (reuses locked Phase 6 primitives; nothing weakened):

    Authenticated JWT
        -> current_user (``get_current_user``: users.user_id + server-resolved
           institution_id tenant)
        -> ``student_context.get_student_context`` (students row resolved
           server-side from users.user_id; eligibility: approved + active +
           institution active)
        -> ``assert_student_context_tenant`` (defence-in-depth: the resolved
           student tenant must match the authenticated user's tenant)
        -> ``student_dashboard.list_published_notices`` with the student's OWN
           institution id as a mandatory equality filter

The caller never supplies identity: the service accepts the ``current_user``
dict only. There is NO ``student_id`` / ``user_id`` / ``institution_id``
parameter, so a client-supplied value can never widen the institution scope and
another institution's notices are structurally unreachable.

Read-only by construction: this module exposes a single list function. There is
no create/update/delete/publish path for students anywhere in the codebase.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import student_dashboard as dashboard_repo
from app.schemas.student_notices import StudentNotice, StudentNoticeList
from app.services import student_context as student_context_service

# Dashboard shows a small, recent set; the full list is requested from the
# Notices page. Both stay well below the admin listing's own limit.
DEFAULT_NOTICE_LIMIT = 5
MAX_NOTICE_LIMIT = 20


def get_own_notices(
    current_user: dict[str, Any],
    limit: int = DEFAULT_NOTICE_LIMIT,
    client: Any | None = None,
) -> StudentNoticeList:
    """Return the authenticated student's institution's published notices.

    Args:
        current_user: the dict returned by ``get_current_user()`` — the ONLY
            identity source (JWT ``sub`` -> users row -> students row).
        limit: maximum number of notices to return (1..MAX_NOTICE_LIMIT).
        client: optional already-created Supabase client (tests inject a mock;
            production uses the service-role admin client).

    Returns:
        ``StudentNoticeList`` — student-safe notices, pinned first then newest.
        An institution with no published notices yields an EMPTY list, never an
        error (absence of data is not a failure).

    Raises:
        AppError 400 INVALID_USER_CONTEXT: no ``user_id`` in the auth context.
        AppError 404 STUDENT_PROFILE_NOT_FOUND: no students row for the user.
        AppError 403 STUDENT_NOT_APPROVED / STUDENT_INACTIVE: not eligible.
        AppError 403 TENANT_MISMATCH: resolved tenant differs from the
            authenticated tenant.
        AppError 422 INVALID_FILTER: ``limit`` out of range.
    """
    bounded_limit = _validate_limit(limit)
    db = client or get_admin_client()

    # Canonical student context (Phase 6.9): server-side identity + eligibility.
    student_ctx = student_context_service.get_student_context(current_user)
    student_context_service.assert_student_context_tenant(current_user, student_ctx)

    institution_id = student_ctx.get("institution_id")
    if institution_id is None:
        # Fail closed: a student without a resolvable tenant must never receive
        # a cross-institution listing.
        raise AppError(
            "No institution is linked to this account",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    rows = dashboard_repo.list_published_notices(
        db, institution_id, limit=bounded_limit
    )
    items = [_to_notice(row) for row in (rows or [])]
    return StudentNoticeList(items=items, total=len(items))


def get_own_notices_dict(
    current_user: dict[str, Any],
    limit: int = DEFAULT_NOTICE_LIMIT,
    client: Any | None = None,
) -> dict[str, Any]:
    """Dict form of :func:`get_own_notices` for the API layer."""
    return get_own_notices(current_user, limit=limit, client=client).model_dump()


def _to_notice(row: dict[str, Any]) -> StudentNotice:
    """Project one stored notice row to the student-safe contract."""
    return StudentNotice(
        notice_id=row["notice_id"],
        title=str(row.get("title") or "").strip(),
        content=str(row.get("content") or "").strip(),
        category=str(row.get("category") or "general").strip(),
        priority=str(row.get("priority") or "normal").strip(),
        is_pinned=bool(row.get("is_pinned")),
        published_at=row.get("published_at"),
        expires_at=row.get("expires_at"),
    )


def _validate_limit(limit: int) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise AppError(
            "Invalid limit filter",
            status_code=422,
            code="INVALID_FILTER",
        )
    if limit < 1 or limit > MAX_NOTICE_LIMIT:
        raise AppError(
            "Invalid limit filter",
            status_code=422,
            code="INVALID_FILTER",
        )
    return limit
