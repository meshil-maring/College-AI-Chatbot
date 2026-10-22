"""Admin results endpoints."""

from uuid import UUID

from fastapi import Depends, Form, UploadFile

from app.config import settings
from app.services.admin import admin_academics
from app.services.admin.admin_academics import (
    ResultCreate,
    ResultUpdate,
    TestResultCreate,
    TestResultUpdate,
)
from app.services.knowledge.ingestion import read_upload_limited
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/students/{student_id}/results")
def list_student_results(
    student_id: UUID,
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    common.assert_student_tenant(current_user, student_id)
    return admin_academics.list_results_for_student(
        student_id, academic_year_id=academic_year_id, semester_id=semester_id
    )


@router.post("/results", status_code=201)
def create_result(
    payload: ResultCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_student_tenant(current_user, payload.student_id)
    created = admin_academics.create_result(payload)
    common.record_audit(
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
    result = admin_academics.get_result(result_id)
    common.assert_student_tenant(current_user, result["student_id"])
    return result


@router.patch("/results/{result_id}")
def update_result(
    result_id: UUID,
    payload: ResultUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_student_tenant(current_user, admin_academics.get_result(result_id)["student_id"])
    updated = admin_academics.update_result(result_id, payload)
    common.record_audit(
        current_user,
        "result.update",
        "student_results",
        str(result_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/results/{result_id}")
def delete_result(result_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    common.assert_student_tenant(current_user, admin_academics.get_result(result_id)["student_id"])
    deleted = admin_academics.delete_result(result_id)
    common.record_audit(current_user, "result.delete", "student_results", str(result_id), None)
    return {"deleted": True, "result": deleted}


@router.post("/results/csv-upload")
async def upload_results_csv(
    file: UploadFile,
    institution_id: UUID = Form(...),
    current_user: dict = Depends(_ADMIN),
) -> admin_academics.CsvUploadResult:
    """Validate and import result rows; bad rows are reported, valid rows kept."""
    institution_id = common.scope_institution(current_user, institution_id)
    content = await read_upload_limited(file, settings.max_csv_upload_bytes)
    summary = admin_academics.upload_results_csv(content, institution_id)
    common.record_audit(
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


@router.get("/students/{student_id}/test-results")
def list_student_test_results(
    student_id: UUID,
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    common.assert_student_tenant(current_user, student_id)
    return admin_academics.list_test_results_for_student(
        student_id, academic_year_id=academic_year_id, semester_id=semester_id
    )


@router.post("/test-results", status_code=201)
def create_test_result(
    payload: TestResultCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_student_tenant(current_user, payload.student_id)
    created = admin_academics.create_test_result(payload)
    common.record_audit(
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
    common.assert_student_tenant(
        current_user, admin_academics.get_test_result(test_result_id)["student_id"]
    )
    updated = admin_academics.update_test_result(test_result_id, payload)
    common.record_audit(
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
    common.assert_student_tenant(
        current_user, admin_academics.get_test_result(test_result_id)["student_id"]
    )
    deleted = admin_academics.delete_test_result(test_result_id)
    common.record_audit(
        current_user,
        "test_result.delete",
        "test_results",
        str(test_result_id),
        None,
    )
    return {"deleted": True, "test_result": deleted}
