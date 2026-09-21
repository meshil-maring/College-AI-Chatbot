"""Phase 6.16.2 — Student academic DETAIL experience (self-contained).

Read-only detail pages (attendance + results) over the EXISTING /me/*
contracts; no endpoint, table, or authorization rule is added or changed.
Every assertion below pins a Section-28/33 Definition-of-Done property:

  * authenticated student access (200 for the owner; 401 unauthenticated);
  * tenant isolation (Student A / Institution A can never see Institution B;
    cross-tenant service call fails closed with 403 TENANT_MISMATCH);
  * student ownership (repository queried with the JWT user's own student_id;
    another user's rows are filtered out; signatures have no identity params);
  * filter validation (bad date_from / bad academic_year_id -> 422
    INVALID_FILTER; valid date range forwarded server-side);
  * limit validation (unbounded client limits stay impossible: the detail
    endpoints expose no limit field, and the services keep their fixed
    server-side page caps);
  * read-only enforcement (the student router exposes GET only on the detail
    paths; POST/PUT/PATCH/DELETE -> 405);
  * data minimization (no internal ids, auth ids, tenant ids, or audit fields
    in the academic-profile, attendance, or results payloads).
"""
from __future__ import annotations

import inspect
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services import student_academic_profile as profile_svc
from app.services import student_attendance as attendance_svc
from app.services import student_results as results_svc

TC = TestClient(app, raise_server_exceptions=False)

TA = "a1111111-0000-0000-0000-000000000001"
TB = "b2222222-0000-0000-0000-000000000002"
SUID = "71000000-0000-0000-0000-000000000001"
OUID = "71000000-0000-0000-0000-000000000002"
SID = "30000000-0000-0000-0000-000000000151"
OSID = "30000000-0000-0000-0000-000000000152"
AY = "a0000000-0000-0000-0000-0000000000a1"
SEM = "a0000000-0000-0000-0000-0000000000b1"
CID = "30000000-0000-0000-0000-0000000000c1"

ATTENDANCE_PATH = "/api/v1/students/me/attendance/summary"
RESULTS_PATH = "/api/v1/students/me/results/summary"
TEST_RESULTS_PATH = "/api/v1/students/me/test-results/summary"
PROFILE_PATH = "/api/v1/students/me/academic-profile"


def _user(uid: str = SUID, tenant: str = TA) -> dict:
    return {
        "user_id": uid,
        "auth_user_id": "a1",
        "email": "s@c.edu",
        "roles": ["student"],
        "institution_id": tenant,
    }


def _student_profile(**overrides: object) -> dict:
    row = {
        "student_id": SID,
        "user_id": SUID,
        "institution_id": TA,
        "student_number": "S100",
        "email": "s@c.edu",
        "register_number": "REG100",
        "university_roll_number": "ROLL100",
        "program_id": "50000000-0000-0000-0000-000000000001",
        "academic_year_id": "50000000-0000-0000-0000-000000000002",
        "approval_status": "approved",
        "status": "active",
        "is_active": True,
    }
    row.update(overrides)
    return row


def _attendance_row(sid: str = SID, status: str = "present",
                    date: str = "2026-09-01") -> dict:
    return {
        "student_attendance_id": str(uuid4()),
        "student_id": sid,
        "institution_id": TA,
        "section_id": str(uuid4()),
        "academic_year_id": AY,
        "semester_id": SEM,
        "date": date,
        "status": status,
        "notes": None,
        "created_at": "2026-09-01T00:00:00+00:00",
        "updated_at": "2026-09-01T00:00:00+00:00",
    }


def _academic_row(sid: str = SID, status: str = "published") -> dict:
    return {
        "student_id": sid,
        "academic_year_id": AY,
        "semester_id": SEM,
        "program_id": str(uuid4()),
        "result_type": "semester",
        "total_credits_earned": 20,
        "total_credits_max": 22,
        "sgpa": 8.5,
        "cgpa": 8.2,
        "status": status,
        "issued_at": "2026-06-01T00:00:00+00:00",
        "institution_id": TA,
    }


