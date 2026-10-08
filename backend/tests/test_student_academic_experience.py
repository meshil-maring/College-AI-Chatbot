"""Student Academic Experience & Performance — backend contract & security tests.

Covers the four additive, read-only student endpoints introduced by this
phase and the aggregation service behind them:

    GET /api/v1/students/me/attendance/subjects   -> own subject-wise attendance
    GET /api/v1/students/me/assessments/upcoming  -> own upcoming assessments
    GET /api/v1/students/me/performance/subjects  -> own subject performance
    GET /api/v1/students/me/timeline              -> own derived timeline

Covered:
  * server-side student identity (JWT -> students row; no client-supplied
    identifier can select another student — IDOR);
  * tenant isolation (cross-institution rows are filtered and a mismatched
    tenant fails closed with 403 TENANT_MISMATCH);
  * account state (pending / inactive / profileless students are rejected
    with the existing codes);
  * assessment visibility (DRAFT / CANCELLED / past-scheduled never
    student-visible; publication comes from the existing result service);
  * teacher/internal metadata never appears (remarks, description,
    marks_state, actors, internal database identifiers);
  * authoritative attendance math (same statistics() helper and the same
    MONITORING_THRESHOLD the faculty surface uses; legacy mirror merged with
    roster+date dedup; no fabrication when data is absent);
  * performance aggregation correctness plus honest null states;
  * timeline derivation from existing records only;
  * read-only surface (GET only) and permission enforcement.

No existing contract, table or authorization rule is modified by this suite.
"""

from __future__ import annotations

import datetime
from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app
from app.repositories import student_academic_experience as experience_repo
from app.schemas.student_results import (
    StudentOwnResults,
    StudentOwnResultsSummary,
    StudentOwnTestResults,
    StudentOwnTestResultsSummary,
    StudentTestResultRecord,
)
from app.services import student_academic_experience as experience_service
from app.services import student_results as student_results_service

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "a1111111-0000-0000-0000-0000000000a1"
TENANT_B = "b2222222-0000-0000-0000-0000000000b2"
STUDENT_USER_ID = "71000000-0000-0000-0000-000000000001"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"
OTHER_STUDENT_ID = "30000000-0000-0000-0000-000000000152"

SECTION_A = "40000000-0000-0000-0000-00000000000a"
SECTION_B = "40000000-0000-0000-0000-00000000000b"
SECTION_FOREIGN = "40000000-0000-0000-0000-0000000000ff"
OFFERING_A = "41000000-0000-0000-0000-00000000000a"
OFFERING_B = "41000000-0000-0000-0000-00000000000b"
COURSE_A = "42000000-0000-0000-0000-00000000000a"
COURSE_B = "42000000-0000-0000-0000-00000000000b"
ROSTER_A1 = "43000000-0000-0000-0000-000000000001"
ROSTER_A2 = "43000000-0000-0000-0000-000000000002"
ROSTER_FOREIGN = "43000000-0000-0000-0000-0000000000ff"
SESSION_1 = "44000000-0000-0000-0000-000000000001"
SESSION_2 = "44000000-0000-0000-0000-000000000002"
SESSION_3 = "44000000-0000-0000-0000-000000000003"
SESSION_4 = "44000000-0000-0000-0000-000000000004"

NEW_ENDPOINTS = (
    "/api/v1/students/me/attendance/subjects",
    "/api/v1/students/me/assessments/upcoming",
    "/api/v1/students/me/performance/subjects",
    "/api/v1/students/me/timeline",
)

IDENTITY_QUERY = {
    "student_id": OTHER_STUDENT_ID,
    "user_id": "71000000-0000-0000-0000-000000000009",
    "register_number": "REG-B-999",
    "university_roll_number": "ROLL-B-999",
    "institution_id": TENANT_B,
}


def _student_user(user_id=STUDENT_USER_ID, tenant=TENANT_A, roles=None):
    return {
        "user_id": user_id,
        "auth_user_id": "61000000-0000-0000-0000-000000000001",
        "email": "student@college.edu",
        "roles": roles if roles is not None else ["student"],
        "status": "active",
        "institution_id": tenant,
    }


