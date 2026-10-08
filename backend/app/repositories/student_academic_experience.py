"""Student Academic Experience — read-only repository projections.

This module is a READ LAYER over EXISTING authoritative academic tables. It
introduces no table, column, status or workflow of its own. Every query is a
narrow projection of rows that already exist:

* ``faculty_attendance_rosters`` / ``faculty_attendance_sessions`` /
  ``faculty_attendance_records`` — the Faculty Attendance system, reached via
  the student's own ``linked_student_id`` roster link;
* ``student_attendance`` — legacy/admin attendance rows, reused for the same
  roster dedup the Faculty Attendance reporting service already performs;
* ``sections`` / ``course_offerings`` / ``courses`` — subject labels only;
* ``faculty_tests`` / ``test_types`` — assessment metadata for the student's
  own sections (visibility filtering happens in the service layer).

Tenant isolation: ``institution_id`` is a MANDATORY argument on every
tenant-scoped function and is always applied as an equality filter, so a
query can never span institutions. The caller obtains it exclusively from the
authenticated student's server-resolved context.

Identity scoping: roster access is keyed by ``linked_student_id`` (the
student's own server-resolved ``students.student_id``); attendance records
are reachable only through that student's own roster ids.

Every function takes an already-created Supabase ``Client`` first (service
role in production), following the ``app.repositories`` convention. Reads go
through ``app.repositories.query_pages`` so a page cap can never silently
truncate a projection.
"""

from __future__ import annotations

from uuid import UUID

from supabase import Client

from app.repositories.query_pages import read_all

# Projections: only the columns the student-facing service needs. Internal
# workflow fields (``reconciliation_state``, ``source_metadata``,
# ``conducted_by``, ``created_by``, ``description``, ``marks_state``,
# ``version`` ...) are deliberately NOT selected.
ROSTER_COLUMNS = (
    "roster_id, institution_id, section_id, course_offering_id, semester_id, "
    "register_number, roster_status, linked_student_id"
)
SECTION_COLUMNS = "section_id, course_offering_id, code, name, is_active"
OFFERING_COLUMNS = "course_offering_id, course_id, academic_year_id, semester_id"
COURSE_COLUMNS = "course_id, code, name"
SESSION_COLUMNS = (
    "session_id, institution_id, section_id, course_offering_id, session_date"
)
RECORD_COLUMNS = "record_id, session_id, roster_id, status"
LEGACY_ATTENDANCE_COLUMNS = (
    "student_attendance_id, institution_id, section_id, student_id, date, status"
)
TEST_COLUMNS = (
    "test_id, institution_id, section_id, title, test_type, max_marks, "
    "scheduled_date, start_time, end_time, duration_minutes, status"
)
TEST_TYPE_COLUMNS = "code, name"

# Bounded batch size for ``in_`` filters (keeps generated URLs small).
BATCH_SIZE = 100

# Upper bounds: a single student's academic footprint is small by construction
# (one roster per section they belong to). These caps keep a pathological row
# from turning one dashboard request into an unbounded scan.
MAX_ROSTERS = 200
MAX_SESSIONS_PER_SECTION = 400
MAX_LEGACY_ROWS = 500
MAX_TESTS = 100