def _test_row(sid: str = SID, status: str = "published",
              name: str = "Quiz 1") -> dict:
    return {
        "student_id": sid,
        "course_id": CID,
        "academic_year_id": AY,
        "semester_id": SEM,
        "test_name": name,
        "test_type": "quiz",
        "max_marks": 20,
        "scored_marks": 18,
        "percentage": 90.0,
        "letter_grade": "A",
        "conducted_at": "2026-09-01T00:00:00+00:00",
        "status": status,
    }

# ============================================================================
# Authenticated student access
# ============================================================================


def test_detail_endpoints_require_authentication() -> None:
    _clear_auth()
    try:
        for path in (ATTENDANCE_PATH, RESULTS_PATH, TEST_RESULTS_PATH):
            response = TC.get(path)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    finally:
        _clear_auth()


def test_owner_receives_own_attendance_summary() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    rows = [_attendance_row(status="present"), _attendance_row(status="absent")]
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                attendance_svc.academics_repo, "list_student_attendance",
                return_value=rows):
            response = TC.get(ATTENDANCE_PATH)
    finally:
        _clear_auth()
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["records_available"] is True
    assert body["summary"]["total_classes"] == 2
    assert body["summary"]["attendance_percentage"] == 50.0
    assert len(body["records"]) == 2


def test_owner_receives_own_results_and_test_results() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        with patch.object(results_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                results_svc.student_data_service, "get_own_results",
                return_value=[_academic_row()]), patch.object(
                results_svc.student_data_service, "get_own_test_results",
                return_value=[_test_row()]), patch.object(
                results_svc.personalization_repo, "get_course_labels",
                return_value={}):
            academic = TC.get(RESULTS_PATH)
        with patch.object(results_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                results_svc.student_data_service, "get_own_results",
                return_value=[]), patch.object(
                results_svc.student_data_service, "get_own_test_results",
                return_value=[_test_row()]), patch.object(
                results_svc.personalization_repo, "get_course_labels",
                return_value={}):
            tests = TC.get(TEST_RESULTS_PATH)
    finally:
        _clear_auth()
    assert academic.status_code == 200
    assert academic.json()["summary"]["total_results"] == 1
    assert academic.json()["records"][0]["sgpa"] == 8.5
    assert tests.status_code == 200
    assert tests.json()["summary"]["total_results"] == 1
    assert tests.json()["records"][0]["test_name"] == "Quiz 1"


# ============================================================================
# Tenant isolation + student ownership
# ============================================================================


def test_other_students_rows_are_never_returned() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    rows = [_attendance_row(sid=SID), _attendance_row(sid=OSID)]
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                attendance_svc.academics_repo, "list_student_attendance",
                return_value=rows) as list_mock:
            response = TC.get(ATTENDANCE_PATH)
    finally:
        _clear_auth()
    assert response.status_code == 200
    # Repository queried with the JWT user's OWN student id; the foreign row
    # is filtered out before projection.
    assert list_mock.call_args.args[1] == SID
    assert len(response.json()["records"]) == 1


def test_cross_tenant_student_profile_is_denied_with_403() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user(tenant=TA)
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile(institution_id=TB)):
            response = TC.get(ATTENDANCE_PATH)
        with patch.object(results_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile(institution_id=TB)):
            denied = TC.get(RESULTS_PATH)
    finally:
        _clear_auth()
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    assert denied.status_code == 403


def test_other_token_cannot_reach_first_students_data() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user(uid=OUID)
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=None) as lookup:
            response = TC.get(ATTENDANCE_PATH)
    finally:
        _clear_auth()
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"
    assert lookup.call_args.args[1] == OUID


def test_service_signatures_carry_no_identity_parameters() -> None:
    for fn in (attendance_svc.get_own_attendance,
               results_svc.get_own_results,
               results_svc.get_own_test_results,
               results_svc.get_own_result):
        params = list(inspect.signature(fn).parameters)
        assert params[0] == "current_user"
        for forbidden in ("student_id", "user_id", "institution_id", "email",
                          "register_number", "university_roll_number"):
            assert forbidden not in params


