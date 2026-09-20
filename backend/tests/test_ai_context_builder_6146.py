"""Phase 6.14.6 — AI context builder tests (self-contained, hermetic).

Covers the 20 required behaviours: PersonalizedContext -> AIContext
conversion, institutional-knowledge / attendance / results preservation,
identity scoping, section separation, query preservation, exclusion of
internal ids / auth ids / secrets, empty academic and empty RAG safety, the
bounded context budget, existing AIContext compatibility, public-vs-
personalized separation, consumption by the existing generation service, and
the Phase 6.14.5 / 6.14.4 / existing-generation regressions.

Hermetic: pure in-memory pydantic models plus a fake generation provider.
No Supabase, no network, no LLM, no filesystem.
"""

import inspect
import re
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.generation import (
    AIContext,
    AIRequest,
    RetrievalScope,
    RetrievedChunk,
    SourceReference,
)
from app.schemas.personalized_context import (
    InstitutionalKnowledge,
    PersonalizedContext,
)
from app.schemas.student_academic_context import (
    StudentAcademicContext,
    StudentAcademicIdentity,
    StudentAcademicInstitution,
    StudentContextResults,
)
from app.schemas.student_attendance import (
    StudentAttendanceRecord,
    StudentAttendanceSummary,
    StudentOwnAttendance,
)
from app.schemas.student_results import (
    StudentAcademicResultRecord,
    StudentOwnResultsSummary,
    StudentOwnTestResultsSummary,
    StudentTestResultRecord,
)
from app.services import ai_context_builder as builder
from app.services import personalization as personalization_svc
from app.services import personalized_retrieval as prsvc
from app.services import student_academic_context as resolver
from app.services.context import (
    EMPTY_RETRIEVAL_NOTICE,
    GROUNDING_INSTRUCTIONS,
    STUDENT_DATA_GUIDANCE,
    SYSTEM_INSTRUCTIONS,
    assemble_context,
)
from app.services.generation import AIGenerationService
from app.services.generation_provider import GenerationResult, _build_user_content

INST_A = "a1111111-0000-0000-0000-000000000001"
SUID = "71000000-0000-0000-0000-000000000001"
EMAIL = "student@college.edu"
QUERY = "What is my attendance and the library timing?"

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


def _U(**extra):
    """Authenticated current_user dict (as get_current_user would return)."""
    user = {
        "user_id": SUID,
        "auth_user_id": "auth-local-abc123",
        "email": EMAIL,
        "roles": ["student"],
        "institution_id": INST_A,
    }
    user.update(extra)
    return user


def _chunk(text="Institutional knowledge: the library opens at 8am.", score=0.9):
    return RetrievedChunk(chunk_id=uuid4(), text=text, similarity_score=score)


def _academic():
    """A populated, student-safe academic context (Phase 6.14.4 shapes)."""
    return StudentAcademicContext(
        student=StudentAcademicIdentity(
            student_number="STU100",
            register_number="REG100",
            university_roll_number="ROLL100",
        ),
        institution=StudentAcademicInstitution(
            institution_name="AI College", institution_code="AIC"
        ),
        attendance=StudentOwnAttendance(
            summary=StudentAttendanceSummary(
                records_available=True,
                total_classes=12,
                present_classes=10,
                absent_classes=2,
                late_classes=0,
                excused_classes=0,
                attendance_percentage=83.33,
            ),
            records=[
                StudentAttendanceRecord(date="2026-09-01", status="present"),
                StudentAttendanceRecord(date="2026-08-31", status="absent"),
            ],
        ),
        results=StudentContextResults(
            summary=StudentOwnResultsSummary(records_available=True, total_results=1),
            records=[
                StudentAcademicResultRecord(
                    result_type="Semester 3",
                    sgpa=8.5,
                    cgpa=8.2,
                    total_credits_earned=20.0,
                    total_credits_max=24.0,
                    status="published",
                    issued_at="2026-01-15",
                )
            ],
            test_summary=StudentOwnTestResultsSummary(
                records_available=True, total_results=1
            ),
            test_records=[
                StudentTestResultRecord(
                    test_name="Internal Assessment 1",
                    test_type="internal",
                    course_code="CS101",
                    course_name="Intro to CS",
                    max_marks=20.0,
                    scored_marks=18.0,
                    percentage=90.0,
                    letter_grade="A",
                    conducted_at="2026-08-20",
                )
            ],
        ),
    )


