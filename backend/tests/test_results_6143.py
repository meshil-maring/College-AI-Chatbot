"""Phase 6.14.3 - Test & exam result integration (self-contained)."""
from unittest.mock import MagicMock, patch
from uuid import uuid4
import inspect
import pytest
from fastapi.testclient import TestClient
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services import student_results as svc
TC = TestClient(app, raise_server_exceptions=False)
TA = "a1111111-0000-0000-0000-000000000001"
TB = "b2222222-0000-0000-0000-000000000002"
SUID = "71000000-0000-0000-0000-000000000001"
OUID = "71000000-0000-0000-0000-000000000002"
SID = "30000000-0000-0000-0000-000000000151"
OSID = "30000000-0000-0000-0000-000000000152"
AY = "a0000000-0000-0000-0000-0000000000a1"
SEM = "a0000000-0000-0000-0000-0000000000b1"
RID = "40000000-0000-0000-0000-000000000701"
CID = "30000000-0000-0000-0000-0000000000c1"
def _U(uid=SUID, tenant=TA):
    return {"user_id": uid, "auth_user_id": "a1",
            "email": "s@c.edu", "roles": ["student"],
            "institution_id": tenant}
def _P(**ov):
    r = {"student_id": SID, "user_id": SUID,
         "institution_id": TA, "student_number": "S100",
         "status": "active", "is_active": True}
    r.update(ov)
    return r
def _AR(sid=SID, status="published", sgpa=8.5, cgpa=8.2):
    return {"student_id": sid, "academic_year_id": AY,
            "semester_id": SEM, "program_id": str(uuid4()),
            "result_type": "semester", "total_credits_earned": 20,
            "total_credits_max": 22, "sgpa": sgpa, "cgpa": cgpa,
            "status": status, "issued_at": "2026-06-01T00:00:00+00:00",
            "institution_id": TA}
def _TR(sid=SID, status="published", name="Quiz 1"):
    return {"student_id": sid, "course_id": CID,
            "academic_year_id": AY, "semester_id": SEM,
            "test_name": name, "test_type": "quiz",
            "max_marks": 20, "scored_marks": 18,
            "percentage": 90.0, "letter_grade": "A",
            "conducted_at": "2026-09-01T00:00:00+00:00",
            "status": status}
@pytest.fixture(autouse=True)
def _cl():
    yield
    app.dependency_overrides.pop(get_current_user, None)
def _mk(profile, results=None, testrows=None, labels=None):
    p1 = patch.object(svc.academics_repo, "get_student_by_user_id",
                      return_value=profile)
    p2 = patch.object(svc.student_data_service, "get_own_results",
                      return_value=(results if results is not None else []))
    p3 = patch.object(svc.student_data_service, "get_own_test_results",
                      return_value=(testrows if testrows is not None else []))
    p4 = patch.object(svc.personalization_repo, "get_course_labels",
                      return_value=(labels if labels is not None else {}))
    return p1, p2, p3, p4
def test_1_own_academic():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2, p3, p4 = _mk(_P(), results=[_AR()])
    with p1, p2, p3, p4:
        r = TC.get("/api/v1/students/me/results/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total_results"] == 1
    assert body["summary"]["records_available"] is True
    assert body["records"][0]["sgpa"] == 8.5
    assert body["records"][0]["status"] == "published"
def test_2_own_test():
    app.dependency_overrides[get_current_user] = lambda: _U()
    labels = {CID: {"course_id": CID, "code": "CS101", "name": "Intro CS"}}
    p1, p2, p3, p4 = _mk(_P(), testrows=[_TR()], labels=labels)
    with p1, p2, p3, p4:
        r = TC.get("/api/v1/students/me/test-results/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total_results"] == 1
    rec = body["records"][0]
    assert rec["test_name"] == "Quiz 1"
    assert rec["scored_marks"] == 18
    assert rec["course_code"] == "CS101"
    for f in ("student_id", "test_result_id", "institution_id",
              "course_id", "section_id", "academic_year_id"):
        assert f not in rec
def test_3_unpublished_not_exposed():
    app.dependency_overrides[get_current_user] = lambda: _U()
    rows = [_AR(status="published"), _AR(status="draft"),
            _AR(status="withheld")]
    p1, p2, p3, p4 = _mk(_P(), results=rows,
        testrows=[_TR(status="published"), _TR(status="draft"),
                  _TR(status="withheld", name="Q2")])
    with p1, p2, p3, p4:
        r1 = TC.get("/api/v1/students/me/results/summary")
    with p1, p2, p3, p4:
        r2 = TC.get("/api/v1/students/me/test-results/summary")
    assert r1.json()["summary"]["total_results"] == 1
    assert r2.json()["summary"]["total_results"] == 1
def test_4_other_student_404():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1 = patch.object(svc.academics_repo, "get_student_by_user_id",
                      return_value=_P())
    err = AppError("Result not found", status_code=404,
                   code="RESULT_NOT_FOUND")
    p2 = patch.object(svc.student_data_service, "get_own_result",
                      side_effect=err)
    with p1, p2:
        r = TC.get(f"/api/v1/students/me/results/{uuid4()}/detail")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "RESULT_NOT_FOUND"
