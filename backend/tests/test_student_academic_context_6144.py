"""Phase 6.14.4 — Student academic context resolver (self-contained).

Covers the 20 required behaviours: context resolution, JWT-only identity,
attendance/results inclusion, academic-year/semester filtering, empty-data
safety, cross-student / cross-institution denial, unpublished-result
exclusion, no internal ids/secrets, client-override impossibility, existing
service preservation, and Phase 6.14.2 / 6.14.3 regressions.

Hermetic like the previous phases: repository functions are patched with
unittest.mock; no live Supabase, network, or generation pipeline is touched.
"""
from contextlib import ExitStack
from unittest.mock import patch
from uuid import uuid4
import inspect

import pytest

from app.core.errors import AppError
from app.repositories import admin_academics as repo
from app.services import student_academic_context as ctxsvc
from app.services import student_academic_profile as psvc
from app.services import student_attendance as asvc
from app.services import student_results as rsvc

TA = "a1111111-0000-0000-0000-000000000001"
TB = "b2222222-0000-0000-0000-000000000002"
SUID = "71000000-0000-0000-0000-000000000001"
OUID = "71000000-0000-0000-0000-000000000002"
SID = "30000000-0000-0000-0000-000000000151"
OSID = "30000000-0000-0000-0000-000000000152"
AY = "a0000000-0000-0000-0000-0000000000a1"
SEM = "a0000000-0000-0000-0000-0000000000b1"
CID = "30000000-0000-0000-0000-0000000000c1"

IDENTITY_PARAMS = ("student_id", "user_id", "institution_id", "email",
                   "register_number", "university_roll_number")


def _U(uid=SUID, tenant=TA):
    """Authenticated current_user dict (as get_current_user would return)."""
    return {"user_id": uid, "auth_user_id": "a1", "email": "s@c.edu",
            "roles": ["student"], "institution_id": tenant}


def _P(**ov):
    """students row (as the repos would return it)."""
    r = {"student_id": SID, "user_id": SUID, "institution_id": TA,
         "student_number": "S100", "email": "s@c.edu",
         "register_number": "REG100", "university_roll_number": "ROLL100",
         "program_id": str(uuid4()), "academic_year_id": AY,
         "approval_status": "approved", "status": "active",
         "is_active": True}
    r.update(ov)
    return r


def _AT(sid=SID, status="present", date="2026-09-01"):
    """One stored student_attendance row (internal ids included)."""
    return {"student_attendance_id": str(uuid4()), "student_id": sid,
            "institution_id": TA, "section_id": str(uuid4()),
            "academic_year_id": AY, "semester_id": SEM,
            "date": date, "status": status, "notes": None}


def _AR(sid=SID, status="published", sgpa=8.5, cgpa=8.2):
    """One stored student_results (consolidated) row."""
    return {"student_id": sid, "academic_year_id": AY, "semester_id": SEM,
            "program_id": str(uuid4()), "result_type": "semester",
            "total_credits_earned": 20, "total_credits_max": 22,
            "sgpa": sgpa, "cgpa": cgpa, "status": status,
            "issued_at": "2026-06-01T00:00:00+00:00", "institution_id": TA}


def _TR(sid=SID, status="published", name="Quiz 1"):
    """One stored test_results row."""
    return {"student_id": sid, "course_id": CID, "academic_year_id": AY,
            "semester_id": SEM, "test_name": name, "test_type": "quiz",
            "max_marks": 20, "scored_marks": 18, "percentage": 90.0,
            "letter_grade": "A", "conducted_at": "2026-09-01T00:00:00+00:00",
            "status": status}


