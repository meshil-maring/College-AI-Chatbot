"""Phase 6.14.5 — Personalized retrieval boundary (self-contained).

Covers the 24 required behaviours: authenticated student retrieval,
institution RAG retrieval, academic-context inclusion, empty-data safety
(no chunks / no attendance / no results / both empty), cross-institution and
cross-student denial, client identity-override rejection (student_id /
institution_id / organization_id), unauthorized-scope denial, inactive /
pending / rejected institution denial, private-knowledge exclusion,
other-student attendance/results exclusion, no-secrets guarantee, and the
Phase 6.14.2 / 6.14.3 / 6.14.4 / 6.13.7 / existing-retrieval regressions.

Hermetic like the previous phases: repositories are patched with
unittest.mock and the Supabase access is a fake in-memory client (same
pattern as the Phase 6.13.8 tests). No live Supabase, network, or generation
pipeline is touched.
"""
from contextlib import ExitStack
from unittest.mock import MagicMock, patch
from uuid import uuid4
import inspect

import pytest

from app.config import settings
from app.core.errors import AppError
from app.repositories import admin_academics as repo
from app.repositories import tenancy as tenancy_repo
from app.schemas.retrieval import RetrievalRequest
from app.services import personalized_retrieval as prsvc
from app.services import public_chat as public_chat_svc
from app.services import retrieval as retrieval_svc
from app.services import student_academic_context as ctxsvc
from app.services import student_academic_profile as psvc
from app.services import student_attendance as asvc
from app.services import student_results as rsvc

ORG_A = "11111111-0000-0000-0000-00000000000a"
ORG_B = "22222222-0000-0000-0000-00000000000b"
INST_A = "a1111111-0000-0000-0000-000000000001"
INST_B = "b2222222-0000-0000-0000-000000000002"
SUID = "71000000-0000-0000-0000-000000000001"
OUID = "71000000-0000-0000-0000-000000000002"
SID = "30000000-0000-0000-0000-000000000151"
OSID = "30000000-0000-0000-0000-000000000152"
AY = "a0000000-0000-0000-0000-0000000000a1"
SEM = "a0000000-0000-0000-0000-0000000000b1"
CID = "30000000-0000-0000-0000-0000000000c1"

KS_PUB_A = "c0000000-0000-0000-0000-00000000000a"   # published, own institution
KS_PRIV_A = "c0000000-0000-0000-0000-00000000000b"  # draft, own institution
KS_PUB_B = "c0000000-0000-0000-0000-00000000000c"   # published, other institution
RUN_A = "d0000000-0000-0000-0000-00000000000a"      # run of KS_PUB_A
RUN_PRIV = "d0000000-0000-0000-0000-00000000000b"   # run of KS_PRIV_A
RUN_B = "d0000000-0000-0000-0000-00000000000c"      # run of KS_PUB_B

QUERY = "What is the attendance requirement?"


def _U(uid=SUID, tenant=INST_A):
    """Authenticated current_user dict (as get_current_user would return)."""
    return {"user_id": uid, "auth_user_id": "a1", "email": "s@c.edu",
            "roles": ["student"], "institution_id": tenant}


def _P(**ov):
    """students row (as the repos would return it)."""
    r = {"student_id": SID, "user_id": SUID, "institution_id": INST_A,
         "student_number": "S100", "email": "s@c.edu",
         "register_number": "REG100", "university_roll_number": "ROLL100",
         "program_id": str(uuid4()), "academic_year_id": AY,
         "approval_status": "approved", "status": "active",
         "is_active": True}
    r.update(ov)
    return r


def _AT(sid=SID, status="present", date="2026-09-01"):
    return {"student_attendance_id": str(uuid4()), "student_id": sid,
            "institution_id": INST_A, "section_id": str(uuid4()),
            "academic_year_id": AY, "semester_id": SEM,
            "date": date, "status": status, "notes": None}