def _student_profile(institution_id=TENANT_A, approval_status="approved",
                     is_active=True, student_id=STUDENT_ID,
                     user_id=STUDENT_USER_ID):
    return {
        "student_id": student_id,
        "user_id": user_id,
        "institution_id": institution_id,
        "student_number": "STU100",
        "approval_status": approval_status,
        "is_active": is_active,
        "email": "student@college.edu",
        "status": "active",
        "auth_user_id": "61000000-0000-0000-0000-000000000001",
    }


def _db_for_student(**kwargs):
    """Supabase stub whose ``students`` lookup returns the given profile."""
    db = MagicMock()
    row = _student_profile(**kwargs)
    chain = db.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = MagicMock(data=row)
    return db


@pytest.fixture(autouse=True)
def student_auth():
    app.dependency_overrides[get_current_user] = _student_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Shared row builders (rows the repository functions return)
# ============================================================================

def _roster(roster_id, section_id, offering_id, institution_id=TENANT_A,
            linked_student_id=STUDENT_ID):
    return {
        "roster_id": roster_id,
        "institution_id": institution_id,
        "section_id": section_id,
        "course_offering_id": offering_id,
        "semester_id": "45000000-0000-0000-0000-00000000000s",
        "register_number": "REG-100",
        "roster_status": "ACTIVE",
        "linked_student_id": linked_student_id,
    }


def _session(session_id, section_id, offering_id, day, institution_id=TENANT_A):
    return {
        "session_id": session_id,
        "institution_id": institution_id,
        "section_id": section_id,
        "course_offering_id": offering_id,
        "session_date": day,
    }


def _record(record_id, session_id, roster_id, status):
    return {"record_id": record_id, "session_id": session_id,
            "roster_id": roster_id, "status": status}


def _default_rosters():
    return [_roster(ROSTER_A1, SECTION_A, OFFERING_A),
            _roster(ROSTER_A2, SECTION_B, OFFERING_B)]


def _default_sections():
    return [
        {"section_id": SECTION_A, "course_offering_id": OFFERING_A,
         "code": "A1", "name": "Section A", "is_active": True},
        {"section_id": SECTION_B, "course_offering_id": OFFERING_B,
         "code": "B1", "name": "Section B", "is_active": True},
    ]


def _default_offerings():
    return [
        {"course_offering_id": OFFERING_A, "course_id": COURSE_A,
         "academic_year_id": "45000000-0000-0000-0000-00000000000y",
         "semester_id": "45000000-0000-0000-0000-00000000000s"},
        {"course_offering_id": OFFERING_B, "course_id": COURSE_B,
         "academic_year_id": "45000000-0000-0000-0000-00000000000y",
         "semester_id": "45000000-0000-0000-0000-00000000000s"},
    ]


def _default_courses():
    return [
        {"course_id": COURSE_A, "code": "CS301", "name": "DBMS"},
        {"course_id": COURSE_B, "code": "CS302", "name": "Operating Systems"},
    ]

def _default_test_types():
    return {"quiz": "Quiz", "midterm": "Mid-Term"}

def _future_date(days=0):
    return (datetime.datetime.now(UTC) + datetime.timedelta(days=days)).date().isoformat()



def _default_sessions():
    return [
        _session(SESSION_1, SECTION_A, OFFERING_A, "2026-09-01"),
        _session(SESSION_2, SECTION_A, OFFERING_A, "2026-09-02"),
        _session(SESSION_3, SECTION_B, OFFERING_B, "2026-09-01"),
        _session(SESSION_4, SECTION_B, OFFERING_B, "2026-09-02"),
    ]


def _default_records():
    return [
        _record("55000000-0000-0000-0000-000000000001", SESSION_1, ROSTER_A1, "present"),
        _record("55000000-0000-0000-0000-000000000002", SESSION_2, ROSTER_A1, "absent"),
        _record("55000000-0000-0000-0000-000000000003", SESSION_3, ROSTER_A2, "present"),
        _record("55000000-0000-0000-0000-000000000004", SESSION_4, ROSTER_A2, "present"),
    ]


def _default_legacy():
    # One mirrored row for section A on a date WITHOUT a faculty session
    # (counted), and one duplicate for section B on a session date (deduped).
    return [
        {"student_attendance_id": "56000000-0000-0000-0000-000000000001",
         "institution_id": TENANT_A, "section_id": SECTION_A,
         "student_id": STUDENT_ID, "date": "2026-09-03", "status": "present"},
        {"student_attendance_id": "56000000-0000-0000-0000-000000000002",
         "institution_id": TENANT_A, "section_id": SECTION_B,
         "student_id": STUDENT_ID, "date": "2026-09-01", "status": "present"},
    ]


