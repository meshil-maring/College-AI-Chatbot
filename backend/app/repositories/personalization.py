"""Phase 6.10 — Read helpers for personalization labels.

Resolves human-readable labels (program name/code, academic year name/code,
current semester, course code/name) for identifiers that ALREADY belong to the
authenticated student's authorized records.

These are label lookups only. Every identifier passed in is derived server-side
from the student's own authorized rows (profile, test results, result items),
so there is no tenant filtering inside these helpers: the tenant boundary was
already enforced at the access layer that produced the identifiers. The labels
themselves are benign reference data (a course code is not student data), but
they are only ever resolved for the authenticated student's own records.

All functions follow the project repository convention: the first argument is
an already-created Supabase ``Client`` (service-role client in production).
"""

from __future__ import annotations

from typing import Any

from supabase import Client

# Projection used everywhere here: no internal tenant/audit metadata.
_LABEL_COLUMNS = "code, name"


def get_program_label(client: Client, program_id: Any, institution_id: Any = None) -> dict | None:
    """Return ``{program_id, code, name}`` for one program, or None.

    ``programs`` carries no ``institution_id`` column (its tenant is reached via
    ``programs.department_id -> departments.institution_id``), so when
    ``institution_id`` is supplied the lookup is performed through the embedded
    department chain as defense-in-depth against a stale program reference.
    """
    if program_id is None:
        return None
    if institution_id is None:
        response = (
            client.table("programs")
            .select(f"program_id, {_LABEL_COLUMNS}")
            .eq("program_id", str(program_id))
            .maybe_single()
            .execute()
        )
        return response.data
    response = (
        client.table("programs")
        .select(f"program_id, {_LABEL_COLUMNS}, departments(institution_id)")
        .eq("program_id", str(program_id))
        .maybe_single()
        .execute()
    )
    row = response.data
    if row is None:
        return None
    department = row.get("departments")
    if isinstance(department, list):
        department = department[0] if department else {}
    if not isinstance(department, dict):
        return None
    if str(department.get("institution_id")) != str(institution_id):
        return None
    return {
        "program_id": row.get("program_id"),
        "code": row.get("code"),
        "name": row.get("name"),
    }


def get_academic_year_label(
    client: Client, academic_year_id: Any, institution_id: Any = None
) -> dict | None:
    """Return ``{academic_year_id, code, name}`` for one academic year, or None."""
    if academic_year_id is None:
        return None
    query = (
        client.table("academic_years")
        .select(f"academic_year_id, {_LABEL_COLUMNS}")
        .eq("academic_year_id", str(academic_year_id))
    )
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    response = query.maybe_single().execute()
    return response.data


def get_current_semester_label(
    client: Client, academic_year_id: Any
) -> dict | None:
    """Return ``{semester_id, code, name}`` for the ``is_current`` semester of
    one academic year, or None when no current semester is flagged."""
    if academic_year_id is None:
        return None
    response = (
        client.table("semesters")
        .select(f"semester_id, {_LABEL_COLUMNS}")
        .eq("academic_year_id", str(academic_year_id))
        .eq("is_current", True)
        .maybe_single()
        .execute()
    )
    return response.data


def get_course_labels(client: Client, course_ids: list) -> dict[str, dict]:
    """Return ``{course_id: {course_id, code, name}}`` for the given course ids.

    Unknown ids are simply absent from the mapping; the student's record data
    produced the ids, so they are expected to resolve.
    """
    if not course_ids:
        return {}
    response = (
        client.table("courses")
        .select(f"course_id, {_LABEL_COLUMNS}")
        .in_("course_id", [str(course_id) for course_id in course_ids])
        .execute()
    )
    return {str(row["course_id"]): row for row in (response.data or [])}