def _AR(sid=SID, status="published", sgpa=8.5, cgpa=8.2):
    return {"student_id": sid, "academic_year_id": AY, "semester_id": SEM,
            "program_id": str(uuid4()), "result_type": "semester",
            "total_credits_earned": 20, "total_credits_max": 22,
            "sgpa": sgpa, "cgpa": cgpa, "status": status,
            "issued_at": "2026-06-01T00:00:00+00:00", "institution_id": INST_A}


def _TR(sid=SID, status="published", name="Quiz 1"):
    return {"student_id": sid, "course_id": CID, "academic_year_id": AY,
            "semester_id": SEM, "test_name": name, "test_type": "quiz",
            "max_marks": 20, "scored_marks": 18, "percentage": 90.0,
            "letter_grade": "A", "conducted_at": "2026-09-01T00:00:00+00:00",
            "status": status}


class FakeTable:
    """Minimal Supabase table mock (same pattern as Phase 6.13.8 tests)."""

    def __init__(self, client, name):
        self._client = client
        self._table = name
        self._select_cols = None
        self._eq_cols = []
        self._eq_vals = []
        self._in_col = None
        self._in_vals = None
        self._maybe_single = False

    def select(self, cols):
        self._select_cols = [c.strip() for c in cols.split(",")]
        return self

    def eq(self, col, val):
        self._eq_cols.append(col)
        self._eq_vals.append(val)
        return self

    def in_(self, col, vals):
        self._in_col = col
        self._in_vals = vals
        return self

    def maybe_single(self):
        self._maybe_single = True
        return self

    def execute(self):
        rows = list(self._client.tables.get(self._table, []))
        for eq_col, eq_val in zip(self._eq_cols, self._eq_vals):
            rows = [r for r in rows if str(r.get(eq_col, "")) == str(eq_val)]
        if self._in_col is not None:
            vals = self._in_vals
            if isinstance(vals, str):
                vals = [vals]
            rows = [r for r in rows
                    if str(r.get(self._in_col, "")) in [str(v) for v in vals]]
        if self._select_cols:
            projected = []
            for r in rows:
                row_out = {}
                for col in self._select_cols:
                    if "(" in col:
                        base, inner = col.split("(", 1)
                        inner_col = inner.rstrip(")")
                        parent_val = r.get(base.strip())
                        if isinstance(parent_val, list):
                            embedded = [dict(pv) for pv in parent_val
                                        if isinstance(pv, dict) and dict(pv).get(inner_col)]
                            row_out[base.strip()] = embedded
                        elif isinstance(parent_val, dict):
                            row_out[base.strip()] = {inner_col: parent_val.get(inner_col)}
                        else:
                            row_out[base.strip()] = None
                    else:
                        row_out[col] = r.get(col)
                projected.append(row_out)
            result = projected if projected else None
        else:
            result = rows if rows else None
        if getattr(self, "_maybe_single", False):
            result = result[0] if result else None
        return MagicMock(data=result)


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = []
        return FakeTable(self, name)


def _inst_row(inst_id=INST_A, org=ORG_A, status="active", is_active=True):
    return {"institution_id": inst_id, "organization_id": org,
            "name": f"Inst {str(inst_id)[:4]}", "code": str(inst_id)[:6].upper(),
            "status": status, "is_active": is_active}


def _ks_row(ks_id, inst=INST_A, source_type="faq", lifecycle="published"):
    return {"knowledge_source_id": ks_id, "institution_id": inst,
            "source_type": source_type, "title": f"KS {str(ks_id)[:4]}",
            "description": None, "authority_level": "standard",
            "lifecycle_status": lifecycle, "effective_from": None,
            "effective_until": None, "created_at": None, "updated_at": None}