def _patch_experience_repo(**overrides):
    """Patch every repository function with a deterministic default."""
    defaults = {
        "list_linked_rosters": _default_rosters(),
        "list_sections": _default_sections(),
        "list_course_offerings": _default_offerings(),
        "list_courses": _default_courses(),
        "list_section_sessions": _default_sessions(),
        "list_records_for_rosters": _default_records(),
        "list_legacy_attendance": _default_legacy(),
        "list_faculty_tests": [],
        "list_test_types": {"quiz": "Quiz", "midterm": "Mid-Term"},
    }
    defaults.update(overrides)
    return [
        patch.object(experience_repo, name, return_value=value)
        for name, value in defaults.items()
    ]


def _patch_scope(institution_id=TENANT_A, **kwargs):
    return patch(
        "app.services.student_context.get_admin_client",
        return_value=_db_for_student(institution_id=institution_id, **kwargs),
    )


def _repo_defaults(**overrides):
    defaults = {
        "list_linked_rosters": _default_rosters(),
        "list_sections": _default_sections(),
        "list_course_offerings": _default_offerings(),
        "list_courses": _default_courses(),
        "list_section_sessions": _default_sessions(),
        "list_records_for_rosters": _default_records(),
        "list_legacy_attendance": _default_legacy(),
        "list_faculty_tests": [],
        "list_test_types": {"quiz": "Quiz", "midterm": "Mid-Term"},
    }
    defaults.update(overrides)
    return defaults


def _experience_env(scope_kwargs=None, **repo_overrides):
    """Enter the full patch environment for one request.

    Returns ``(stack, mocks)`` where ``mocks`` maps each patched repository
    function to its MagicMock (for IDOR/scoping assertions). The eligibility
    chain (``student_context.get_student_context``) stays REAL — only its
    database client and the repository projections are stubbed, so account
    state and tenant checks are genuinely exercised.
    """
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(_patch_scope(**(scope_kwargs or {})))
    stack.enter_context(
        patch(
            "app.services.student_academic_experience.get_admin_client",
            return_value=MagicMock(),
        )
    )
    # The existing publication-filtered result services stay authoritative for
    # score/result data; default them to empty so no test can accidentally
    # reach real database machinery (individual tests override as needed).
    stack.enter_context(
        patch.object(
            student_results_service,
            "get_own_test_results",
            return_value=StudentOwnTestResults(
                summary=StudentOwnTestResultsSummary(), records=[]
            ),
        )
    )
    stack.enter_context(
        patch.object(
            student_results_service,
            "get_own_results",
            return_value=StudentOwnResults(
                summary=StudentOwnResultsSummary(), records=[]
            ),
        )
    )
    mocks = {}
    for name, value in _repo_defaults(**repo_overrides).items():
        mocks[name] = stack.enter_context(
            patch.object(experience_repo, name, return_value=value)
        )
    return stack, mocks


def _db_no_profile():
    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    return db


def _published_tests(records):
    return patch.object(
        student_results_service,
        "get_own_test_results",
        return_value=StudentOwnTestResults(
            summary=StudentOwnTestResultsSummary(
                records_available=bool(records), total_results=len(records)
            ),
            records=records,
        ),
    )


def _published_results(records):
    return patch.object(
        student_results_service,
        "get_own_results",
        return_value=StudentOwnResults(
            summary=StudentOwnResultsSummary(
                records_available=bool(records), total_results=len(records)
            ),
            records=records,
        ),
    )


def _test_record(**overrides):
    payload = {
        "test_name": "Midterm 1",
        "test_type": "midterm",
        "course_code": "CS301",
        "course_name": "DBMS",
        "max_marks": 100.0,
        "scored_marks": 80.0,
        "percentage": 80.0,
        "conducted_at": "2026-09-10T09:00:00+00:00",
        "mark_status": "present",
    }
    payload.update(overrides)
    return StudentTestResultRecord(**payload)