def _std(att=None, ares=None, tres=None, labels=None, prow=None, srow=None):
    """Hermetic patch set covering every repo call one resolver makes.

    prow: students row seen by the Phase 6.14.1 profile service.
    srow: students row seen by the attendance/results services
          (defaults to prow). Patches target the SHARED repository
          modules, so one set covers profile + attendance + results.
    """
    prow = prow if prow is not None else _P()
    srow = srow if srow is not None else prow
    return [
        patch.object(repo, "get_student_academic_profile_row",
                     return_value=prow),
        patch.object(psvc.personalization_repo, "get_program_label",
                     return_value={"code": "CSE", "name": "B.Tech CSE"}),
        patch.object(psvc.personalization_repo, "get_academic_year_label",
                     return_value={"code": "AY26", "name": "2026-27"}),
        patch.object(psvc.personalization_repo, "get_current_semester_label",
                     return_value={"code": "S1", "name": "Sem 1"}),
        patch.object(psvc.tenancy_repo, "get_institution_by_id",
                     return_value={"institution_id": prow["institution_id"],
                                   "name": "Test College", "code": "GIT"}),
        patch.object(repo, "get_student_by_user_id", return_value=srow),
        patch.object(repo, "list_student_attendance",
                     return_value=att if att is not None else []),
        patch.object(rsvc.student_data_service, "get_own_results",
                     return_value=ares if ares is not None else []),
        patch.object(rsvc.student_data_service, "get_own_test_results",
                     return_value=tres if tres is not None else []),
        patch.object(psvc.personalization_repo, "get_course_labels",
                     return_value=labels if labels is not None else {}),
    ]


def _run(patches, fn, *args, **kwargs):
    """Apply patches, call fn, return (result, active_mocks)."""
    with ExitStack() as st:
        mocks = [st.enter_context(p) for p in patches]
        out = fn(*args, **kwargs)
    return out, mocks


def _run_raises(patches, fn, *args, **kwargs):
    """Apply patches, call fn, return the raised AppError."""
    with ExitStack() as st:
        for p in patches:
            st.enter_context(p)
        with pytest.raises(AppError) as ei:
            fn(*args, **kwargs)
    return ei.value