def _db(**ov):
    """Fake admin client with the standard two-institution world."""
    o = {"inst_a_status": "active", "inst_a_is_active": True}
    o.update(ov)
    fake = FakeClient()
    fake.tables["institutions"] = [
        _inst_row(INST_A, ORG_A, o["inst_a_status"], o["inst_a_is_active"]),
        _inst_row(INST_B, ORG_B),
    ]
    fake.tables["knowledge_sources"] = [
        _ks_row(KS_PUB_A, INST_A, "faq", "published"),
        _ks_row(KS_PRIV_A, INST_A, "faq", "draft"),
        _ks_row(KS_PUB_B, INST_B, "faq", "published"),
    ]
    fake.tables["document_processing_runs"] = [
        {"processing_run_id": RUN_A,
         "document_versions": [{"knowledge_source_id": KS_PUB_A}]},
        {"processing_run_id": RUN_PRIV,
         "document_versions": [{"knowledge_source_id": KS_PRIV_A}]},
        {"processing_run_id": RUN_B,
         "document_versions": [{"knowledge_source_id": KS_PUB_B}]},
    ]
    return fake


def _lookup_institution(fake, iid):
    for row in fake.tables.get("institutions", []):
        if str(row.get("institution_id")) == str(iid):
            return row
    return None


def _lookup_ks(fake, ksid):
    for row in fake.tables.get("knowledge_sources", []):
        if str(row.get("knowledge_source_id")) == str(ksid):
            return row
    return None


def _list_ks(fake, iid):
    return [row for row in fake.tables.get("knowledge_sources", [])
            if str(row.get("institution_id")) == str(iid)
            and row.get("lifecycle_status") == "published"]


def _chunk(run_id=RUN_A, cid=None):
    """RetrievedChunk provenance-tagged with a processing run."""
    return prsvc.RetrievedChunk(
        chunk_id=cid or uuid4(),
        text="The minimum attendance requirement is 75 percent.",
        similarity_score=0.9,
        metadata={"processing_run_id": run_id},
    )


def _retrieval(chunks):
    """Patch the EXISTING retrieval service's retrieve() used by the module."""
    response = retrieval_svc.RetrievalResponse(results=[
        retrieval_svc.RetrievalResult(
            chunk_id=c.chunk_id,
            text=c.text,
            similarity_score=c.similarity_score,
            metadata=dict(c.metadata),
        )
        for c in chunks
    ])
    return patch.object(prsvc, "retrieve", return_value=response)


def _std(att=None, ares=None, tres=None, prow=None):
    """Hermetic patch set covering every repo call the 6.14.4 resolver makes."""
    prow = prow if prow is not None else _P()
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
        patch.object(repo, "get_student_by_user_id", return_value=prow),
        patch.object(repo, "list_student_attendance",
                     return_value=att if att is not None else []),
        patch.object(rsvc.student_data_service, "get_own_results",
                     return_value=ares if ares is not None else []),
        patch.object(rsvc.student_data_service, "get_own_test_results",
                     return_value=tres if tres is not None else []),
        patch.object(psvc.personalization_repo, "get_course_labels",
                     return_value={}),
    ]


def _run(client=None, att=None, ares=None, tres=None, prow=None,
         chunks=None, current_user=None):
    """Run get_personalized_context hermetically; returns (result, mocks)."""
    fake = client if client is not None else _db()
    patches = []
    patches.extend(_std(att=att, ares=ares, tres=tres, prow=prow))
    # Entered AFTER _std so the fake-client lookups win over the _std row
    # patches for the same tenancy repo functions.
    patches.extend([
        patch.object(tenancy_repo, "get_institution_by_id",
                     side_effect=lambda db_, iid: _lookup_institution(fake, iid)),
        patch.object(tenancy_repo, "get_knowledge_source_by_id",
                     side_effect=lambda db_, ksid: _lookup_ks(fake, ksid)),
        patch.object(tenancy_repo,
                     "list_published_knowledge_sources_for_institution",
                     side_effect=lambda db_, iid: _list_ks(fake, iid)),
    ])
    if chunks is None:
        chunks = [_chunk()]
    patches.append(_retrieval(chunks))
    with ExitStack() as st:
        mocks = [st.enter_context(p) for p in patches]
        out = prsvc.get_personalized_context(
            current_user if current_user is not None else _U(),
            QUERY, client=fake)
    return out, mocks