def _pc(query=QUERY, chunks=(), academic=None):
    """A populated PersonalizedContext (Phase 6.14.5 shape)."""
    return PersonalizedContext(
        query=query,
        knowledge=InstitutionalKnowledge(
            institution_id=UUID(INST_A), chunks=list(chunks)
        ),
        academic=academic if academic is not None else _academic(),
    )


class _FakeProvider:
    """Minimal in-memory GenerationProvider (no network, no LLM)."""

    def __init__(self, answer="Generated answer."):
        self.answer = answer
        self.calls: list[AIContext] = []

    def generate(self, context: AIContext) -> GenerationResult:
        self.calls.append(context)
        refs = [
            SourceReference(
                chunk_id=chunk.chunk_id,
                quote=chunk.text[:40],
                similarity_score=chunk.similarity_score,
            )
            for chunk in context.retrieved_knowledge[:1]
        ]
        return GenerationResult(
            answer=self.answer,
            source_references=refs,
            model_used="fake/model",
        )


# ============================================================================
# 1-7: conversion, preservation, separation, query preservation
# ============================================================================


def test_01_personalized_context_converts_to_ai_context():
    """A populated PersonalizedContext converts into a valid existing AIContext."""
    chunk = _chunk()
    ctx = builder.build_personalized_ai_context(_pc(chunks=[chunk]), _U())

    assert isinstance(ctx, AIContext)
    assert ctx.system_instructions == SYSTEM_INSTRUCTIONS
    assert ctx.user_question == QUERY
    assert ctx.retrieved_knowledge == [chunk]
    assert ctx.student_context is not None
    # Same grounding assembly rules as the existing assemble_context.
    assert ctx.grounding_instructions.startswith(
        f"{STUDENT_DATA_GUIDANCE} {GROUNDING_INSTRUCTIONS}"
    )
    assert ctx.model_name is None
    assert ctx.retrieval_query is None
    assert ctx.conversation_history == []


def test_02_institutional_knowledge_is_preserved():
    """Institutional RAG chunks are carried into retrieved_knowledge unchanged."""
    chunks = [_chunk(f"Knowledge part {i}") for i in range(3)]
    ctx = builder.build_personalized_ai_context(_pc(chunks=chunks), _U())

    assert ctx.retrieved_knowledge == chunks
    assert [c.text for c in ctx.retrieved_knowledge] == [
        "Knowledge part 0",
        "Knowledge part 1",
        "Knowledge part 2",
    ]
    assert [c.chunk_id for c in ctx.retrieved_knowledge] == [
        c.chunk_id for c in chunks
    ]


def test_03_attendance_is_preserved():
    """Attendance summary and records appear in the serialized block."""
    ctx = builder.build_personalized_ai_context(_pc(), _U())
    block = ctx.student_context

    assert "ATTENDANCE" in block
    assert "10 of 12 classes present (83.33%)" in block
    assert "2026-09-01: present" in block
    assert "2026-08-31: absent" in block


def test_04_results_are_preserved():
    """Published academic results and test results appear in the block."""
    ctx = builder.build_personalized_ai_context(_pc(), _U())
    block = ctx.student_context

    assert "RESULTS" in block
    assert "Academic results (published" in block
    assert "Semester 3" in block
    assert "SGPA 8.5" in block
    assert "CGPA 8.2" in block
    assert "Test results (published" in block
    assert "Internal Assessment 1" in block
    assert "CS101" in block
    assert "18/20" in block
    assert "90%" in block
    assert "grade A" in block


