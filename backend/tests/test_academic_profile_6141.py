"""Phase 6.14.1 - Student academic profile (self-contained)."""
from unittest.mock import MagicMock, patch
from uuid import uuid4
import inspect
import pytest
from fastapi.testclient import TestClient
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services import student_academic_profile as psvc
TC = TestClient(app, raise_server_exceptions=False)
TA = "a1111111-0000-0000-0000-000000000001"
TB = "b2222222-0000-0000-0000-000000000002"
SUID = "71000000-0000-0000-0000-000000000001"
OUID = "71000000-0000-0000-0000-000000000002"
PID = "50000000-0000-0000-0000-000000000001"
AYID = "50000000-0000-0000-0000-000000000002"
def _U(uid=SUID, tenant=TA):
    return {"user_id": uid, "auth_user_id": "a1",
            "email": "s@c.edu", "roles": ["student"],
            "institution_id": tenant}
def _R(**ov):
    r = {"student_id": str(uuid4()), "user_id": SUID,
         "institution_id": TA, "student_number": "STU100",
         "email": "s@c.edu", "register_number": "REG100",
         "university_roll_number": "ROLL100", "program_id": PID,
         "academic_year_id": AYID, "approval_status": "approved",
         "status": "active", "is_active": True}
    r.update(ov)
    return r
@pytest.fixture(autouse=True)
def _cl():
    yield
    app.dependency_overrides.pop(get_current_user, None)
def _mk(row, prog=None, year=None, sem=None, inst=None):
    p1 = patch.object(psvc.academics_repo,
                      "get_student_academic_profile_row", return_value=row)
    p2 = patch.object(psvc.personalization_repo, "get_program_label",
                      return_value=(prog if prog != "D" else None))
    p3 = patch.object(psvc.personalization_repo,
                      "get_academic_year_label",
                      return_value=(year if year != "D" else None))
    p4 = patch.object(psvc.personalization_repo,
                      "get_current_semester_label",
                      return_value=(sem if sem != "D" else None))
    p5 = patch.object(psvc.tenancy_repo, "get_institution_by_id",
                      return_value=inst)
    return p1, p2, p3, p4, p5
def _def(row):
    return ({"code": "CSE", "name": "B.Tech CSE"},
            {"code": "AY26", "name": "2026-27"},
            {"code": "S1", "name": "Sem 1"},
            {"institution_id": row["institution_id"],
             "name": "Test College", "code": "GIT"})
def test_1_own_profile():
    app.dependency_overrides[get_current_user] = lambda: _U()
    row = _R()
    a, b, c, d = _def(row)
    p = _mk(row, a, b, c, d)
    with p[0], p[1], p[2], p[3], p[4]:
        r = TC.get("/api/v1/students/me/academic-profile")
    assert r.status_code == 200
    assert r.json()["student_number"] == "STU100"
    assert r.json()["register_number"] == "REG100"
    assert r.json()["institution_code"] == "GIT"
    assert r.json()["program_name"] == "B.Tech CSE"
    assert r.json()["approval_status"] == "approved"
def test_2_no_ids():
    app.dependency_overrides[get_current_user] = lambda: _U()
    row = _R()
    a, b, c, d = _def(row)
    p = _mk(row, a, b, c, d)
    with p[0], p[1], p[2], p[3], p[4]:
        body = TC.get("/api/v1/students/me/academic-profile").json()
    for f in ("student_id", "user_id", "auth_user_id",
              "institution_id", "program_id", "academic_year_id"):
        assert f not in body
def test_3_unauth():
    r = TC.get("/api/v1/students/me/academic-profile")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTH_REQUIRED"
def test_4_other_token():
    app.dependency_overrides[get_current_user] = lambda: _U(OUID)
    db = MagicMock()
    with patch.object(psvc.academics_repo,
                      "get_student_academic_profile_row",
                      return_value=None) as lk:
        with patch.object(psvc, "get_admin_client", return_value=db):
            r = TC.get("/api/v1/students/me/academic-profile")
    assert r.status_code == 404
    lk.assert_called_once_with(db, OUID)
def test_5_xtenant():
    app.dependency_overrides[get_current_user] = lambda: _U(tenant=TA)
    row = _R(institution_id=TB)
    a, b, c, d = _def(row)
    p = _mk(row, a, b, c, d)
    with p[0], p[1], p[2], p[3], p[4]:
        r = TC.get("/api/v1/students/me/academic-profile")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "TENANT_MISMATCH"
def test_6_override():
    app.dependency_overrides[get_current_user] = lambda: _U()
    row = _R()
    a, b, c, d = _def(row)
    p = _mk(row, a, b, c, d)
    with p[0], p[1], p[2], p[3], p[4]:
        r = TC.get("/api/v1/students/me/academic-profile",
                   params={"student_id": str(uuid4())})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["student_number"] == "STU100"
def test_7_sig():
    assert list(inspect.signature(
        psvc.get_academic_profile).parameters) == ["current_user", "client"]
def test_8_svc_xtenant():
    row = _R(institution_id=TB)
    a, b, c, d = _def(row)
    p = _mk(row, a, b, c, d)
    with p[0], p[1], p[2], p[3], p[4]:
        with pytest.raises(AppError) as e:
            psvc.get_academic_profile(_U(tenant=TA))
    assert e.value.code == "TENANT_MISMATCH"
def test_9_svc_noprofile():
    db = MagicMock()
    with patch.object(psvc.academics_repo,
                      "get_student_academic_profile_row",
                      return_value=None):
        with patch.object(psvc, "get_admin_client", return_value=db):
            with pytest.raises(AppError) as e:
                psvc.get_academic_profile(_U())
    assert e.value.code == "STUDENT_PROFILE_NOT_FOUND"