def _run_raises(**kw):
    with pytest.raises(AppError) as ei:
        _run(**kw)
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


# ============================================================================
# Core behavior (tests 1-6)
# ============================================================================


def test_1_authenticated_student_retrieval_works():
    att = [_AT(status="present"), _AT(status="absent")]
    ctx, mocks = _run(att=att, ares=[_AR()], tres=[_TR()])
    assert ctx is not None
    assert ctx.knowledge.chunks[0].text.startswith("The minimum attendance")
    # The retrieval scope is the SERVER-RESOLVED own tenant.
    request = mocks[-1].call_args.args[0]
    assert request.institution_id is not None
    assert str(request.institution_id) == INST_A
    assert request.query == QUERY
    assert ctx.academic.student.student_number == "S100"


def test_2_institution_rag_retrieval_works():
    c1, c2 = _chunk(), _chunk(run_id=RUN_A)
    ctx, mocks = _run(chunks=[c1, c2])
    assert len(ctx.knowledge.chunks) == 2
    assert {c.chunk_id for c in ctx.knowledge.chunks} == {
        c1.chunk_id, c2.chunk_id}
    # The EXISTING Phase 3 retrieval service was used (not a second one).
    assert mocks[-1].call_args.args[0].institution_id is not None
    # The Phase 6.13.8 source-type whitelist is reused verbatim.
    assert prsvc.PUBLIC_SOURCE_TYPES == public_chat_svc.PUBLIC_SOURCE_TYPES


def test_3_student_academic_context_is_included():
    att = [_AT(status="present"), _AT(status="present"),
           _AT(status="present"), _AT(status="absent")]
    ctx, _ = _run(att=att, ares=[_AR()], tres=[_TR()])
    s = ctx.academic.attendance.summary
    assert s.total_classes == 4
    assert s.attendance_percentage == 75.0
    assert ctx.academic.results.summary.total_results == 1
    assert ctx.academic.results.test_summary.total_results == 1
    assert ctx.academic.student.register_number == "REG100"
    assert ctx.academic.institution.institution_code == "A11111"


def test_4_no_rag_results_returns_valid_context():
    ctx, _ = _run(chunks=[])
    assert ctx.knowledge.chunks == []
    assert ctx.academic.attendance.summary.records_available is False
    assert ctx.academic.results.summary.total_results == 0


def test_5_no_attendance_returns_valid_context():
    ctx, _ = _run(ares=[_AR()], tres=[_TR()])
    assert ctx.academic.attendance.summary.total_classes == 0
    assert ctx.academic.attendance.summary.attendance_percentage is None
    assert ctx.academic.attendance.records == []
    assert ctx.knowledge.chunks[0].chunk_id is not None
    assert ctx.academic.results.summary.total_results == 1


def test_6_no_results_returns_valid_context():
    ctx, _ = _run(att=[_AT()])
    assert ctx.academic.results.summary.records_available is False
    assert ctx.academic.results.summary.total_results == 0
    assert ctx.academic.results.records == []
    assert ctx.academic.results.test_records == []
    assert ctx.academic.attendance.summary.total_classes == 1


# ============================================================================
# Empty + boundary behavior (tests 7-12)
# ============================================================================


def test_7_both_empty_returns_valid_context():
    ctx, _ = _run(chunks=[])
    assert ctx.knowledge.chunks == []
    assert ctx.academic.attendance.records == []
    assert ctx.academic.results.records == []
    assert ctx.academic.results.test_records == []
    assert ctx.academic.student.student_number == "S100"