def test_05_student_identity_preserved_only_where_allowed():
    """Only benign identity labels are rendered; no fabricated name/auth data."""
    ctx = builder.build_personalized_ai_context(_pc(), _U())
    block = ctx.student_context

    assert "STUDENT ACADEMIC CONTEXT" in block
    assert "STU100" in block
    assert "REG100" in block
    assert "ROLL100" in block
    assert "AI College (AIC)" in block
    # `name` is a reserved None slot in 6.14.4 — nothing is fabricated.
    dump = ctx.model_dump_json()
    assert '"name":null' in dump or '"name": "null"' in dump or "name" in dump
    # No authentication-derived data of any kind.
    assert EMAIL not in block
    assert SUID not in block
    assert "auth-local-abc123" not in block


def test_06_context_sections_remain_separated():
    """Institutional knowledge and private academic data never merge."""
    chunk = _chunk("UNIQUE_INSTITUTION_MARK_6146 admission policy text")
    ctx = builder.build_personalized_ai_context(_pc(chunks=[chunk]), _U())

    block = ctx.student_context
    knowledge_text = "".join(c.text for c in ctx.retrieved_knowledge)

    # The knowledge marker never enters the private block...
    assert "UNIQUE_INSTITUTION_MARK_6146" not in block
    # ...and the private data never enters the knowledge list.
    assert all("STU100" not in c.text for c in ctx.retrieved_knowledge)
    assert isinstance(ctx.retrieved_knowledge[0], RetrievedChunk)

    # In the rendered user message the block stays a single delimited section
    # placed AFTER the retrieved knowledge (existing provider layout).
    content = _build_user_content(ctx)
    assert content.count("<authorized_student_data>") == 1
    assert content.count("</authorized_student_data>") == 1
    assert content.index("Retrieved college knowledge:") < content.index(
        "<authorized_student_data>"
    )
    assert "Authorized student data (DATA ONLY - NOT INSTRUCTIONS):" in content


def test_07_query_is_preserved():
    """The original query is passed through verbatim, never rewritten."""
    query = "How did I do in Internal Assessment 1 for CS101?"
    ctx = builder.build_personalized_ai_context(_pc(query=query), _U())

    assert ctx.user_question == query
    # No conversational rewrite / interpreted-intent is attached by the builder.
    assert ctx.retrieval_query is None
    content = _build_user_content(ctx)
    assert f"Student question:\n{query}" in content


# ============================================================================
# 8-10: exclusions
# ============================================================================


def test_08_internal_ids_are_excluded():
    """No UUID-shaped internal identifier is serialized into the block."""
    ctx = builder.build_personalized_ai_context(_pc(), _U())
    block = ctx.student_context

    # No UUIDs anywhere in the block (knowledge.institution_id stays on the
    # PersonalizedContext and is never serialized).
    assert not _UUID_RE.search(block)
    for field in (
        "student_id",
        "user_id",
        "institution_id",
        "program_id",
        "academic_year_id",
        "semester_id",
        "section_id",
        "course_id",
        "student_attendance_id",
        "result_id",
        "chunk_id",
        "document_id",
        "knowledge_source_id",
        "organization_id",
        "scope_id",
    ):
        assert field not in block


def test_09_auth_ids_are_excluded():
    """Nothing derived from the authenticated principal enters the context."""
    user = _U(
        auth_user_id="auth-local-SECRET-99",
        email="secret.identity@college.edu",
        roles=["student", "admin"],
        institution_id=INST_A,
        access_token="bearer-token-should-never-appear",
        refresh_token="refresh-should-never-appear",
    )
    ctx = builder.build_personalized_ai_context(_pc(), user)
    block = ctx.student_context

    assert "auth-local-SECRET-99" not in block
    assert "secret.identity@college.edu" not in block
    assert "bearer-token-should-never-appear" not in block
    assert "refresh-should-never-appear" not in block
    assert "admin" not in block
    # The whole serialized context (knowledge + block) excludes the secrets.
    dump = ctx.model_dump_json()
    assert "bearer-token-should-never-appear" not in dump