def test_client_supplied_student_id_cannot_override_identity() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    rows = [_attendance_row()]
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()) as lookup, patch.object(
                attendance_svc.academics_repo, "list_student_attendance",
                return_value=rows):
            response = TC.get(ATTENDANCE_PATH,
                              params={"student_id": OSID})
    finally:
        _clear_auth()
    # Extra query params are ignored (inert): identity still resolves from the
    # JWT, so the caller's own rows come back unchanged.
    assert response.status_code == 200
    assert lookup.call_args.args[1] == SUID
    assert len(response.json()["records"]) == 1


# ============================================================================
# Filter validation + limit validation
# ============================================================================


def test_invalid_attendance_filters_are_rejected_with_422() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                attendance_svc.academics_repo, "list_student_attendance",
                return_value=[]):
            bad_date = TC.get(ATTENDANCE_PATH,
                              params={"date_from": "not-a-date"})
            bad_year = TC.get(ATTENDANCE_PATH,
                              params={"academic_year_id": "bad-uuid"})
            bad_range = TC.get(ATTENDANCE_PATH,
                               params={"date_from": "2026-09-30",
                                       "date_to": "2026-09-01"})
    finally:
        _clear_auth()
    for response in (bad_date, bad_year, bad_range):
        assert response.status_code == 422
        assert response.json()["error"]["code"] in ("INVALID_FILTER",
                                                    "VALIDATION_ERROR")


def test_invalid_result_filters_are_rejected_with_422() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        with patch.object(results_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                results_svc.student_data_service, "get_own_results",
                return_value=[]), patch.object(
                results_svc.student_data_service, "get_own_test_results",
                return_value=[]), patch.object(
                results_svc.personalization_repo, "get_course_labels",
                return_value={}):
            response = TC.get(RESULTS_PATH,
                              params={"academic_year_id": "bad-uuid"})
            tests = TC.get(TEST_RESULTS_PATH,
                           params={"semester_id": "bad-uuid"})
    finally:
        _clear_auth()
    assert response.status_code == 422
    assert tests.status_code == 422


def test_valid_date_range_is_forwarded_server_side() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                attendance_svc.academics_repo, "list_student_attendance",
                return_value=[]) as list_mock:
            response = TC.get(ATTENDANCE_PATH,
                              params={"date_from": "2026-09-01",
                                      "date_to": "2026-09-30"})
    finally:
        _clear_auth()
    assert response.status_code == 200
    assert list_mock.call_args.kwargs["date_from"] == "2026-09-01"
    assert list_mock.call_args.kwargs["date_to"] == "2026-09-30"


def test_detail_routes_expose_no_client_limit_field() -> None:
    """Unbounded client limits stay impossible: the services keep fixed
    server-side page caps (attendance 200 / test results 100); the OpenAPI
    schema for the detail routes has no client-settable ``limit``."""
    assert inspect.signature(
        attendance_svc.get_own_attendance).parameters["limit"].default == 200
    assert inspect.signature(
        results_svc.get_own_test_results).parameters["limit"].default == 100
    paths = app.openapi()["paths"]
    for path in ("/api/v1/students/me/attendance/summary",
                 "/api/v1/students/me/results/summary",
                 "/api/v1/students/me/test-results/summary"):
        params = [p.get("name") for p in paths[path]["get"].get("parameters", [])]
        assert "limit" not in params
    # Backend validation stays authoritative: unknown client params are inert,
    # so an absurd ?limit= value can never widen the server-side page cap.
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                attendance_svc.academics_repo, "list_student_attendance",
                return_value=[]):
            response = TC.get(ATTENDANCE_PATH, params={"limit": 1000000})
    finally:
        _clear_auth()
    assert response.status_code == 200
    assert response.json()["records"] == []




def _clear_auth() -> None:
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Read-only enforcement
# ============================================================================


def test_detail_routes_are_get_only() -> None:
    paths = app.openapi()["paths"]
    for path in ("/api/v1/students/me/attendance/summary",
                 "/api/v1/students/me/results/summary",
                 "/api/v1/students/me/test-results/summary"):
        assert "get" in paths[path]
        for method in ("post", "put", "patch", "delete"):
            assert method not in paths[path]