def test_8_cross_institution_rag_retrieval_denied():
    """Vector search is institution-scoped; tenant B rows cannot be asked for.

    The service derives the scope from the JWT tenant itself, so there is no
    parameter through which another institution's knowledge could be
    requested; the query is passed to retrieval verbatim with the resolved
    own-tenant scope only.
    """
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, institution_id=INST_B, client=_db())
    # And the scope that IS used is always the authenticated tenant.
    ctx, mocks = _run(chunks=[_chunk(run_id=RUN_B)])
    request = mocks[-1].call_args.args[0]
    assert str(request.institution_id) == INST_A
    # Defense in depth: even a wrongly-returned other-tenant chunk is
    # dropped by the provenance filter.
    assert ctx.knowledge.chunks == []


def test_9_cross_student_academic_data_denied():
    """No identity parameter exists; other students' rows are filtered."""
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, student_id=OSID, client=_db())
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, user_id=OUID, client=_db())
    att = [_AT(sid=OSID), _AT(), _AT(sid=OSID)]
    ares = [_AR(sid=OSID), _AR()]
    tres = [_TR(sid=OSID), _TR()]
    ctx, _ = _run(att=att, ares=ares, tres=tres)
    assert ctx.academic.attendance.summary.total_classes == 1
    assert ctx.academic.results.summary.total_results == 1
    assert ctx.academic.results.test_summary.total_results == 1


def test_10_client_student_id_override_denied():
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, student_id=OSID, client=_db())
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, **{"student_id": str(OSID)}, client=_db())


def test_11_client_institution_id_override_denied():
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, institution_id=INST_B, client=_db())
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, **{"institution_id": INST_B}, client=_db())
    ctx, mocks = _run(chunks=[_chunk(run_id=RUN_B)])
    assert str(mocks[-1].call_args.args[0].institution_id) == INST_A


def test_12_client_organization_id_override_denied():
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, organization_id=ORG_B, client=_db())
    with pytest.raises(TypeError):
        prsvc.get_personalized_context(
            _U(), QUERY, scope_id=ORG_B, client=_db())


def test_13_unauthorized_scope_denied():
    """A tampered students row (other tenant) fails closed, no context."""
    err = _run_raises(prow=_P(institution_id=INST_B))
    assert err.status_code == 403
    assert err.code == "TENANT_MISMATCH"


def test_14_inactive_institution_denied():
    err = _run_raises(client=_db(inst_a_status="suspended",
                                 inst_a_is_active=False))
    assert err.status_code == 403
    assert err.code == "TENANT_INACTIVE"


def test_15_pending_institution_denied():
    err = _run_raises(client=_db(inst_a_status="pending",
                                 inst_a_is_active=False))
    assert err.status_code == 403
    assert err.code == "TENANT_INACTIVE"


def test_16_rejected_institution_denied():
    err = _run_raises(client=_db(inst_a_status="rejected",
                                 inst_a_is_active=False))
    assert err.status_code == 403
    assert err.code == "TENANT_INACTIVE"


def test_17_private_unauthorized_knowledge_excluded():
    """Draft / private / other-institution chunks never enter the context."""
    # Only a private (draft) own-institution chunk exists.
    ctx, _ = _run(chunks=[_chunk(run_id=RUN_PRIV)])
    assert ctx.knowledge.chunks == []
    # A chunk with no resolvable provenance is dropped (fail closed).
    no_prov = prsvc.RetrievedChunk(
        chunk_id=uuid4(), text="orphan", similarity_score=0.5, metadata={})
    ctx2, _ = _run(chunks=[no_prov])
    assert ctx2.knowledge.chunks == []
    # Mixed: only the authorized published own-institution chunk survives.
    good, private, foreign = _chunk(), _chunk(run_id=RUN_PRIV), _chunk(run_id=RUN_B)
    ctx3, _ = _run(chunks=[good, private, foreign])
    assert [c.chunk_id for c in ctx3.knowledge.chunks] == [good.chunk_id]