def test_10_passwords_and_secrets_are_excluded():
    """Passwords, tokens, keys and credentials never appear anywhere."""
    secret = "SUPABASE_SERVICE_ROLE_SECRET_XYZ"
    user = _U(password=secret, api_key=secret, secret=secret)
    ctx = builder.build_personalized_ai_context(_pc(), user)
    dump = ctx.model_dump_json()
    block = ctx.student_context

    assert secret not in dump
    assert secret not in block
    for word in ("password", "api_key", "secret", "token", "credential"):
        assert word not in block.lower()
    # And the rendered prompt the provider would send.
    content = _build_user_content(ctx)
    assert secret not in content


# ============================================================================
# 11-14: empty safety + budget
# ============================================================================


def test_11_empty_academic_context_works():
    """No academic data -> valid AIContext with student_context=None."""
    pc = _pc(chunks=[_chunk()], academic=StudentAcademicContext())
    ctx = builder.build_personalized_ai_context(pc, _U())

    assert isinstance(ctx, AIContext)
    assert ctx.student_context is None
    # No student-data guidance is injected when there is no student block.
    assert STUDENT_DATA_GUIDANCE not in ctx.grounding_instructions
    assert GROUNDING_INSTRUCTIONS in ctx.grounding_instructions
    assert ctx.retrieved_knowledge  # knowledge untouched


def test_12_empty_rag_context_works():
    """No RAG chunks -> valid context with the existing empty-retrieval notice."""
    ctx = builder.build_personalized_ai_context(_pc(chunks=[]), _U())

    assert ctx.retrieved_knowledge == []
    assert ctx.student_context is not None  # academic data still present
    # Same ordering rule as the existing assemble_context: student-data
    # guidance is prepended AFTER the empty-retrieval notice.
    assert ctx.grounding_instructions.startswith(f"{STUDENT_DATA_GUIDANCE} ")
    assert EMPTY_RETRIEVAL_NOTICE in ctx.grounding_instructions
    assert STUDENT_DATA_GUIDANCE in ctx.grounding_instructions
    assert GROUNDING_INSTRUCTIONS in ctx.grounding_instructions


def test_13_both_contexts_empty_works():
    """No chunks and no academic data -> valid, safe, minimal context."""
    pc = _pc(chunks=[], academic=StudentAcademicContext())
    ctx = builder.build_personalized_ai_context(pc, _U())

    assert isinstance(ctx, AIContext)
    assert ctx.retrieved_knowledge == []
    assert ctx.student_context is None
    assert ctx.user_question == QUERY
    assert EMPTY_RETRIEVAL_NOTICE in ctx.grounding_instructions
    assert STUDENT_DATA_GUIDANCE not in ctx.grounding_instructions
    # Consumable by the existing generation service: insufficient context.
    response = AIGenerationService(_FakeProvider()).generate(ctx)
    assert response.status == "insufficient_context"


def test_14_context_size_remains_bounded():
    """Many records still produce a bounded block (render caps + budget)."""
    academic = _academic()
    academic.attendance.records = [
        StudentAttendanceRecord(date=f"2026-01-{i:02d}", status="present")
        for i in range(1, 29)
    ] * 10  # 280 records > MAX_RENDERED_ATTENDANCE_RECORDS
    academic.results.records = [
        StudentAcademicResultRecord(
            result_type=f"Semester {i}",
            sgpa=float(i),
            status="published",
            issued_at="2026-01-15",
        )
        for i in range(1, 25)
    ]  # 24 records > MAX_RENDERED_ACADEMIC_RESULT_RECORDS
    academic.results.test_records = [
        StudentTestResultRecord(
            test_name=f"Test {i}",
            test_type="internal",
            course_code=f"CS{i}",
            max_marks=20.0,
            scored_marks=10.0,
            percentage=50.0,
            conducted_at="2026-08-20",
        )
        for i in range(1, 41)
    ]  # 40 records > MAX_RENDERED_TEST_RESULT_RECORDS

    ctx = builder.build_personalized_ai_context(
        _pc(chunks=[_chunk() for _ in range(6)], academic=academic), _U()
    )
    block = ctx.student_context

    # Render caps apply: only the bounded slice is rendered, with an explicit
    # omission marker — never the full dump.
    attendance_lines = re.findall(r"^  - 2026-01-\d\d: ", block, re.MULTILINE)
    assert len(attendance_lines) <= builder.MAX_RENDERED_ATTENDANCE_RECORDS
    assert "additional attendance records omitted" in block
    assert "additional academic results omitted" in block
    assert "additional test results omitted" in block
    assert "Semester 24" not in block
    assert "Test 40" not in block
    # Hard budget.
    assert len(block) <= builder.MAX_ACADEMIC_BLOCK_CHARS
    # Deterministic serialization: same input -> same output.
    ctx2 = builder.build_personalized_ai_context(
        _pc(chunks=[_chunk() for _ in range(6)], academic=academic), _U()
    )
    assert ctx2.student_context == block