def test_5_xtenant_403():
    app.dependency_overrides[get_current_user] = lambda: _U(tenant=TA)
    p1, p2, p3, p4 = _mk(_P(institution_id=TB), results=[_AR()])
    with p1, p2, p3, p4:
        r = TC.get("/api/v1/students/me/results/summary")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "TENANT_MISMATCH"
def test_6_result_id_manipulation():
    app.dependency_overrides[get_current_user] = lambda: _U()
    foreign = _AR(sid=OSID)
    foreign["student_result_items"] = []
    p1 = patch.object(svc.academics_repo, "get_student_by_user_id",
                      return_value=_P())
    p2 = patch.object(svc.student_data_service, "get_own_result",
                      return_value=foreign)
    with p1, p2:
        r = TC.get(f"/api/v1/students/me/results/{RID}/detail")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "RESULT_NOT_FOUND"

def test_7_student_id_inert():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2, p3, p4 = _mk(_P(), results=[_AR()])
    with p1, p2 as m2, p3, p4:
        r = TC.get("/api/v1/students/me/results/summary",
                   params={"student_id": OSID})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["summary"]["total_results"] == 1
        assert m2.call_args.args[0] == SUID
def test_8_email_inert():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2, p3, p4 = _mk(_P(), results=[_AR()])
    with p1, p2, p3, p4:
        r = TC.get("/api/v1/students/me/results/summary",
                   params={"email": "other@college.edu"})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["records"][0]["sgpa"] == 8.5
def test_9_register_inert():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2, p3, p4 = _mk(_P(), testrows=[_TR()])
    with p1, p2, p3, p4:
        r = TC.get("/api/v1/students/me/test-results/summary",
                   params={"register_number": "REG999"})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["summary"]["total_results"] == 1
def test_10_roll_inert():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2, p3, p4 = _mk(_P(), testrows=[_TR()])
    with p1, p2, p3, p4:
        r = TC.get("/api/v1/students/me/test-results/summary",
                   params={"university_roll_number": "ROLL999"})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["records"][0]["test_name"] == "Quiz 1"
def test_11_empty():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2, p3, p4 = _mk(_P(), results=[], testrows=[])
    with p1, p2, p3, p4:
        r1 = TC.get("/api/v1/students/me/results/summary")
    with p1, p2, p3, p4:
        r2 = TC.get("/api/v1/students/me/test-results/summary")
    assert r1.json()["records"] == []
    assert r1.json()["summary"]["records_available"] is False
    assert r1.json()["summary"]["total_results"] == 0
    assert r2.json()["records"] == []
    assert r2.json()["summary"]["records_available"] is False
def test_12_missing_data_safe():
    app.dependency_overrides[get_current_user] = lambda: _U()
    sparse = {"student_id": SID, "status": "published",
              "result_type": None, "sgpa": None}
    p1, p2, p3, p4 = _mk(_P(), results=[sparse],
        testrows=[{"student_id": SID, "status": "published"}])
    with p1, p2, p3, p4:
        r1 = TC.get("/api/v1/students/me/results/summary")
    with p1, p2, p3, p4:
        r2 = TC.get("/api/v1/students/me/test-results/summary")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["records"][0]["sgpa"] is None
    assert r2.json()["records"][0]["test_name"] is None
def test_13_legacy_unchanged():
    app.dependency_overrides[get_current_user] = lambda: _U()
    rows = [_AR()]
    db = MagicMock()
    (db.table.return_value.select.return_value.eq.return_value
     .maybe_single.return_value.execute).return_value = MagicMock(
        data=_P())
    with patch("app.services.student_data.get_admin_client",
               return_value=db):
        with patch("app.repositories.admin_academics.list_student_results",
                   return_value=rows):
            r = TC.get("/api/v1/students/me/results")
    assert r.status_code == 200
    assert r.json()[0]["student_id"] == SID
    trows = [_TR()]
    with patch("app.services.student_data.get_admin_client",
               return_value=db):
        with patch("app.repositories.admin_academics.list_test_results",
                   return_value=trows):
            r2 = TC.get("/api/v1/students/me/test-results")
    assert r2.status_code == 200
    assert r2.json()[0]["student_id"] == SID
def test_14_sig_and_filters():
    for fn in (svc.get_own_results, svc.get_own_test_results,
               svc.get_own_result):
        params = list(inspect.signature(fn).parameters)
        assert params[0] == "current_user"
        for bad in ("student_id", "user_id", "institution_id",
                    "email", "register_number",
                    "university_roll_number"):
            assert bad not in params
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2, p3, p4 = _mk(_P(), results=[])
    with p1, p2, p3, p4:
        r = TC.get("/api/v1/students/me/results/summary",
                   params={"academic_year_id": "bad-uuid"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] in ("INVALID_FILTER",
                                          "VALIDATION_ERROR")
def test_15_svc_guards():
    p1, p2, p3, p4 = _mk(_P(institution_id=TB), results=[])
    with p1, p2, p3, p4:
        with pytest.raises(AppError) as e:
            svc.get_own_results(_U(tenant=TA))
    assert e.value.code == "TENANT_MISMATCH"
    db = MagicMock()
    with patch.object(svc.academics_repo, "get_student_by_user_id",
                      return_value=None):
        with patch.object(svc, "get_admin_client", return_value=db):
            with pytest.raises(AppError) as e2:
                svc.get_own_test_results(_U())
    assert e2.value.code == "STUDENT_PROFILE_NOT_FOUND"