def list_linked_rosters(
    client: Client,
    student_id: UUID | str,
    institution_id: UUID | str,
) -> list[dict]:
    """List the student's OWN rosters inside their OWN institution.

    ``linked_student_id`` is the existing identity link maintained by the
    Faculty Attendance reconciliation (only approved, identity-matched
    students receive it), and ``institution_id`` is the mandatory tenant
    equality filter. Both are always applied.
    """
    query = (
        client.table("faculty_attendance_rosters")
        .select(ROSTER_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("linked_student_id", str(student_id))
        .order("roster_id")
        .limit(MAX_ROSTERS)
    )
    return read_all(query)


def _in_batches(values: list[UUID | str]) -> list[list[str]]:
    return [
        [str(value) for value in values[start : start + BATCH_SIZE]]
        for start in range(0, len(values), BATCH_SIZE)
    ]


def list_sections(
    client: Client,
    section_ids: list[UUID | str],
) -> list[dict]:
    """Label projection for a bounded set of section ids."""
    rows: list[dict] = []
    for batch in _in_batches(section_ids):
        rows.extend(
            read_all(
                client.table("sections")
                .select(SECTION_COLUMNS)
                .in_("section_id", batch)
                .order("section_id")
            )
        )
    return rows


def list_course_offerings(
    client: Client,
    offering_ids: list[UUID | str],
) -> list[dict]:
    """Label projection for a bounded set of course-offering ids."""
    rows: list[dict] = []
    for batch in _in_batches(offering_ids):
        rows.extend(
            read_all(
                client.table("course_offerings")
                .select(OFFERING_COLUMNS)
                .in_("course_offering_id", batch)
                .order("course_offering_id")
            )
        )
    return rows


def list_courses(client: Client, course_ids: list[UUID | str]) -> list[dict]:
    """Label projection for a bounded set of course ids."""
    rows: list[dict] = []
    for batch in _in_batches(course_ids):
        rows.extend(
            read_all(
                client.table("courses")
                .select(COURSE_COLUMNS)
                .in_("course_id", batch)
                .order("course_id")
            )
        )
    return rows


def list_section_sessions(
    client: Client,
    institution_id: UUID | str,
    section_ids: list[UUID | str],
) -> list[dict]:
    """Recorded attendance sessions for the student's OWN sections."""
    rows: list[dict] = []
    for batch in _in_batches(section_ids):
        rows.extend(
            read_all(
                client.table("faculty_attendance_sessions")
                .select(SESSION_COLUMNS)
                .eq("institution_id", str(institution_id))
                .in_("section_id", batch)
                .order("session_date")
                .limit(MAX_SESSIONS_PER_SECTION * max(len(batch), 1))
            )
        )
    return rows


def list_records_for_rosters(
    client: Client,
    roster_ids: list[UUID | str],
) -> list[dict]:
    """Attendance records reachable ONLY through the student's own roster ids."""
    rows: list[dict] = []
    for batch in _in_batches(roster_ids):
        rows.extend(
            read_all(
                client.table("faculty_attendance_records")
                .select(RECORD_COLUMNS)
                .in_("roster_id", batch)
                .order("record_id")
            )
        )
    return rows


def list_legacy_attendance(
    client: Client,
    institution_id: UUID | str,
    student_id: UUID | str,
    section_ids: list[UUID | str],
) -> list[dict]:
    """The student's OWN legacy ``student_attendance`` rows for their sections.

    The Faculty Attendance reporting service already merges these mirrored
    rows (deduplicated by roster + date) into the authoritative per-student
    figures; the student-facing aggregation performs the SAME merge so both
    surfaces report identical numbers.
    """
    rows: list[dict] = []
    for batch in _in_batches(section_ids):
        rows.extend(
            read_all(
                client.table("student_attendance")
                .select(LEGACY_ATTENDANCE_COLUMNS)
                .eq("institution_id", str(institution_id))
                .eq("student_id", str(student_id))
                .in_("section_id", batch)
                .order("date")
                .limit(MAX_LEGACY_ROWS)
            )
        )
    return rows


def list_faculty_tests(
    client: Client,
    institution_id: UUID | str,
    section_ids: list[UUID | str],
    statuses: tuple[str, ...],
    limit: int = 20,
) -> list[dict]:
    """Assessment metadata for the student's OWN sections.

    The caller passes the EXACT status vocabulary that is student-visible
    (never ``DRAFT`` / ``CANCELLED``); ordering is server-authoritative
    (earliest scheduled first). The projection never selects the assessment
    description, marks state, version or actor columns.
    """
    if not statuses:
        return []
    bounded = max(1, min(int(limit), MAX_TESTS))
    rows: list[dict] = []
    for batch in _in_batches(section_ids):
        rows.extend(
            read_all(
                client.table("faculty_tests")
                .select(TEST_COLUMNS)
                .eq("institution_id", str(institution_id))
                .in_("section_id", batch)
                .in_("status", list(statuses))
                .order("scheduled_date")
                .limit(bounded)
            )
        )
    rows.sort(
        key=lambda row: (
            str(row.get("scheduled_date") or "9999-12-31"),
            str(row.get("title") or ""),
        )
    )
    return rows[:bounded]


def list_test_types(client: Client) -> dict[str, str]:
    """Small shared catalog: ``test_types`` code -> display name."""
    rows = read_all(
        client.table("test_types").select(TEST_TYPE_COLUMNS).order("code")
    )
    return {
        str(row.get("code")): str(row.get("name") or "")
        for row in rows
        if row.get("code")
    }


    return rows