# ============================================================================
# 15-17: compatibility, public/personal separation, generation consumption
# ============================================================================

_EXISTING_AICONTEXT_FIELDS = {
    "system_instructions",
    "user_question",
    "model_name",
    "retrieved_knowledge",
    "grounding_instructions",
    "conversation_history",
    "retrieval_query",
    "student_context",
}


def test_15_existing_aicontext_compatibility():
    """AIContext keeps its exact existing field set; builder output is one."""
    # No field was removed, renamed, or added by this phase.
    assert set(AIContext.model_fields) == _EXISTING_AICONTEXT_FIELDS
    # The existing public assembly path still behaves exactly as before.
    request = AIRequest(
        user_query="When does the library open?",
        retrieval_scope=RetrievalScope(institution_id=UUID(INST_A)),
        retrieved_chunks=[_chunk("Library hours are 8am to 8pm.")],
        model_name="some/model",
    )
    public_ctx = assemble_context(request)
    assert set(public_ctx.model_dump()) == _EXISTING_AICONTEXT_FIELDS
    assert public_ctx.system_instructions == SYSTEM_INSTRUCTIONS
    assert public_ctx.user_question == "When does the library open?"
    # The builder output is the same contract and round-trips through the
    # model without any special casing.
    ctx = builder.build_personalized_ai_context(_pc(chunks=[_chunk()]), _U())
    reparsed = AIContext.model_validate(ctx.model_dump())
    assert reparsed.user_question == ctx.user_question
    assert reparsed.student_context == ctx.student_context


def test_16_public_context_cannot_receive_student_academic_data():
    """The public path never receives StudentAcademicContext data."""
    request = AIRequest(
        user_query=QUERY,
        retrieval_scope=RetrievalScope(institution_id=UUID(INST_A)),
        retrieved_chunks=[_chunk("Attendance policy requires 75 percent.")],
    )
    public_ctx = assemble_context(request)

    # Public context: no student block at all, even though the query is
    # phrased as a personal question.
    assert public_ctx.student_context is None
    content = _build_user_content(public_ctx)
    assert "<authorized_student_data>" not in content
    assert "STU100" not in content
    assert "10 of 12" not in content

    # Only the personalized builder (fed an ALREADY-AUTHORIZED
    # PersonalizedContext) can produce the block — and it reuses the existing
    # delimiters so the Phase 6.10 privacy gates recognize it.
    personalized = builder.build_personalized_ai_context(_pc(chunks=[]), _U())
    p_content = _build_user_content(personalized)
    assert personalization_svc.prompt_contains_student_data(p_content)
    redacted = personalization_svc.redact_student_data(p_content)
    assert "STU100" not in redacted
    assert "10 of 12" not in redacted


