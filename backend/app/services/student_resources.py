"""Phase 6.16 — Student learning-resource service.

Reusable, tenant-scoped, read-only student view of the institution's PUBLISHED
learning resources (study material, lecture notes, academic documents — the
institution's own knowledge sources). It introduces NO new resource model: it
projects existing ``knowledge_sources`` rows that an administrator already
moved to ``lifecycle_status = 'published'``.

Security model (identical to ``app.services.student_notices``):

    Authenticated JWT -> current_user -> student_context.get_student_context
        -> assert_student_context_tenant
        -> student_dashboard.list_published_resources(student's OWN institution)

The caller never supplies identity, so another institution's resources are
structurally unreachable.

Data minimization: only title / description / source type / effective dates are
projected. Storage details (``storage_bucket``, ``storage_object_key``,
``file_checksum``), document and version identifiers, and every internal
database identifier are excluded by the repository projection AND by the
``extra="forbid"`` response schema. No download URL is generated.

Read-only by construction: this module exposes a single list function. Students
cannot create, publish, modify, or delete knowledge sources.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import student_dashboard as dashboard_repo
from app.schemas.student_resources import StudentResource, StudentResourceList
from app.services import student_context as student_context_service

# Dashboard shows a compact recent set; the Learning Resources page asks for
# more of the same published corpus.
DEFAULT_RESOURCE_LIMIT = 6
MAX_RESOURCE_LIMIT = 50


def get_own_resources(
    current_user: dict[str, Any],
    limit: int = DEFAULT_RESOURCE_LIMIT,
    client: Any | None = None,
) -> StudentResourceList:
    """Return the authenticated student's institution's published resources.

    Args:
        current_user: the dict returned by ``get_current_user()`` — the ONLY
            identity source.
        limit: maximum number of resources to return (1..MAX_RESOURCE_LIMIT).
        client: optional already-created Supabase client (tests inject a mock;
            production uses the service-role admin client).

    Returns:
        ``StudentResourceList`` — student-safe resources, newest first. An
        institution with no published resources yields an EMPTY list, never an
        error.

    Raises:
        AppError 400 INVALID_USER_CONTEXT: no ``user_id`` in the auth context.
        AppError 404 STUDENT_PROFILE_NOT_FOUND: no students row for the user.
        AppError 403 STUDENT_NOT_APPROVED / STUDENT_INACTIVE: not eligible.
        AppError 403 TENANT_MISMATCH: resolved tenant differs from the
            authenticated tenant (or is unresolvable — fail closed).
        AppError 422 INVALID_FILTER: ``limit`` out of range.
    """
    bounded_limit = _validate_limit(limit)
    db = client or get_admin_client()

    student_ctx = student_context_service.get_student_context(current_user)
    student_context_service.assert_student_context_tenant(current_user, student_ctx)

    institution_id = student_ctx.get("institution_id")
    if institution_id is None:
        raise AppError(
            "No institution is linked to this account",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    rows = dashboard_repo.list_published_resources(
        db, institution_id, limit=bounded_limit
    )
    items = [_to_resource(row) for row in (rows or [])]
    return StudentResourceList(items=items, total=len(items))


def get_own_resources_dict(
    current_user: dict[str, Any],
    limit: int = DEFAULT_RESOURCE_LIMIT,
    client: Any | None = None,
) -> dict[str, Any]:
    """Dict form of :func:`get_own_resources` for the API layer."""
    return get_own_resources(current_user, limit=limit, client=client).model_dump()


def _to_resource(row: dict[str, Any]) -> StudentResource:
    """Project one stored knowledge-source row to the student-safe contract."""
    description = row.get("description")
    effective_from = row.get("effective_from")
    effective_until = row.get("effective_until")
    return StudentResource(
        resource_id=row["knowledge_source_id"],
        title=str(row.get("title") or "").strip(),
        description=(
            str(description).strip() if description is not None and str(description).strip() else None
        ),
        source_type=str(row.get("source_type") or "").strip(),
        effective_from=_as_text(effective_from),
        effective_until=_as_text(effective_until),
    )


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_limit(limit: int) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise AppError(
            "Invalid limit filter",
            status_code=422,
            code="INVALID_FILTER",
        )
    if limit < 1 or limit > MAX_RESOURCE_LIMIT:
        raise AppError(
            "Invalid limit filter",
            status_code=422,
            code="INVALID_FILTER",
        )
    return limit