def test_18_another_students_attendance_excluded():
    att = [_AT(sid=OSID), _AT(sid=OSID)]
    ctx, _ = _run(att=att, ares=[_AR()], tres=[_TR()])
    assert ctx.academic.attendance.summary.total_classes == 0
    assert ctx.academic.attendance.records == []
    assert ctx.academic.attendance.summary.attendance_percentage is None


def test_19_another_students_results_excluded():
    ctx, _ = _run(att=[_AT()], ares=[_AR(sid=OSID)], tres=[_TR(sid=OSID)])
    assert ctx.academic.results.summary.total_results == 0
    assert ctx.academic.results.records == []
    assert ctx.academic.results.test_summary.total_results == 0
    assert ctx.academic.results.test_records == []


# ============================================================================
# Secrets / contract / regression (tests 20-26)
# ============================================================================


def test_20_raw_secrets_excluded():
    att = [_AT()]
    ctx, _ = _run(att=att, ares=[_AR()], tres=[_TR()])
    keys = set(_keys(ctx.model_dump()))
    forbidden = ("password", "token", "secret", "credential", "api_key",
                 "auth_user_id", "email")
    for bad in forbidden:
        assert not any(bad in k for k in keys), bad
    # No student/internal-identity database identifiers anywhere in the
    # context tree (chunk metadata keeps only the existing Phase 4
    # retrieval-provenance fields; the knowledge block carries only the
    # student's OWN tenant label).
    for internal in ("student_id", "user_id", "organization_id",
                     "auth_user_id"):
        assert not any(k == internal for k in keys), internal
    # knowledge and academic stay distinct top-level sections.
    assert set(ctx.model_dump().keys()) == {"query", "knowledge", "academic"}


def test_21_phase_6142_regression():
    """Phase 6.14.2 attendance service still behaves exactly as before."""
    att = [_AT(status="present"), _AT(status="present"),
           _AT(status="present"), _AT(status="absent")]
    with ExitStack() as st:
        for p in [patch.object(repo, "get_student_by_user_id",
                               return_value=_P()),
                  patch.object(repo, "list_student_attendance",
                               return_value=att)]:
            st.enter_context(p)
        out = asvc.get_own_attendance(_U())
    assert out.summary.total_classes == 4
    assert out.summary.attendance_percentage == 75.0
    # tenant boundary unchanged
    with pytest.raises(AppError) as err:
        with ExitStack() as st:
            for p in [patch.object(repo, "get_student_by_user_id",
                                   return_value=_P(institution_id=INST_B)),
                      patch.object(repo, "list_student_attendance",
                                   return_value=[])]:
                st.enter_context(p)
            asvc.get_own_attendance(_U(tenant=INST_A))
    assert err.value.code == "TENANT_MISMATCH"


def test_22_phase_6143_regression():
    """Phase 6.14.3 results services still behave exactly as before."""
    with ExitStack() as st:
        for p in [patch.object(repo, "get_student_by_user_id",
                               return_value=_P()),
                  patch.object(rsvc.student_data_service, "get_own_results",
                               return_value=[_AR(status="published"),
                                             _AR(status="draft")]),
                  patch.object(rsvc.student_data_service,
                               "get_own_test_results",
                               return_value=[_TR(status="published"),
                                             _TR(status="draft")]),
                  patch.object(psvc.personalization_repo,
                               "get_course_labels", return_value={})]:
            st.enter_context(p)
        a = rsvc.get_own_results(_U())
        t = rsvc.get_own_test_results(_U())
    assert a.summary.total_results == 1
    assert a.records[0].sgpa == 8.5
    assert t.summary.total_results == 1
    assert t.records[0].test_name == "Quiz 1"
    # tenant boundary unchanged
    with pytest.raises(AppError) as err:
        with ExitStack() as st:
            st.enter_context(patch.object(
                repo, "get_student_by_user_id",
                return_value=_P(institution_id=INST_B)))
            rsvc.get_own_results(_U(tenant=INST_A))
    assert err.value.code == "TENANT_MISMATCH"