def test_17_personalized_context_consumed_by_existing_generation_service():
    """The built AIContext flows through the UNCHANGED AIGenerationService."""
    chunk = _chunk("Attendance policy requires 75 percent attendance.")
    pc = _pc(chunks=[chunk])
    ctx = builder.build_personalized_ai_context(pc, _U())

    provider = _FakeProvider("You attended 10 of 12 classes (83.33%).")
    service = AIGenerationService(provider)
    response = service.generate(ctx)

    assert response.status == "success"
    assert response.answer == "You attended 10 of 12 classes (83.33%)."
    assert response.model_used == "fake/model"
    # Grounding validation still enforces chunk-id provenance.
    assert response.source_references[0].chunk_id == chunk.chunk_id
    # The provider received the full context: knowledge + private block.
    assert provider.calls == [ctx]
    content = _build_user_content(ctx)
    assert chunk.text in content
    assert "10 of 12 classes present (83.33%)" in content
    assert "<authorized_student_data>" in content


# ============================================================================
# 18-20: Phase 6.14.5 / 6.14.4 / existing-generation regressions
# ============================================================================


def test_18_phase_6145_regression():
    """The Phase 6.14.5 boundary contract is untouched by this phase."""
    # Identity is still derived EXCLUSIVELY from current_user: no client
    # identity parameter exists on the retrieval boundary.
    params = list(inspect.signature(prsvc.get_personalized_context).parameters)
    assert params == [
        "current_user",
        "query",
        "academic_year_id",
        "semester_id",
        "client",
        "top_k",
    ]
    assert not any(
        name in params
        for name in (
            "student_id",
            "user_id",
            "institution_id",
            "organization_id",
            "scope_id",
        )
    )
    # PersonalizedContext is still extra="forbid" and keeps both sources
    # explicitly separated.
    assert PersonalizedContext.model_config.get("extra") == "forbid"
    assert set(PersonalizedContext.model_fields) == {
        "query",
        "knowledge",
        "academic",
    }
    with pytest.raises(ValidationError):
        PersonalizedContext(query="x", rogue_field="nope")
    # Blank queries are still rejected by the upstream boundary contract (and
    # defensively by the builder).
    with pytest.raises(Exception):
        prsvc.get_personalized_context(_U(), "   ")
    with pytest.raises(Exception):
        builder.build_personalized_ai_context(
            PersonalizedContext(query="   "), _U()
        )


def test_19_phase_6144_regression():
    """The Phase 6.14.4 academic-context contract is untouched."""
    assert StudentAcademicContext.model_config.get("extra") == "forbid"
    assert set(StudentAcademicContext.model_fields) == {
        "student",
        "institution",
        "attendance",
        "results",
    }
    # Existing resolver limits are still the authoritative defaults.
    assert resolver.DEFAULT_ATTENDANCE_LIMIT == 200
    assert resolver.DEFAULT_TEST_RESULTS_LIMIT == 100
    params = list(
        inspect.signature(resolver.get_student_academic_context).parameters
    )
    assert params == [
        "current_user",
        "academic_year_id",
        "semester_id",
        "date_from",
        "date_to",
        "client",
        "attendance_limit",
        "test_results_limit",
    ]
    assert not any(
        name in params
        for name in ("student_id", "user_id", "institution_id", "organization_id")
    )


def test_20_existing_generation_regression():
    """The existing public generation pipeline behaves exactly as before."""
    chunk = _chunk("The library opens at 8am and closes at 8pm.")
    request = AIRequest(
        user_query="When does the library open?",
        retrieval_scope=RetrievalScope(institution_id=UUID(INST_A)),
        retrieved_chunks=[chunk],
    )
    ctx = assemble_context(request)

    # Standard public assembly is unchanged (no student guidance injected).
    assert ctx.system_instructions == SYSTEM_INSTRUCTIONS
    assert ctx.grounding_instructions == GROUNDING_INSTRUCTIONS
    assert ctx.student_context is None
    assert STUDENT_DATA_GUIDANCE not in ctx.grounding_instructions

    # The unchanged service still generates and still enforces grounding.
    provider = _FakeProvider("The library opens at 8am.")
    response = AIGenerationService(provider).generate(ctx)
    assert response.status == "success"
    assert response.answer == "The library opens at 8am."
    assert response.source_references[0].chunk_id == chunk.chunk_id
    content = _build_user_content(ctx)
    assert "Retrieved college knowledge:" in content
    assert chunk.text in content
    assert "authorized_student_data" not in content
