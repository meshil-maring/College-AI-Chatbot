"""Principals and record fixtures shared by academic foundation tests."""

from uuid import uuid4


TENANT = "10000000-0000-0000-0000-000000000001"
ORGANIZATION = "50000000-0000-0000-0000-000000000001"
FOREIGN_TENANT = "10000000-0000-0000-0000-000000000002"
DEPARTMENT = "20000000-0000-0000-0000-000000000001"
PROGRAM = "30000000-0000-0000-0000-000000000001"
YEAR = "40000000-0000-0000-0000-000000000001"
SEMESTER = "60000000-0000-0000-0000-000000000001"
SUBJECT = "70000000-0000-0000-0000-000000000001"
ALL_PERMISSIONS = [
    f"{entity}.{action}"
    for entity in ("departments", "academic_years")
    for action in ("read", "manage")
]


def principal(permissions=None):
    return {
        "user_id": str(uuid4()),
        "status": "active",
        "institution_id": TENANT,
        "roles": ["admin"],
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
        "effective_permissions": ALL_PERMISSIONS,
        "role_assignments": [{
            "role": "admin",
            "scope_type": "institution",
            "scope_id": TENANT,
            "scope_organization_id": ORGANIZATION,
            "is_active": True,
            "permissions": ALL_PERMISSIONS if permissions is None else permissions,
        }],
    }


def academic_year(**changes):
    return {
        "academic_year_id": YEAR,
        "institution_id": TENANT,
        "name": "2026–2027",
        "code": "2026-27",
        "start_date": "2026-07-01",
        "end_date": "2027-06-30",
        "is_current": False,
        "is_active": True,
        **changes,
    }


COURSE = SUBJECT
LINK = "80000000-0000-0000-0000-000000000001"
OFFERING = "90000000-0000-0000-0000-000000000001"
SECTION = "a0000000-0000-0000-0000-000000000001"
SETUP_PERMISSIONS = ALL_PERMISSIONS + [f"{resource}.{action}" for resource in ("courses", "semesters") for action in ("read", "manage")]


def setup_rows():
    shared = {"institution_id": TENANT, "is_active": True}
    return {
        "departments": {**shared, "department_id": DEPARTMENT, "name": "CSE", "code": "CSE", "description": None},
        "programs": {**shared, "program_id": PROGRAM, "department_id": DEPARTMENT, "name": "B.Tech CSE", "code": "BTECH", "description": None, "degree_type": "B.Tech", "duration_years": 4, "total_credits": None},
        "academic_years": academic_year(),
        "semesters": {**shared, "semester_id": SEMESTER, "academic_year_id": YEAR, "name": "Autumn", "code": "AUT", "semester_number": 1, "start_date": "2026-07-01", "end_date": "2026-12-31", "is_current": False},
        "courses": {**shared, "course_id": COURSE, "department_id": DEPARTMENT, "name": "Data Mining", "code": "DM", "description": None, "credits": 3.5, "lecture_hours": 3, "tutorial_hours": None, "practical_hours": 2},
        "program_courses": {**shared, "program_course_id": LINK, "program_id": PROGRAM, "course_id": COURSE, "semester_id": None, "course_type": "core", "is_required": True},
        "course_offerings": {**shared, "course_offering_id": OFFERING, "course_id": COURSE, "program_id": PROGRAM, "academic_year_id": YEAR, "semester_id": SEMESTER, "capacity": 60},
        "sections": {**shared, "section_id": SECTION, "course_offering_id": OFFERING, "name": "A", "code": "A", "capacity": 30},
    }