def _keys(obj):
    """Recursively yield every mapping key in a dumped model."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_1_authenticated_context_resolves():
    att = [_AT(status="present"), _AT(status="absent")]
    ctx, _ = _run(_std(att=att, ares=[_AR()], tres=[_TR()]),
                  ctxsvc.get_student_academic_context, _U())
    assert ctx.student.student_number == "S100"
    assert ctx.student.register_number == "REG100"
    assert ctx.student.university_roll_number == "ROLL100"
    assert ctx.institution.institution_name == "Test College"
    assert ctx.institution.institution_code == "GIT"
    assert ctx.attendance.summary.total_classes == 2
    assert ctx.results.summary.total_results == 1
    assert ctx.results.test_summary.total_results == 1


def test_2_identity_comes_from_jwt():
    """user_id in the context (JWT sub) is the only identity source."""
    _, mocks = _run(_std(att=[_AT()], ares=[_AR()], tres=[_TR()]),
                    ctxsvc.get_student_academic_context, _U(OUID))
    # profile service looked up students by the JWT-derived user_id...
    assert mocks[0].call_args.args[1] == OUID
    # ...and so did the attendance and results services.
    assert mocks[5].call_args.args[1] == OUID
    assert mocks[5].call_count == 3  # attendance + academic + test results


def test_3_attendance_included():
    att = [_AT(status="present"), _AT(status="present"),
           _AT(status="absent"), _AT(status="late")]
    ctx, _ = _run(_std(att=att), ctxsvc.get_student_academic_context, _U())
    s = ctx.attendance.summary
    assert s.records_available is True
    assert (s.total_classes, s.present_classes, s.absent_classes,
            s.late_classes) == (4, 2, 1, 1)
    assert s.attendance_percentage == 50.0
    assert [r.status for r in ctx.attendance.records] == [
        "present", "present", "absent", "late"]


def test_4_results_included():
    labels = {CID: {"course_id": CID, "code": "CS101", "name": "Intro CS"}}
    ctx, _ = _run(_std(ares=[_AR()], tres=[_TR()], labels=labels),
                  ctxsvc.get_student_academic_context, _U())
    assert ctx.results.records[0].sgpa == 8.5
    assert ctx.results.records[0].cgpa == 8.2
    assert ctx.results.records[0].status == "published"
    tr = ctx.results.test_records[0]
    assert tr.test_name == "Quiz 1"
    assert tr.course_code == "CS101"
    assert tr.percentage == 90.0


def test_5_academic_year_filter_forwarded():
    ctx, mocks = _run(_std(att=[_AT()], ares=[_AR()], tres=[_TR()]),
                      ctxsvc.get_student_academic_context, _U(),
                      academic_year_id=AY)
    assert ctx is not None
    assert mocks[6].call_args.kwargs["academic_year_id"] == AY
    assert mocks[7].call_args.kwargs["academic_year_id"] == AY
    assert mocks[8].call_args.kwargs["academic_year_id"] == AY


def test_6_semester_filter_forwarded():
    ctx, mocks = _run(_std(att=[_AT()], ares=[_AR()], tres=[_TR()]),
                      ctxsvc.get_student_academic_context, _U(),
                      semester_id=SEM)
    assert ctx is not None
    assert mocks[6].call_args.kwargs["semester_id"] == SEM
    assert mocks[7].call_args.kwargs["semester_id"] == SEM
    assert mocks[8].call_args.kwargs["semester_id"] == SEM


def test_7_no_attendance():
    ctx, _ = _run(_std(ares=[_AR()], tres=[_TR()]),
                  ctxsvc.get_student_academic_context, _U())
    s = ctx.attendance.summary
    assert s.records_available is False
    assert s.total_classes == 0
    assert s.attendance_percentage is None
    assert ctx.attendance.records == []
    # results still present — not an authorization failure
    assert ctx.results.summary.total_results == 1


def test_8_no_results():
    ctx, _ = _run(_std(att=[_AT()]),
                  ctxsvc.get_student_academic_context, _U())
    assert ctx.results.summary.records_available is False
    assert ctx.results.summary.total_results == 0
    assert ctx.results.records == []
    assert ctx.results.test_summary.records_available is False
    assert ctx.results.test_records == []
    assert ctx.attendance.summary.total_classes == 1


def test_9_neither_attendance_nor_results():
    ctx, _ = _run(_std(), ctxsvc.get_student_academic_context, _U())
    assert ctx.attendance.records == []
    assert ctx.attendance.summary.total_classes == 0
    assert ctx.attendance.summary.attendance_percentage is None
    assert ctx.results.records == []
    assert ctx.results.test_records == []
    assert ctx.results.summary.total_results == 0
    assert ctx.results.test_summary.total_results == 0
    assert ctx.student.register_number == "REG100"


def test_10_cross_student_access_denied():
    """No identity parameter exists; other students' rows are filtered."""
    with pytest.raises(TypeError):
        ctxsvc.get_student_academic_context(_U(), student_id=OSID)
    att = [_AT(sid=OSID), _AT(), _AT(sid=OSID)]
    ares = [_AR(sid=OSID), _AR()]
    tres = [_TR(sid=OSID), _TR()]
    ctx, _ = _run(_std(att=att, ares=ares, tres=tres),
                  ctxsvc.get_student_academic_context, _U())
    assert len(ctx.attendance.records) == 1
    assert len(ctx.results.records) == 1
    assert len(ctx.results.test_records) == 1


def test_11_cross_institution_access_denied():
    """students row of another institution -> fail-closed 403, no context."""
    err = _run_raises(_std(prow=_P(institution_id=TB)),
                      ctxsvc.get_student_academic_context, _U(tenant=TA))
    assert err.code == "TENANT_MISMATCH"


