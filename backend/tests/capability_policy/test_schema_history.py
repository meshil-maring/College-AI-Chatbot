"""Test schema history."""

from __future__ import annotations

import pytest

import re

from .schema import (
    _created_tables,
    _table_body,
)

from .support import (
    _clean_dependencies,
    _migration_sql,
    _route_paths,
)


@pytest.mark.parametrize(
    "table",
    ["faculties", "faculty", "staffs", "staff", "staff_profiles", "faculty_profiles"],
)
def test_no_staff_or_faculty_profile_table_exists(table: str) -> None:
    """There is no staffs/faculty profile table anywhere in the schema ledger."""
    assert table not in _created_tables()


@pytest.mark.parametrize(
    "table",
    [
        "teaching_assignments",
        "faculty_assignments",
        "course_faculty",
        "instructor_assignments",
        "class_teachers",
        "faculty_courses",
        "faculty_students",
    ],
)
def test_no_teaching_assignment_or_faculty_student_scope_table_exists(
    table: str,
) -> None:
    """The Faculty -> Student scope relationship is NOT implemented."""
    assert table not in _created_tables()


def test_the_only_staff_faculty_scope_is_the_institution_role_grant() -> None:
    """`user_roles.scope_id` is the ONLY scope staff/faculty hold.

    This is the authoritative student-scope finding: staff and faculty are
    institution-scoped BY ROLE, with no narrower academic-assignment layer.
    """
    from app.core.security import SUPPORTED_ROLES

    assert "staff" in SUPPORTED_ROLES
    assert "faculty" in SUPPORTED_ROLES

    # `scope_type` / `scope_id` were added to the EXISTING user_roles table by
    # ALTER TABLE in the Phase 6.13 migration, not declared in CREATE TABLE.
    sql = _migration_sql()
    for column in ("scope_type", "scope_id", "scope_organization_id"):
        assert re.search(
            rf'ALTER TABLE "public"\."user_roles"\s*'
            rf'ADD COLUMN IF NOT EXISTS "{column}"',
            sql,
        ), column

    columns = _table_body("user_roles")
    for forbidden in ("course_id", "department_id", "section_id", "program_id"):
        assert forbidden not in columns, forbidden


def test_institution_membership_request_carries_no_assignment_semantics() -> None:
    """Onboarding metadata is NOT an academic assignment relationship."""
    columns = _table_body("institution_membership_requests")
    # `department` / `designation` are free-text onboarding metadata only.
    assert '"department"' in columns
    assert '"designation"' in columns
    for forbidden in ("course_id", "section_id", "program_id", "faculty_id"):
        assert forbidden not in columns, forbidden
    # Role escalation is structurally impossible at the database level.
    assert "array['staff'::text, 'faculty'::text]" in columns


def test_academic_tables_exist_but_carry_no_faculty_owner_relationship() -> None:
    """Courses/departments/sections exist, but none is linked to a faculty user.

    This is precisely why no faculty -> student scope can be derived today.
    """
    created = _created_tables()
    for academic_table in ("courses", "departments", "sections", "course_offerings"):
        assert academic_table in created, academic_table

    sql = _migration_sql()
    for academic_table in ("course_offerings", "sections", "courses"):
        definitions = re.findall(
            rf'CREATE TABLE(?: IF NOT EXISTS)? "public"\."{academic_table}"\s*\((.*?);',
            sql,
            re.S | re.I,
        )
        assert definitions, academic_table
        assert not any(
            re.search(r'REFERENCES "public"\."users"', definition, re.I)
            or re.search(
                r'"(?:instructor|faculty|teacher|owner)_user_id"',
                definition,
                re.I,
            )
            for definition in definitions
        ), academic_table


def test_no_staff_or_faculty_router_exists() -> None:
    """Capability is expressed by role dependencies, not by role-specific APIs."""
    paths = _route_paths()
    assert not [p for p in paths if p.startswith("/api/v1/staff")]
    assert not [p for p in paths if p.startswith("/api/v1/faculty")]