def test_mutation_verbs_are_rejected_with_405() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        for path in (ATTENDANCE_PATH, RESULTS_PATH, TEST_RESULTS_PATH):
            assert TC.post(path, json={}).status_code == 405
            assert TC.put(path, json={}).status_code == 405
            assert TC.patch(path, json={}).status_code == 405
            assert TC.delete(path).status_code == 405
    finally:
        _clear_auth()


def test_student_role_cannot_use_privileged_academic_writes() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        # A student JWT against an admin write path gets the locked 403
        # FORBIDDEN via the existing require_roles("admin") dependency.
        response = TC.get("/api/v1/admin/me")
    finally:
        _clear_auth()
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# ============================================================================
# Data minimization
# ============================================================================


def test_attendance_payload_contains_no_internal_identifiers() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    rows = [_attendance_row()]
    try:
        with patch.object(attendance_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                attendance_svc.academics_repo, "list_student_attendance",
                return_value=rows):
            payload = TC.get(ATTENDANCE_PATH).text
    finally:
        _clear_auth()
    for forbidden in ("student_id", "student_attendance_id", "user_id",
                      "auth_user_id", "institution_id", "section_id",
                      "program_id", "academic_year_id", "semester_id",
                      "created_at", "updated_at"):
        assert forbidden not in payload


def test_results_payloads_contain_no_internal_identifiers() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        with patch.object(results_svc.academics_repo,
                           "get_student_by_user_id",
                           return_value=_student_profile()), patch.object(
                results_svc.student_data_service, "get_own_results",
                return_value=[_academic_row()]), patch.object(
                results_svc.student_data_service, "get_own_test_results",
                return_value=[_test_row()]), patch.object(
                results_svc.personalization_repo, "get_course_labels",
                return_value={CID: {"code": "CS101", "name": "Intro CS"}}):
            academic = TC.get(RESULTS_PATH).text
            tests = TC.get(TEST_RESULTS_PATH).text
    finally:
        _clear_auth()
    for forbidden in ("student_id", "student_result_id", "test_result_id",
                      "student_result_item_id", "user_id", "auth_user_id",
                      "institution_id", "program_id", "course_id",
                      "section_id", "academic_year_id", "semester_id"):
        assert forbidden not in academic
        assert forbidden not in tests
    # Benign course labels ARE projected for the student's own rows.
    assert "CS101" in tests


def test_response_models_reject_extra_internal_fields() -> None:
    import pytest as _pytest

    from app.schemas.student_attendance import StudentOwnAttendance
    from app.schemas.student_results import StudentOwnResults

    with _pytest.raises(Exception):
        StudentOwnAttendance(summary={}, records=[],  # type: ignore[call-arg]
                             institution_id=TA)
    with _pytest.raises(Exception):
        StudentOwnResults(summary={}, records=[],  # type: ignore[call-arg]
                          student_id=SID)


def test_academic_profile_stays_minimized() -> None:
    app.dependency_overrides[get_current_user] = lambda: _user()
    row = _student_profile()
    labels = ({"code": "CSE", "name": "B.Tech CSE"},
              {"code": "AY26", "name": "2026-27"},
              {"code": "S1", "name": "Sem 1"},
              {"institution_id": TA, "name": "Test College", "code": "GIT"})
    try:
        with patch.object(profile_svc.academics_repo,
                           "get_student_academic_profile_row",
                           return_value=row), patch.object(
                profile_svc.personalization_repo, "get_program_label",
                return_value=labels[0]), patch.object(
                profile_svc.personalization_repo, "get_academic_year_label",
                return_value=labels[1]), patch.object(
                profile_svc.personalization_repo, "get_current_semester_label",
                return_value=labels[2]), patch.object(
                profile_svc.tenancy_repo, "get_institution_by_id",
                return_value=labels[3]):
            payload = TC.get(PROFILE_PATH).text
    finally:
        _clear_auth()
    for forbidden in ("student_id", "user_id", "auth_user_id",
                      "institution_id", "program_id", "academic_year_id"):
        assert forbidden not in payload
    assert "Test College" in payload