def test_12_institution_mismatch_denied():
    """Profile row matches the tenant, but the attendance/results services
    resolve a row of another institution: the denial propagates and the
    resolver never bypasses it."""
    err = _run_raises(_std(srow=_P(institution_id=TB)),
                      ctxsvc.get_student_academic_context, _U(tenant=TA))
    assert err.code == "TENANT_MISMATCH"


def test_13_unpublished_results_excluded():
    ares = [_AR(status="published"), _AR(status="draft"),
            _AR(status="withheld")]
    tres = [_TR(status="published"), _TR(status="draft")]
    ctx, _ = _run(_std(ares=ares, tres=tres),
                  ctxsvc.get_student_academic_context, _U())
    assert ctx.results.summary.total_results == 1
    assert [r.status for r in ctx.results.records] == ["published"]
    assert ctx.results.test_summary.total_results == 1
    assert [r.test_name for r in ctx.results.test_records] == ["Quiz 1"]


def test_14_no_internal_ids_or_secrets_exposed():
    labels = {CID: {"course_id": CID, "code": "CS101", "name": "Intro CS"}}
    ctx, _ = _run(_std(att=[_AT()], ares=[_AR()], tres=[_TR()],
                       labels=labels),
                  ctxsvc.get_student_academic_context, _U())
    all_keys = set(_keys(ctx.model_dump()))
    for bad in ("student_id", "user_id", "auth_user_id", "institution_id",
                "program_id", "academic_year_id", "semester_id",
                "section_id", "course_id", "student_attendance_id",
                "student_result_id", "test_result_id", "password",
                "password_hash", "secret", "token", "email"):
        assert bad not in all_keys, bad


def test_15_client_student_id_cannot_override_identity():
    params = list(inspect.signature(
        ctxsvc.get_student_academic_context).parameters)
    for bad in IDENTITY_PARAMS:
        assert bad not in params
    with pytest.raises(TypeError):
        ctxsvc.get_student_academic_context(_U(), student_id=OSID)
    # even with other students' rows in the pool, only the JWT student's
    # rows are projected and the lookup uses the JWT-derived user_id
    ctx, mocks = _run(_std(att=[_AT(sid=OSID), _AT()],
                           ares=[_AR(sid=OSID), _AR()],
                           tres=[_TR(sid=OSID), _TR()]),
                      ctxsvc.get_student_academic_context, _U())
    assert len(ctx.attendance.records) == 1
    assert len(ctx.results.records) == 1
    assert len(ctx.results.test_records) == 1
    assert mocks[5].call_args.args[1] == SUID


def test_16_client_institution_id_cannot_override_identity():
    params = list(inspect.signature(
        ctxsvc.get_student_academic_context).parameters)
    assert "institution_id" not in params
    with pytest.raises(TypeError):
        ctxsvc.get_student_academic_context(_U(), institution_id=TB)
    # institution labels are server-resolved; a stale cross-tenant row is
    # rejected before any label is produced
    err = _run_raises(_std(prow=_P(institution_id=TB)),
                      ctxsvc.get_student_academic_context, _U(tenant=TA))
    assert err.code == "TENANT_MISMATCH"


def _isolate_delegation():
    """Patch the three existing services so delegation can be observed."""
    return (
        patch.object(psvc, "get_academic_profile",
                     return_value=psvc.StudentAcademicProfile()),
        patch.object(asvc, "get_own_attendance",
                     return_value=asvc.StudentOwnAttendance()),
        patch.object(rsvc, "get_own_results",
                     return_value=rsvc.StudentOwnResults()),
        patch.object(rsvc, "get_own_test_results",
                     return_value=rsvc.StudentOwnTestResults()),
    )


