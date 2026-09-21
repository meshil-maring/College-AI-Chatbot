"""Phase 6.16 — Read-only repository queries behind the student experience.

The student dashboard needs TWO read projections that had no student-scoped
data-access path before this phase:

* the institution's published notices (previously only reachable through
  ``/admin/notices``, which requires ``require_roles("admin")``);
* the institution's published knowledge sources ("learning resources").

Both queries are additive and read-only. No existing repository function,
table, column, contract, or authorization rule is modified.

Every function takes an already-created Supabase ``Client`` as its first
argument (service-role client in production), following the existing
repository convention in ``app.repositories``.

Tenant isolation: ``institution_id`` is a MANDATORY argument on both functions
and is always applied as an equality filter, so a query can never span
institutions. The caller (``app.services.student_notices`` /
``app.services.student_resources``) obtains it exclusively from the
authenticated student's server-resolved context.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from supabase import Client

# Projections: ONLY columns that are safe to hand to a student-facing
# projection. `institution_id`, `created_by`, `is_active`, `is_published`,
# `updated_at`, `storage_bucket`, `storage_object_key`, `file_checksum` and
# every document/pipeline identifier are deliberately NOT selected.
NOTICE_COLUMNS = (
    "notice_id, title, content, category, priority, is_pinned, "
    "published_at, expires_at"
)

RESOURCE_COLUMNS = (
    "knowledge_source_id, source_type, title, description, "
    "lifecycle_status, effective_from, effective_until"
)

# Publication boundary for learning resources. Mirrors the published-only
# boundary already used for institution knowledge by the locked Phase 6.13.8
# public-knowledge check; no new lifecycle value is introduced.
PUBLISHED_RESOURCE_LIFECYCLE_STATUS = "published"

# Source types that already have a dedicated student surface and must not be
# repeated in the learning-resource list: `notice` (Notices section) and
# `faq` (answered by the AI assistant). These names are exactly the
# corresponding members of the locked `app.services.public_chat.
# PUBLIC_SOURCE_TYPES` vocabulary; `tests/test_student_experience_dashboard_
# phase_6_16.py` asserts that the two definitions cannot drift apart.
EXCLUDED_RESOURCE_SOURCE_TYPES: tuple[str, ...] = ("notice", "faq")


def _utc_now_iso() -> str:
    """Current UTC timestamp in the ISO-8601 form PostgREST compares against."""
    return datetime.now(timezone.utc).isoformat()


def list_published_notices(
    client: Client,
    institution_id: UUID | str,
    limit: int = 5,
    now: str | None = None,
) -> list[dict]:
    """List the institution's published, active, unexpired notices.

    Ordering matches the existing admin listing (pinned first, then newest
    publication first) so the dashboard shows the same priority order an
    administrator sees.

    Args:
        client: Already-created Supabase client.
        institution_id: The authenticated student's own institution. Required.
        limit: Maximum rows (the caller validates the bound).
        now: Injectable UTC timestamp for the expiry boundary; defaults to the
            current UTC time. The expiry filter is ALWAYS applied.

    Returns:
        Raw ``notices`` rows (already restricted to the safe column list).
    """
    timestamp = now or _utc_now_iso()
    query = (
        client.table("notices")
        .select(NOTICE_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("is_active", True)
        .eq("is_published", True)
        .or_(f"expires_at.is.null,expires_at.gte.{timestamp}")
    )
    response = (
        query.order("is_pinned", desc=True)
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def list_published_resources(
    client: Client,
    institution_id: UUID | str,
    limit: int = 6,
) -> list[dict]:
    """List the institution's published learning resources.

    Only ``lifecycle_status = 'published'`` knowledge sources are returned; the
    source types that have their own student surface are excluded (see
    ``EXCLUDED_RESOURCE_SOURCE_TYPES``).

    Args:
        client: Already-created Supabase client.
        institution_id: The authenticated student's own institution. Required.
        limit: Maximum rows (the caller validates the bound).

    Returns:
        Raw ``knowledge_sources`` rows (already restricted to safe columns).
    """
    query = (
        client.table("knowledge_sources")
        .select(RESOURCE_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("lifecycle_status", PUBLISHED_RESOURCE_LIFECYCLE_STATUS)
    )
    for source_type in EXCLUDED_RESOURCE_SOURCE_TYPES:
        query = query.neq("source_type", source_type)
    response = query.order("created_at", desc=True).limit(limit).execute()
    return response.data or []
