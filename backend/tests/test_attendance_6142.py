"""Phase 6.14.2 - Attendance data integration (self-contained)."""
from unittest.mock import patch
from uuid import uuid4
import inspect
import pytest
from fastapi.testclient import TestClient
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services import student_attendance as svc
TC = TestClient(app, raise_server_exceptions=False)
TA = "a1111111-0000-0000-0000-000000000001"
TB = "b2222222-0000-0000-0000-000000000002"
SUID = "71000000-0000-0000-0000-000000000001"
OUID = "71000000-0000-0000-0000-000000000002"
SID = "30000000-0000-0000-0000-000000000151"
OSID = "30000000-0000-0000-0000-000000000152"
AY = "a0000000-0000-0000-0000-0000000000a1"
SEM = "a0000000-0000-0000-0000-0000000000b1"
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
def _R(sid=SID, status="present", date="2026-09-01", notes=None):
    return {"student_attendance_id": str(uuid4()), "student_id": sid,
            "institution_id": TA, "section_id": str(uuid4()),
            "academic_year_id": AY, "semester_id": SEM,
            "date": date, "status": status, "notes": notes,
            "created_at": "2026-09-01T00:00:00+00:00",
            "updated_at": "2026-09-01T00:00:00+00:00"}
@pytest.fixture(autouse=True)
def _cl():
    yield
    app.dependency_overrides.pop(get_current_user, None)
def _mk(profile, rows):
    p1 = patch.object(svc.academics_repo, "get_student_by_user_id",
                      return_value=profile)
    p2 = patch.object(svc.academics_repo, "list_student_attendance",
                      return_value=rows)
    return p1, p2
def test_1_own_attendance():
    app.dependency_overrides[get_current_user] = lambda: _U()
    rows = [_R(status="present"), _R(status="absent"),
            _R(status="late"), _R(status="excused")]
    p1, p2 = _mk(_P(), rows)
    with p1, p2:
        r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total_classes"] == 4
    assert body["summary"]["records_available"] is True
    assert len(body["records"]) == 4
    assert body["records"][0]["status"] == "present"
def test_2_belongs_to_auth_student():
    app.dependency_overrides[get_current_user] = lambda: _U()
    rows = [_R(sid=SID), _R(sid=OSID),
            {"student_id": SID, "date": "2026-09-02",
             "status": "present", "notes": None}]
    p1, p2 = _mk(_P(), rows)
    with p1 as m1, p2 as m2:
        r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 200
    assert m1.call_args.args[1] == SUID
    assert m2.call_args.args[1] == SID
    for rec in r.json()["records"]:
        assert "student_id" not in rec
        assert "student_attendance_id" not in rec
        assert "institution_id" not in rec
        assert "section_id" not in rec
    assert r.json()["summary"]["total_classes"] == 2
def test_3_unauth():
    r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTH_REQUIRED"
def test_4_other_token_cannot_access():
    app.dependency_overrides[get_current_user] = lambda: _U(OUID)
    p1, p2 = _mk(None, [])
    with p1 as lk, p2:
        r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"
    lk.assert_called_once()
    assert lk.call_args.args[1] == OUID
def test_5_xtenant_rejected():
    app.dependency_overrides[get_current_user] = lambda: _U(tenant=TA)
    p1, p2 = _mk(_P(institution_id=TB), [])
    with p1, p2:
        r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "TENANT_MISMATCH"
def test_6_client_student_id_cannot_override():
    app.dependency_overrides[get_current_user] = lambda: _U()
    rows = [_R(sid=SID)]
    p1, p2 = _mk(_P(), rows)
    with p1 as m1, p2 as m2:
        r = TC.get("/api/v1/students/me/attendance/summary",
                   params={"student_id": OSID})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert m1.call_args.args[1] == SUID
        assert m2.call_args.args[1] == SID
        assert r.json()["summary"]["total_classes"] == 1
def test_7_empty_attendance_ok():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2 = _mk(_P(), [])
    with p1, p2:
        r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["records"] == []
    assert body["summary"]["records_available"] is False
    assert body["summary"]["total_classes"] == 0
    assert body["summary"]["attendance_percentage"] is None
def test_8_percentage_rule():
    app.dependency_overrides[get_current_user] = lambda: _U()
    rows = [_R(status="present"), _R(status="present"),
            _R(status="present"), _R(status="absent")]
    p1, p2 = _mk(_P(), rows)
    with p1, p2:
        r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 200
    s = r.json()["summary"]
    assert s["present_classes"] == 3
    assert s["absent_classes"] == 1
    assert s["attendance_percentage"] == 75.0
def test_9_zero_total_no_division_error():
    p1, p2 = _mk(_P(), [])
    with p1, p2:
        out = svc.get_own_attendance(_U())
    assert out.summary.total_classes == 0
    assert out.summary.attendance_percentage is None
def test_9b_zero_total_api():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2 = _mk(_P(), [])
    with p1, p2:
        r = TC.get("/api/v1/students/me/attendance/summary")
    assert r.status_code == 200
    assert r.json()["summary"]["attendance_percentage"] is None
def test_10_invalid_filters_rejected():
    app.dependency_overrides[get_current_user] = lambda: _U()
    p1, p2 = _mk(_P(), [])
    with p1, p2:
        r1 = TC.get("/api/v1/students/me/attendance/summary",
                    params={"date_from": "not-a-date"})
    assert r1.status_code == 422
    assert r1.json()["error"]["code"] == "INVALID_FILTER"
    with p1, p2:
        r2 = TC.get("/api/v1/students/me/attendance/summary",
                    params={"academic_year_id": "bad-uuid"})
    assert r2.status_code == 422
def test_11_existing_attendance_unchanged():
    app.dependency_overrides[get_current_user] = lambda: _U()
    rows = [_R(sid=SID)]
    from unittest.mock import MagicMock
    db = MagicMock()
    (db.table.return_value.select.return_value.eq.return_value
     .maybe_single.return_value.execute).return_value = MagicMock(
         data=_P())
    with patch("app.services.student_data.get_admin_client",
               return_value=db):
        with patch("app.repositories.admin_academics.list_student_attendance",
                   return_value=rows):
            r = TC.get("/api/v1/students/me/attendance")
    assert r.status_code == 200
    assert r.json()[0]["student_id"] == SID
def test_12_sig_has_no_identity_params():
    params = list(inspect.signature(svc.get_own_attendance).parameters)
    assert params[0] == "current_user"
    assert "student_id" not in params
    assert "user_id" not in params
    assert "institution_id" not in params
    assert "email" not in params
def test_13_svc_xtenant_403():
    p1, p2 = _mk(_P(institution_id=TB), [])
    with p1, p2:
        with pytest.raises(AppError) as e:
            svc.get_own_attendance(_U(tenant=TA))
    assert e.value.code == "TENANT_MISMATCH"
def test_14_svc_noprofile_404():
    from unittest.mock import MagicMock
    db = MagicMock()
    with patch.object(svc.academics_repo, "get_student_by_user_id",
                      return_value=None):
        with patch.object(svc, "get_admin_client", return_value=db):
            with pytest.raises(AppError) as e:
                svc.get_own_attendance(_U())
    assert e.value.code == "STUDENT_PROFILE_NOT_FOUND"