def test_17_existing_attendance_service_unchanged_and_used():
    params = list(inspect.signature(asvc.get_own_attendance).parameters)
    assert params[0] == "current_user"
    for bad in IDENTITY_PARAMS:
        assert bad not in params
    with ExitStack() as st:
        mp, ma, _, _ = (st.enter_context(p) for p in _isolate_delegation())
        ctxsvc.get_student_academic_context(
            _U(), academic_year_id=AY, semester_id=SEM,
            date_from="2026-09-01", date_to="2026-09-30",
            attendance_limit=7)
    ma.assert_called_once()
    assert ma.call_args.args[0] == _U()
    k = ma.call_args.kwargs
    assert k["academic_year_id"] == AY
    assert k["semester_id"] == SEM
    assert k["date_from"] == "2026-09-01"
    assert k["date_to"] == "2026-09-30"
    assert k["limit"] == 7
    mp.assert_called_once()


def test_18_existing_results_services_unchanged_and_used():
    for fn in (rsvc.get_own_results, rsvc.get_own_test_results):
        params = list(inspect.signature(fn).parameters)
        assert params[0] == "current_user"
        for bad in IDENTITY_PARAMS:
            assert bad not in params
    with ExitStack() as st:
        _, _, mr, mt = (st.enter_context(p) for p in _isolate_delegation())
        ctxsvc.get_student_academic_context(
            _U(), academic_year_id=AY, semester_id=SEM,
            test_results_limit=3)
    mr.assert_called_once()
    assert mr.call_args.kwargs["academic_year_id"] == AY
    assert mr.call_args.kwargs["semester_id"] == SEM
    mt.assert_called_once()
    assert mt.call_args.kwargs["academic_year_id"] == AY
    assert mt.call_args.kwargs["limit"] == 3


def test_19_phase_6142_regression():
    """Phase 6.14.2 attendance service still behaves exactly as before."""
    att = [_AT(status="present"), _AT(status="present"),
           _AT(status="present"), _AT(status="absent")]
    p = [patch.object(repo, "get_student_by_user_id", return_value=_P()),
         patch.object(repo, "list_student_attendance", return_value=att)]
    out, _ = _run(p, asvc.get_own_attendance, _U())
    assert out.summary.total_classes == 4
    assert out.summary.attendance_percentage == 75.0
    assert out.records[0].status == "present"
    # empty-data rule unchanged
    out2, _ = _run(
        [patch.object(repo, "get_student_by_user_id", return_value=_P()),
         patch.object(repo, "list_student_attendance", return_value=[])],
        asvc.get_own_attendance, _U())
    assert out2.summary.attendance_percentage is None
    # tenant boundary unchanged
    err = _run_raises(
        [patch.object(repo, "get_student_by_user_id",
                      return_value=_P(institution_id=TB)),
         patch.object(repo, "list_student_attendance", return_value=[])],
        asvc.get_own_attendance, _U(tenant=TA))
    assert err.code == "TENANT_MISMATCH"


def test_20_phase_6143_regression():
    """Phase 6.14.3 results services still behave exactly as before."""
    p = [patch.object(repo, "get_student_by_user_id", return_value=_P()),
         patch.object(rsvc.student_data_service, "get_own_results",
                      return_value=[_AR(status="published"),
                                    _AR(status="draft")]),
         patch.object(rsvc.student_data_service, "get_own_test_results",
                      return_value=[_TR(status="published"),
                                    _TR(status="draft")]),
         patch.object(psvc.personalization_repo, "get_course_labels",
                      return_value={})]
    with ExitStack() as st:
        for pp in p:
            st.enter_context(pp)
        a = rsvc.get_own_results(_U())
        t = rsvc.get_own_test_results(_U())
    assert a.summary.total_results == 1
    assert a.records[0].status == "published"
    assert a.records[0].sgpa == 8.5
    assert t.summary.total_results == 1
    assert t.records[0].test_name == "Quiz 1"
    # tenant boundary unchanged
    err = _run_raises(
        [patch.object(repo, "get_student_by_user_id",
                      return_value=_P(institution_id=TB))],
        rsvc.get_own_results, _U(tenant=TA))
    assert err.code == "TENANT_MISMATCH"
