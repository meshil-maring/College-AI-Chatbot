"""Student-scoped transfer request routes (self-service + staff-entry)."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends

from app.core.security import authorize_permissions, get_current_user
from app.repositories.students import transfer_equivalency as transfer_equiv_repo
from app.schemas.students import transfer_request as schemas
from app.services.students import transfer_service, transfer_util, transfer_workflow
from app.services.students.student_context import get_student_context

router = APIRouter(prefix="/transfer-requests", tags=["transfer-requests"])


@router.get(
    "",
    response_model=schemas.TransferRequestList,
    summary="List the authenticated student's transfer requests",
)
def list_my_transfers(current_user: dict = Depends(get_current_user)) -> schemas.TransferRequestList:
    authorize_permissions(current_user, "transfers.read")
    student = get_student_context(current_user)
    return transfer_service.list_transfer_requests(
        current_user, student_id=student["student_id"]
    )


@router.get(
    "/settings",
    response_model=schemas.InstitutionTransferSettings,
    summary="Get institution transfer settings",
)
def get_transfer_settings(
    current_user: dict = Depends(get_current_user),
) -> schemas.InstitutionTransferSettings:
    authorize_permissions(current_user, "transfers.read")
    client, tenant, _ = transfer_util._context(current_user, ("transfers.read",))
    settings = transfer_equiv_repo.get_transfer_settings(client, tenant=tenant)
    if not settings:
        return schemas.InstitutionTransferSettings(
            institution_id=str(tenant),
            allow_student_transfer_requests=False,
            allow_staff_created_transfers=True,
            max_active_requests_per_student=1,
            updated_at=None,
        )
    return schemas.InstitutionTransferSettings(**settings)


@router.put(
    "/settings",
    response_model=schemas.InstitutionTransferSettings,
    summary="Update institution transfer settings",
)
def update_transfer_settings(
    payload: schemas.InstitutionTransferSettingsUpdate,
    current_user: dict = Depends(get_current_user),
) -> schemas.InstitutionTransferSettings:
    authorize_permissions(current_user, "institution.settings.manage")
    client, tenant, actor_id = transfer_util._context(current_user, ("institution.settings.manage",))
    settings = transfer_equiv_repo.upsert_transfer_settings(
        client, actor=actor_id, tenant=tenant, payload=payload.model_dump(exclude_none=True)
    )
    return schemas.InstitutionTransferSettings(**settings)


@router.get(
    "/equivalencies",
    response_model=schemas.TransferEquivalencyList,
    summary="List subject equivalencies",
)
def list_equivalencies(
    current_user: dict = Depends(get_current_user),
    program_id: UUID | None = None,
) -> schemas.TransferEquivalencyList:
    authorize_permissions(current_user, "transfers.read")
    client, tenant, _ = transfer_util._context(current_user, ("transfers.read",))
    items = transfer_equiv_repo.list_equivalencies(
        client, tenant=tenant, program_id=program_id
    )
    return schemas.TransferEquivalencyList(items=items)


@router.post(
    "/equivalencies",
    response_model=schemas.SubjectEquivalency,
    summary="Create subject equivalency",
)
def create_equivalency(
    payload: schemas.TransferEquivalencyCreate,
    current_user: dict = Depends(get_current_user),
) -> schemas.SubjectEquivalency:
    authorize_permissions(current_user, "institution.settings.manage")
    client, tenant, actor_id = transfer_util._context(current_user, ("institution.settings.manage",))
    row = transfer_equiv_repo.create_equivalency(
        client, actor=actor_id, tenant=tenant, payload=payload.model_dump()
    )
    return schemas.SubjectEquivalency(**row)


@router.get(
    "/{request_id}",
    response_model=schemas.TransferRequestResponse,
    summary="Get a transfer request with eligibility and approval history",
)
def get_transfer(
    request_id: UUID,
    current_user: dict = Depends(get_current_user),
) -> schemas.TransferRequestResponse:
    authorize_permissions(current_user, "transfers.read")
    return transfer_service.get_transfer_request_view(current_user, request_id)


@router.post(
    "",
    status_code=201,
    response_model=schemas.TransferRequestResponse,
    summary="Submit a transfer request",
)
def create_transfer(
    payload: schemas.TransferRequestCreate,
    current_user: dict = Depends(get_current_user),
) -> schemas.TransferRequestResponse:
    authorize_permissions(current_user, "transfers.request")
    return transfer_service.submit_transfer_request(
        current_user,
        current_user=current_user,
        student_id=payload.student_id,
        payload=payload.model_dump(),
    )


@router.put(
    "/{request_id}/review",
    response_model=schemas.TransferRequestResponse,
    summary="Review a transfer request eligibility",
)
def review_transfer_api(
    request_id: UUID,
    review: schemas.TransferReview = Body(...),
    current_user: dict = Depends(get_current_user),
) -> schemas.TransferRequestResponse:
    authorize_permissions(current_user, "transfers.review")
    return transfer_workflow.review_transfer(current_user, request_id, review.model_dump())


@router.put(
    "/{request_id}/approve",
    response_model=schemas.TransferRequestResponse,
    summary="Approve a transfer request",
)
def approve_transfer_api(
    request_id: UUID,
    review: schemas.TransferReview = Body(...),
    current_user: dict = Depends(get_current_user),
) -> schemas.TransferRequestResponse:
    authorize_permissions(current_user, "transfers.approve")
    return transfer_workflow.approve_transfer(current_user, request_id, review.model_dump())


@router.put(
    "/{request_id}/reject",
    response_model=schemas.TransferRequestResponse,
    summary="Reject a transfer request",
)
def reject_transfer_api(
    request_id: UUID,
    review: schemas.TransferReview = Body(...),
    current_user: dict = Depends(get_current_user),
) -> schemas.TransferRequestResponse:
    authorize_permissions(current_user, "transfers.review")
    return transfer_workflow.reject_transfer(current_user, request_id, review.model_dump())


@router.put(
    "/{request_id}/complete",
    response_model=schemas.TransferRequestResponse,
    summary="Complete a transfer request",
)
def complete_transfer_api(
    request_id: UUID,
    complete: schemas.TransferComplete = Body(...),
    current_user: dict = Depends(get_current_user),
) -> schemas.TransferRequestResponse:
    authorize_permissions(current_user, "transfers.complete")
    return transfer_workflow.complete_transfer(current_user, request_id, complete.model_dump())