def _test_lifecycle(test_id, section_id, title, test_type, status,
                    scheduled_date=None, start_time=None, end_time=None,
                    duration_minutes=None, max_marks=None,
                    institution_id=TENANT_A, description=None):
    """A deterministic ``faculty_tests`` row (internal ids never exported)."""
    return {
        "test_id": test_id,
        "institution_id": institution_id,
        "section_id": section_id,
        "title": title,
        "test_type": test_type,
        "status": status,
        "scheduled_date": scheduled_date,
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "max_marks": max_marks,
        "description": description,
    }



# 1. Authentication, identity, eligibility, tenant isolation (API)
# ============================================================================

class TestAuthenticationAndIdentity:
    def test_all_new_endpoints_require_authentication(self):
        app.dependency_overrides.pop(get_current_user, None)
        for path in NEW_ENDPOINTS:
            response = client.get(path)
            assert response.status_code == 401, path
            assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_client_supplied_identity_parameters_are_ignored(self):
        """IDOR: foreign student/user/register/roll/institution values change nothing."""
        stack, mocks = _experience_env()
        with stack:
            for path in NEW_ENDPOINTS:
                response = client.get(path, params=IDENTITY_QUERY)
                assert response.status_code == 200, path
        # The roster lookup is keyed by the JWT-derived student + tenant ONLY.
        assert mocks["list_linked_rosters"].call_args.args[1] == STUDENT_ID
        assert mocks["list_linked_rosters"].call_args.args[2] == TENANT_A
        for call in mocks["list_linked_rosters"].call_args_list:
            assert call.args[1] == STUDENT_ID
            assert call.args[2] == TENANT_A

    def test_manipulated_record_identifiers_have_no_route(self):
        """Attendance/session/test/result ids are not part of any new contract."""
        stack, _ = _experience_env()
        with stack:
            for suffix in ("?attendance_id=x", "?session_id=x", "?test_id=x",
                           "?result_id=x", "?roster_id=x"):
                response = client.get(NEW_ENDPOINTS[0] + suffix)
                assert response.status_code == 200
            missing = client.get(
                "/api/v1/students/me/timeline/"
                "55000000-0000-0000-0000-000000000001"
            )
            assert missing.status_code == 404

    def test_student_without_profile_is_404(self):
        with patch(
            "app.services.student_context.get_admin_client",
            return_value=_db_no_profile(),
        ), patch(
            "app.services.student_academic_experience.get_admin_client",
            return_value=MagicMock(),
        ):
            response = client.get(NEW_ENDPOINTS[0])
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"

    def test_pending_student_is_rejected(self):
        stack, _ = _experience_env(scope_kwargs={"approval_status": "pending"})
        with stack:
            response = client.get(NEW_ENDPOINTS[0])
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_NOT_APPROVED"

    def test_inactive_student_is_rejected(self):
        stack, _ = _experience_env(scope_kwargs={"is_active": False})
        with stack:
            response = client.get(NEW_ENDPOINTS[1])
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_INACTIVE"

    def test_cross_tenant_student_context_fails_closed(self):
        """Student row of institution A behind a tenant-B session -> 403."""
        app.dependency_overrides[get_current_user] = lambda: _student_user(
            tenant=TENANT_B
        )
        stack, _ = _experience_env()  # profile stays institution A
        with stack:
            response = client.get(NEW_ENDPOINTS[3])
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"

    def test_student_without_a_tenant_fails_closed(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user(
            tenant=None
        )
        stack, _ = _experience_env(scope_kwargs={"institution_id": None})
        with stack:
            response = client.get(NEW_ENDPOINTS[0])
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"


# ============================================================================
# 2. Subject-wise attendance — authoritative math, dedup, threshold, scoping
# ============================================================================

class TestSubjectAttendance:
    def test_api_returns_own_subject_rows_with_authoritative_math(self):
        stack, _ = _experience_env()
        with stack:
            response = client.get(NEW_ENDPOINTS[0])
        assert response.status_code == 200
        body = response.json()
        assert body["records_available"] is True
        assert body["monitoring_threshold"] == 75.0
        assert body["subject_count"] == 2
        first, second = body["subjects"]
        # CS301: faculty records (present, absent) + ONE legacy mirror row
        # on a date without a session -> 3 conducted, 2 present = 66.67%.
        assert first["subject_code"] == "CS301"
        assert first["classes_conducted"] == 3
        assert first["classes_present"] == 2
        assert first["classes_absent"] == 1
        assert first["attendance_percentage"] == 66.67
        assert first["below_threshold"] is True
        # CS302: 2 faculty records; the legacy mirror row duplicates an
        # existing session date and is deduplicated, not double counted.
        assert second["subject_code"] == "CS302"
        assert second["classes_conducted"] == 2
        assert second["classes_present"] == 2
        assert second["attendance_percentage"] == 100.0
        assert second["below_threshold"] is False
        # Overall aggregates the same merged records (5 conducted, 4 present).
        overall = body["overall"]
        assert overall["classes_conducted"] == 5
        assert overall["classes_present"] == 4
        assert overall["attendance_percentage"] == 80.0
        assert overall["below_threshold"] is False

    def test_service_matches_the_faculty_reporting_statistics(self):
        """Same helper, same threshold as the faculty surface — no drift."""
        from app.services import faculty_attendance_reporting as reporting

        stack, _ = _experience_env()
        with stack:
            result = experience_service.get_subject_attendance(_student_user())
        assert result.monitoring_threshold == float(reporting.MONITORING_THRESHOLD)
        assert reporting.MONITORING_THRESHOLD == 75
        expected = reporting.statistics([
            {"status": "present"}, {"status": "absent"}, {"status": "present"},
        ])
        assert expected["attendance_percentage"] == 66.67
        assert expected["low_attendance"] is True

    def test_threshold_boundary_is_exactly_the_existing_policy(self):
        """Exactly at the threshold -> NOT below it (existing faculty rule)."""
        records = [
            _record(f"55000000-0000-0000-0000-00000000001{i}",
                    SESSION_1, ROSTER_A1,
                    "present" if i < 3 else "absent")
            for i in range(4)
        ]
        stack, _ = _experience_env(
            list_linked_rosters=[_roster(ROSTER_A1, SECTION_A, OFFERING_A)],
            list_sections=_default_sections()[:1],
            list_course_offerings=_default_offerings()[:1],
            list_courses=_default_courses()[:1],
            list_section_sessions=_default_sessions()[:1],
            list_records_for_rosters=records,
            list_legacy_attendance=[],
        )
        with stack:
            body = client.get(NEW_ENDPOINTS[0]).json()
        assert body["subjects"][0]["attendance_percentage"] == 75.0
        assert body["subjects"][0]["below_threshold"] is False

    def test_empty_attendance_is_an_empty_state_not_zeros(self):
        stack, _ = _experience_env(list_linked_rosters=[])
        with stack:
            response = client.get(NEW_ENDPOINTS[0])
        assert response.status_code == 200
        body = response.json()
        assert body["records_available"] is False
        assert body["subjects"] == []
        assert body["subject_count"] == 0
        assert body["overall"]["attendance_percentage"] is None
        assert body["overall"]["below_threshold"] is None

    def test_rosters_of_other_students_or_tenants_are_ignored(self):
        """Defensive IDOR/tenant filter even if a repository row slips through."""
        foreign = _roster(ROSTER_FOREIGN, SECTION_FOREIGN, OFFERING_A,
                          institution_id=TENANT_B,
                          linked_student_id=OTHER_STUDENT_ID)
        stack, _ = _experience_env(
            list_linked_rosters=[foreign] + _default_rosters(),
        )
        with stack:
            body = client.get(NEW_ENDPOINTS[0]).json()
        codes = [row["subject_code"] for row in body["subjects"]]
        assert codes == ["CS301", "CS302"]
        assert body["subject_count"] == 2

    def test_foreign_records_sessions_and_legacy_rows_are_excluded(self):
        foreign_session = _session(SESSION_4, SECTION_A, OFFERING_A,
                                   "2026-09-04", institution_id=TENANT_B)
        foreign_record = _record(
            "55000000-0000-0000-0000-000000000099", SESSION_4, ROSTER_A1, "present"
        )
        foreign_legacy = {
            "student_attendance_id": "56000000-0000-0000-0000-000000000099",
            "institution_id": TENANT_B, "section_id": SECTION_A,
            "student_id": OTHER_STUDENT_ID, "date": "2026-09-05",
            "status": "present",
        }
        stack, _ = _experience_env(
            list_section_sessions=_default_sessions() + [foreign_session],
            list_records_for_rosters=_default_records() + [foreign_record],
            list_legacy_attendance=_default_legacy() + [foreign_legacy],
        )
        with stack:
            body = client.get(NEW_ENDPOINTS[0]).json()
        first = body["subjects"][0]
        # CS301 keeps S1/S2 + the foreign record (resolved via own-tenant
        # session SESSION_4 on 09-02) + its unmatched legacy row on 09-03.
        # 4 conducted / 3 present -> exactly 75%, which is NOT below the
        # 75% threshold (boundary semantics: >= threshold is passing).
        assert first["classes_conducted"] == 4
        assert first["classes_present"] == 3
        assert first["attendance_percentage"] == 75.0
        assert first["below_threshold"] is False

        # The foreign record resolves via the own-tenant SESSION_4 date
        # (2026-09-02) but belongs to ROSTER_A1, so roster-based grouping
        # keeps it in CS301. CS302 is unchanged at 2/2.
        cs2 = body["subjects"][1]
        assert cs2["classes_conducted"] == 2
        assert cs2["classes_present"] == 2
        assert cs2["attendance_percentage"] == 100.0
        assert cs2["below_threshold"] is False
        # 4 (CS301) + 2 (CS302) = 6 conducted, 3 + 2 = 5 present.
        assert body["overall"]["classes_conducted"] == 6
        assert body["overall"]["classes_present"] == 5
        assert body["overall"]["attendance_percentage"] == 83.33

    def test_subject_filter_narrows_to_matching_subject_only(self):
        stack, _ = _experience_env()
        with stack:
            response = client.get(NEW_ENDPOINTS[0], params={"subject": "cs302"})
        body = response.json()
        assert body["subject_count"] == 1
        assert body["subjects"][0]["subject_code"] == "CS302"
        assert body["overall"]["classes_conducted"] == 2

    def test_subject_filter_with_no_match_is_an_empty_state(self):
        stack, _ = _experience_env()
        with stack:
            response = client.get(NEW_ENDPOINTS[0], params={"subject": "NOPE"})
        body = response.json()
        assert body["records_available"] is False
        assert body["subjects"] == []

    def test_overlong_subject_filter_is_rejected(self):
        response = client.get(NEW_ENDPOINTS[0], params={"subject": "x" * 65})
        assert response.status_code == 422

    def test_response_never_contains_internal_identifiers(self):
        stack, _ = _experience_env()
        with stack:
            body = client.get(NEW_ENDPOINTS[0]).json()
        forbidden = {
            "roster_id", "session_id", "record_id", "student_attendance_id",
            "student_id", "user_id", "institution_id", "section_id",
            "course_offering_id", "course_id", "register_number",
            "university_roll_number",
        }

        def walk(node):
            if isinstance(node, dict):
                assert not (forbidden & set(node)), forbidden & set(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(body)


# ============================================================================
# 3. Upcoming assessments — existing faculty_tests lifecycle, own sections only
# ============================================================================

class TestUpcomingAssessments:
    def test_upcoming_assessments_exclude_draft_cancelled_foreign_and_other_sections(self):
        today = _future_date(0)
        tests = [
            _test_lifecycle("t1", SECTION_A, "Today quiz", "quiz", "ONGOING",
                            scheduled_date=today, max_marks=10.0),
            _test_lifecycle("t2", SECTION_A, "Tomorrow", "quiz", "SCHEDULED",
                            scheduled_date=_future_date(1), max_marks=20.0),
            _test_lifecycle("t3", SECTION_A, "Draft work", "quiz", "DRAFT",
                            scheduled_date=_future_date(2), max_marks=20.0),
            _test_lifecycle("t4", SECTION_A, "Cancelled", "quiz", "CANCELLED",
                            scheduled_date=_future_date(3), max_marks=20.0),
            _test_lifecycle("t5", SECTION_A, "Foreign tenant", "quiz", "ONGOING",
                            scheduled_date=_future_date(2), max_marks=20.0,
                            institution_id=TENANT_B),
            _test_lifecycle("t6", SECTION_B, "Other section", "quiz", "ONGOING",
                            scheduled_date=_future_date(1), max_marks=20.0),
        ]
        stack, _ = _experience_env(
            list_faculty_tests=tests,
            list_test_types=_default_test_types(),
        )
        with stack:
            body = client.get(NEW_ENDPOINTS[1]).json()
        assert body["records_available"] is True
        assert body["total"] == 3
        titles = [item["title"] for item in body["items"]]
        # Sorted by (scheduled_date, title): Today quiz (today) first, then
        # Other section and Tomorrow share tomorrow's date so title order
        # decides: "Other section" < "Tomorrow".
        assert titles == ["Today quiz", "Other section", "Tomorrow"], titles
        # Serialized with the schema: no internal ids, no description/actors.
        first = body["items"][0]
        assert first["subject_code"] == "CS301"
        assert first["subject_name"] == "DBMS"
        assert first["section_label"] == "A1"
        assert first["max_marks"] == 10.0
        assert first["start_time"] is None
        assert first["test_type_name"] == "Quiz"
        assert first["status"] == "ONGOING"
        for key in ("description", "remarks", "actors", "version"):
            assert key not in first

    def test_upcoming_assessments_honour_limit_and_reject_out_of_range(self):
        tests = [
            _test_lifecycle("t1", SECTION_A, "One", "quiz", "ONGOING",
                            scheduled_date=_future_date(0), max_marks=10.0),
            _test_lifecycle("t2", SECTION_A, "Two", "quiz", "ONGOING",
                            scheduled_date=_future_date(1), max_marks=10.0),
            _test_lifecycle("t3", SECTION_A, "Three", "quiz", "ONGOING",
                            scheduled_date=_future_date(2), max_marks=10.0),
        ]
        stack, _ = _experience_env(
            list_faculty_tests=tests, list_test_types=_default_test_types(),
        )
        with stack:
            first = client.get(NEW_ENDPOINTS[1], params={"limit": 1}).json()
            bad = [
                client.get(NEW_ENDPOINTS[1], params={"limit": 0}).status_code,
                client.get(NEW_ENDPOINTS[1], params={"limit": 51}).status_code,
                client.get(NEW_ENDPOINTS[1],
                           params={"limit": True}).status_code,
            ]
        assert [i["title"] for i in first["items"]] == ["One"]
        assert bad == [422, 422, 422]

    def test_upcoming_assessments_reject_non_integer_limit(self):
        response = client.get(
            NEW_ENDPOINTS[1], params={"limit": "twenty"}
        )
        assert response.status_code == 422

    def test_subject_filter_surfaces_only_the_selected_section(self):
        tests = [
            _test_lifecycle("t1", SECTION_A, "DC1", "quiz", "ONGOING",
                            scheduled_date=_future_date(0), max_marks=10.0),
            _test_lifecycle("t2", SECTION_B, "DS1", "quiz", "ONGOING",
                            scheduled_date=_future_date(1), max_marks=10.0),
        ]
        stack, _ = _experience_env(
            list_faculty_tests=tests,
            list_test_types=_default_test_types(),
        )
        with stack:
            by_code = {
                item["subject_code"]: item["title"]
                for item in client.get(NEW_ENDPOINTS[1],
                                       params={"subject": "CS302"}).json()[
                                   "items"]
            }
            by_name = {
                item["subject_name"]: item["title"]
                for item in client.get(NEW_ENDPOINTS[1],
                                       params={"subject": "Operating Systems"}).json()[
                                   "items"]
            }
        assert by_code == {"CS302": "DS1"}
        assert by_name == {"Operating Systems": "DS1"}

    def test_completed_assessments_are_never_upcoming(self):
        tests = [
            _test_lifecycle("t1", SECTION_A, "Finished", "quiz", "COMPLETED",
                            scheduled_date=_future_date(0), max_marks=10.0),
            _test_lifecycle("t2", SECTION_A, "Future", "quiz", "SCHEDULED",
                            scheduled_date=_future_date(1), max_marks=10.0),
        ]
        stack, _ = _experience_env(
            list_faculty_tests=tests, list_test_types=_default_test_types(),
        )
        with stack:
            body = client.get(NEW_ENDPOINTS[1]).json()
        assert [i["title"] for i in body["items"]] == ["Future"]

        forbidden = {
            "test_id", "student_id", "user_id", "institution_id",
            "section_id", "description", "remarks", "actors", "version",
            "marks_state", "created_by", "updated_by",
        }

        def walk(node):
            if isinstance(node, dict):
                assert not (forbidden & set(node)), forbidden & set(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(body)