def test_23_phase_6144_regression():
    """Phase 6.14.4 resolver is unchanged AND is what the boundary uses."""
    # Signature unchanged: no identity parameter was added by this phase.
    params = list(inspect.signature(
        ctxsvc.get_student_academic_context).parameters)
    assert params[0] == "current_user"
    for bad in ("student_id", "user_id", "institution_id", "organization_id"):
        assert bad not in params
    # The same resolver output arrives inside the personalized context.
    att = [_AT()]
    ctx, mocks = _run(att=att, ares=[_AR()], tres=[_TR()])
    assert ctx.academic.student.student_number == "S100"
    assert ctx.academic.attendance.summary.total_classes == 1
    assert ctx.academic.results.summary.total_results == 1


def test_24_phase_6137_scope_regression():
    """The locked Phase 6.13.7 guard is unchanged and keeps its semantics."""
    from app.services import authorization as authz

    params = list(inspect.signature(
        authz.assert_active_tenant_context).parameters)
    assert params[0] == "db"
    # INSTITUTION scope on a pending institution still fails closed.
    ctx = {"scope_type": "institution", "scope_id": INST_A,
           "organization_id": ORG_A, "institution_id": INST_A}
    fake = _db(inst_a_status="pending", inst_a_is_active=False)
    with patch.object(authz.tenancy_repo, "get_institution_by_id",
                      side_effect=lambda db, iid: _lookup_institution(fake, iid)):
        with pytest.raises(AppError) as ei:
            authz.assert_active_tenant_context(fake, _U(), ctx)
    assert ei.value.code == "TENANT_INACTIVE"
    # ACTIVE institution still passes.
    fake2 = _db()
    with patch.object(authz.tenancy_repo, "get_institution_by_id",
                      side_effect=lambda db, iid: _lookup_institution(fake2, iid)):
        authz.assert_active_tenant_context(fake2, _U(), ctx)


def test_25_existing_retrieval_regression():
    """The Phase 3 retrieval service is untouched and still enforces scopes."""
    # RetrievalRequest still requires a scope filter.
    with pytest.raises(ValueError):
        RetrievalRequest(query="admissions")
    # Empty results remain valid.
    with patch.object(retrieval_svc, "embed_query",
                      return_value=[0.25] * 1536), \
         patch.object(retrieval_svc, "search_chunks", return_value=[]):
        request = RetrievalRequest(query="admissions", top_k=3,
                                   institution_id=INST_A)
        assert retrieval_svc.retrieve(request).results == []
    # The personalized boundary reuses it (patched through its own name).
    ctx, mocks = _run()
    assert mocks[-1].call_args.args[0].institution_id is not None


def test_26_query_wording_does_not_change_authorization():
    """No keyword-based security: wording only affects the retrieval query."""
    captured = {}

    def fake_retrieve(request, **kwargs):
        captured["query"] = request.query
        captured["institution_id"] = request.institution_id
        return retrieval_svc.RetrievalResponse(results=[])

    fake = _db()
    with ExitStack() as st:
        # _std first, then the fake-client tenancy lookups (entered last so
        # they win over the _std patches on the shared repo module).
        for p in _std():
            st.enter_context(p)
        for p in [patch.object(tenancy_repo, "get_institution_by_id",
                               side_effect=lambda db_, iid:
                               _lookup_institution(fake, iid)),
                  patch.object(tenancy_repo,
                               "list_published_knowledge_sources_for_institution",
                               side_effect=lambda db_, iid:
                               _list_ks(fake, iid))]:
            st.enter_context(p)
        st.enter_context(patch.object(prsvc, "retrieve",
                                      side_effect=fake_retrieve))
        ctx = prsvc.get_personalized_context(
            _U(), "What is my attendance?", client=fake)
    assert captured["query"] == "What is my attendance?"
    assert str(captured["institution_id"]) == INST_A
    # The academic context is always resolved, independent of wording.
    assert ctx.academic is not None
    assert ctx.knowledge.chunks == []







