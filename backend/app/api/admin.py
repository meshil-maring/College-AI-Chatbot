"""Admin API (Phase Admin-3).

Every endpoint requires the ``admin`` role via the existing
``require_roles("admin")`` dependency. Every mutation writes an entry to
``admin_audit_log`` (actor resolved server-side from the authenticated JWT).
No tokens or credentials are ever logged or echoed in errors.

The RAG document workflow reuses the existing locked ingestion services —
nothing in the RAG implementation itself is modified.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, UploadFile

from app.core.errors import AppError
from app.core.security import require_roles
from app.db.supabase import get_admin_client
from app.repositories import admin_knowledge as knowledge_repo
from app.repositories.admin_audit import (
    get_audit_entry,
    list_audit_entries,
    record_admin_action,
)
from app.schemas.admin import (
    AdminAuditLogCreate,
    KnowledgeSourceCreate,
    KnowledgeSourceUpdate,
)
from app.services import admin_academics, admin_dashboard, admin_documents, admin_faq, admin_notices
from app.services.admin_academics import (
    AttendanceCreate,
    AttendanceUpdate,
    ResultCreate,
    ResultUpdate,
    StudentCreate,
    StudentUpdate,
    TestResultCreate,
    TestResultUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN = require_roles("admin")


def _record_audit(
    current_user: dict,
    action: str,
    table_name: str | None,
    record_id: str | None = None,
    record_data: dict | None = None,
) -> None:
    """Persist one admin_audit_log entry for a privileged mutation."""
    record_admin_action(
        get_admin_client(),
        AdminAuditLogCreate(
            actor_user_id=UUID(current_user["user_id"]),
            action=action,
            table_name=table_name,
            record_id=str(record_id) if record_id is not None else None,
            record_data=record_data,
        ),
    )


# ============================================================================
# Admin identity/status
# ============================================================================


@router.get("/me")
def admin_me(current_user: dict = Depends(_ADMIN)) -> dict:
    """Identity and authorization status of the authenticated admin."""
    return {
        "user_id": current_user["user_id"],
        "auth_user_id": current_user["auth_user_id"],
        "email": current_user["email"],
        "roles": current_user["roles"],
        "is_admin": True,
    }


# ============================================================================
# Dashboard
# ============================================================================


@router.get("/dashboard")
def dashboard(
    institution_id: UUID | None = None,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    """Counts across admin-managed tables plus recent audit activity."""
    return admin_dashboard.get_dashboard_summary(institution_id=institution_id)


# ============================================================================
# Knowledge sources
# ============================================================================


@router.post("/knowledge-sources", status_code=201)
def create_knowledge_source(
    payload: KnowledgeSourceCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = get_admin_client()
    created = knowledge_repo.create_knowledge_source(db, payload, current_user["user_id"])
    _record_audit(
        current_user,
        "knowledge_source.create",
        "knowledge_sources",
        created["knowledge_source_id"],
        {"source_type": payload.source_type, "title": payload.title},
    )
    return created


@router.get("/knowledge-sources")
def list_knowledge_sources(
    institution_id: UUID,
    include_archived: bool = True,
    limit: int = 100,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    db = get_admin_client()
    return knowledge_repo.list_knowledge_sources(
        db, institution_id, include_archived=include_archived, limit=limit
    )


@router.get("/knowledge-sources/{knowledge_source_id}")
def get_knowledge_source(
    knowledge_source_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = get_admin_client()
    row = knowledge_repo.get_knowledge_source_detail(db, knowledge_source_id)
    if row is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    return row


@router.patch("/knowledge-sources/{knowledge_source_id}")
def update_knowledge_source(
    knowledge_source_id: UUID,
    payload: KnowledgeSourceUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = get_admin_client()
    updated = knowledge_repo.update_knowledge_source(db, knowledge_source_id, payload)
    if updated is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    _record_audit(
        current_user,
        "knowledge_source.update",
        "knowledge_sources",
        str(knowledge_source_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated

# ============================================================================
# Documents (RAG upload orchestration)
# ============================================================================


@router.get("/knowledge-sources/{knowledge_source_id}/documents")
def list_documents(
    knowledge_source_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    db = get_admin_client()
    return knowledge_repo.list_documents_for_source(db, knowledge_source_id)


@router.get("/documents/{document_id}")
def get_document(
    document_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = get_admin_client()
    doc = knowledge_repo.get_document_with_versions(db, document_id)
    if doc is None:
        raise AppError("Document not found", status_code=404, code="DOCUMENT_NOT_FOUND")
    return doc


@router.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile,
    knowledge_source_id: UUID = Form(...),
    auto_process: bool = Form(default=True),
    current_user: dict = Depends(_ADMIN),
) -> dict:
    """Admin upload → ingestion → extraction → chunking → embedding → retrieval."""
    result = await admin_documents.upload_document(
        file=file,
        knowledge_source_id=str(knowledge_source_id),
        user_id=current_user["user_id"],
        auto_process=auto_process,
    )
    _record_audit(
        current_user,
        "document.upload",
        "documents",
        result["document_id"],
        {
            "knowledge_source_id": str(knowledge_source_id),
            "auto_process": auto_process,
            "original_filename": file.filename,
        },
    )
    return result


@router.post("/documents/{document_id}/versions", status_code=201)
async def upload_document_version(
    document_id: UUID,
    file: UploadFile,
    version_label: str | None = Form(default=None),
    auto_process: bool = Form(default=True),
    current_user: dict = Depends(_ADMIN),
) -> dict:
    """Register a new document version; superseded content leaves retrieval."""
    result = await admin_documents.update_document(
        file=file,
        document_id=document_id,
        user_id=current_user["user_id"],
        version_label=version_label,
        auto_process=auto_process,
    )
    _record_audit(
        current_user,
        "document.update",
        "documents",
        str(document_id),
        {
            "document_version_id": result["document_version_id"],
            "version_number": result["version_number"],
            "auto_process": auto_process,
            "original_filename": file.filename,
        },
    )
    return result


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    result = admin_documents.delete_document(document_id)
    _record_audit(
        current_user,
        "document.delete",
        "documents",
        str(document_id),
        None,
    )
    return result

# ============================================================================
# FAQs (with RAG synchronization)
# ============================================================================


@router.get("/faqs")
def list_faqs(
    institution_id: UUID | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    return admin_faq.list_faqs(
        institution_id=institution_id,
        category=category,
        include_inactive=include_inactive,
    )


@router.post("/faqs", status_code=201)
def create_faq(
    payload: admin_faq.FaqCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    faq = admin_faq.create_faq(payload, current_user["user_id"])
    _record_audit(
        current_user,
        "faq.create",
        "faqs",
        faq["faq_id"],
        {"question": payload.question, "institution_id": payload.institution_id},
    )
    return faq


@router.get("/faqs/{faq_id}")
def get_faq(faq_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    return admin_faq.get_faq(faq_id)


@router.patch("/faqs/{faq_id}")
def update_faq(
    faq_id: UUID,
    payload: admin_faq.FaqUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    updated = admin_faq.update_faq(faq_id, payload, current_user["user_id"])
    _record_audit(
        current_user,
        "faq.update",
        "faqs",
        str(faq_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.post("/faqs/{faq_id}/publish")
def publish_faq(
    faq_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    published = admin_faq.publish_faq(faq_id, current_user["user_id"])
    _record_audit(
        current_user,
        "faq.publish",
        "faqs",
        str(faq_id),
        None,
    )
    return published


@router.delete("/faqs/{faq_id}")
def delete_faq(faq_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    deleted = admin_faq.delete_faq(faq_id)
    _record_audit(current_user, "faq.delete", "faqs", str(faq_id), None)
    return {"deleted": True, "faq": deleted}


# ============================================================================
# Notices (with RAG synchronization)
# ============================================================================


@router.get("/notices")
def list_notices(
    institution_id: UUID | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    return admin_notices.list_notices(
        institution_id=institution_id,
        category=category,
        include_inactive=include_inactive,
    )


@router.post("/notices", status_code=201)
def create_notice(
    payload: admin_notices.NoticeCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    notice = admin_notices.create_notice(payload, current_user["user_id"])
    _record_audit(
        current_user,
        "notice.create",
        "notices",
        notice["notice_id"],
        {"title": payload.title, "institution_id": payload.institution_id},
    )
    return notice


@router.get("/notices/{notice_id}")
def get_notice(notice_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    return admin_notices.get_notice(notice_id)


@router.patch("/notices/{notice_id}")
def update_notice(
    notice_id: UUID,
    payload: admin_notices.NoticeUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    updated = admin_notices.update_notice(notice_id, payload, current_user["user_id"])
    _record_audit(
        current_user,
        "notice.update",
        "notices",
        str(notice_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/notices/{notice_id}")
def delete_notice(notice_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    deleted = admin_notices.delete_notice(notice_id)
    _record_audit(current_user, "notice.delete", "notices", str(notice_id), None)
    return {"deleted": True, "notice": deleted}

# ============================================================================
# Students management
# ============================================================================


@router.get("/students")
def list_students(
    institution_id: UUID,
    program_id: UUID | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    return admin_academics.list_students(
        institution_id,
        program_id=program_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/students", status_code=201)
def create_student(
    payload: StudentCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    created = admin_academics.create_student(payload)
    _record_audit(
        current_user,
        "student.create",
        "students",
        created["student_id"],
        {
            "student_number": payload.student_number,
            "institution_id": str(payload.institution_id),
        },
    )
    return created


@router.get("/students/{student_id}")
def get_student(student_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    return admin_academics.get_student(student_id)


@router.patch("/students/{student_id}")
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    updated = admin_academics.update_student(student_id, payload)
    _record_audit(
        current_user,
        "student.update",
        "students",
        str(student_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/students/{student_id}")
def archive_student(student_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    """Soft-archive a student (academic history retained, access ended)."""
    archived = admin_academics.archive_student(student_id)
    _record_audit(current_user, "student.archive", "students", str(student_id), None)
    return archived


# ============================================================================
# Results management
# ============================================================================


@router.get("/students/{student_id}/results")
def list_student_results(
    student_id: UUID,
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    return admin_academics.list_results_for_student(
        student_id, academic_year_id=academic_year_id, semester_id=semester_id
    )


@router.post("/results", status_code=201)
def create_result(
    payload: ResultCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    created = admin_academics.create_result(payload)
    _record_audit(
        current_user,
        "result.create",
        "student_results",
        created["student_result_id"],
        {
            "student_id": str(payload.student_id),
            "result_type": payload.result_type,
        },
    )
    return created


@router.get("/results/{result_id}")
def get_result(result_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    return admin_academics.get_result(result_id)


@router.patch("/results/{result_id}")
def update_result(
    result_id: UUID,
    payload: ResultUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    updated = admin_academics.update_result(result_id, payload)
    _record_audit(
        current_user,
        "result.update",
        "student_results",
        str(result_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/results/{result_id}")
def delete_result(result_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    deleted = admin_academics.delete_result(result_id)
    _record_audit(current_user, "result.delete", "student_results", str(result_id), None)
    return {"deleted": True, "result": deleted}

# ============================================================================
# Results CSV upload
# ============================================================================


@router.post("/results/csv-upload")
async def upload_results_csv(
    file: UploadFile,
    institution_id: UUID = Form(...),
    current_user: dict = Depends(_ADMIN),
) -> admin_academics.CsvUploadResult:
    """Validate and import result rows; bad rows are reported, valid rows kept."""
    content = await file.read()
    summary = admin_academics.upload_results_csv(content, institution_id)
    _record_audit(
        current_user,
        "result.csv_upload",
        "student_results",
        None,
        {
            "filename": file.filename,
            "institution_id": str(institution_id),
            "total_rows": summary.total_rows,
            "inserted_count": summary.inserted_count,
            "failed_count": summary.failed_count,
        },
    )
    return summary


# ============================================================================
# Test results management
# ============================================================================


@router.get("/students/{student_id}/test-results")
def list_student_test_results(
    student_id: UUID,
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    return admin_academics.list_test_results_for_student(
        student_id, academic_year_id=academic_year_id, semester_id=semester_id
    )


@router.post("/test-results", status_code=201)
def create_test_result(
    payload: TestResultCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    created = admin_academics.create_test_result(payload)
    _record_audit(
        current_user,
        "test_result.create",
        "test_results",
        created["test_result_id"],
        {
            "student_id": str(payload.student_id),
            "test_name": payload.test_name,
            "test_type": payload.test_type,
        },
    )
    return created


@router.patch("/test-results/{test_result_id}")
def update_test_result(
    test_result_id: UUID,
    payload: TestResultUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    updated = admin_academics.update_test_result(test_result_id, payload)
    _record_audit(
        current_user,
        "test_result.update",
        "test_results",
        str(test_result_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/test-results/{test_result_id}")
def delete_test_result(
    test_result_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    deleted = admin_academics.delete_test_result(test_result_id)
    _record_audit(
        current_user,
        "test_result.delete",
        "test_results",
        str(test_result_id),
        None,
    )
    return {"deleted": True, "test_result": deleted}

# ============================================================================
# Attendance management
# ============================================================================


@router.get("/students/{student_id}/attendance")
def list_student_attendance(
    student_id: UUID,
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    return admin_academics.list_attendance_for_student(
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/attendance", status_code=201)
def create_attendance(
    payload: AttendanceCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    created = admin_academics.create_attendance(payload)
    _record_audit(
        current_user,
        "attendance.create",
        "student_attendance",
        created["student_attendance_id"],
        {
            "student_id": str(payload.student_id),
            "date": str(payload.date),
            "status": payload.status,
        },
    )
    return created


@router.patch("/attendance/{attendance_id}")
def update_attendance(
    attendance_id: UUID,
    payload: AttendanceUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    updated = admin_academics.update_attendance(attendance_id, payload)
    _record_audit(
        current_user,
        "attendance.update",
        "student_attendance",
        str(attendance_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/attendance/{attendance_id}")
def delete_attendance(attendance_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    deleted = admin_academics.delete_attendance(attendance_id)
    _record_audit(
        current_user,
        "attendance.delete",
        "student_attendance",
        str(attendance_id),
        None,
    )
    return {"deleted": True, "attendance": deleted}


# ============================================================================
# Audit log
# ============================================================================


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = 50,
    actor_user_id: UUID | None = None,
    table_name: str | None = None,
    action: str | None = None,
    status: str | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    db = get_admin_client()
    return list_audit_entries(
        db,
        limit=limit,
        actor_user_id=actor_user_id,
        table_name=table_name,
        action=action,
        status=status,
    )


@router.get("/audit-logs/{audit_id}")
def get_audit_log(audit_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    db = get_admin_client()
    entry = get_audit_entry(db, audit_id)
    if entry is None:
        raise AppError("Audit entry not found", status_code=404, code="AUDIT_NOT_FOUND")
    return entry





