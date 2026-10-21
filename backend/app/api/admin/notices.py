"""Admin notices endpoints."""

from uuid import UUID

from fastapi import Depends

from app.services.admin import admin_notices
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/notices")
def list_notices(
    institution_id: UUID | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    institution_id = common.scope_institution(current_user, institution_id)
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
    payload = payload.model_copy(
        update={"institution_id": common.scope_institution(current_user, payload.institution_id)}
    )
    notice = admin_notices.create_notice(payload, current_user["user_id"])
    common.record_audit(
        current_user,
        "notice.create",
        "notices",
        notice["notice_id"],
        {"title": payload.title, "institution_id": payload.institution_id},
    )
    return notice


@router.get("/notices/{notice_id}")
def get_notice(notice_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    notice = admin_notices.get_notice(notice_id)
    common.assert_row_tenant(current_user, notice.get("institution_id"))
    return notice


@router.patch("/notices/{notice_id}")
def update_notice(
    notice_id: UUID,
    payload: admin_notices.NoticeUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_row_tenant(current_user, admin_notices.get_notice(notice_id).get("institution_id"))
    updated = admin_notices.update_notice(notice_id, payload, current_user["user_id"])
    common.record_audit(
        current_user,
        "notice.update",
        "notices",
        str(notice_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/notices/{notice_id}")
def delete_notice(notice_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    common.assert_row_tenant(current_user, admin_notices.get_notice(notice_id).get("institution_id"))
    deleted = admin_notices.delete_notice(notice_id)
    common.record_audit(current_user, "notice.delete", "notices", str(notice_id), None)
    return {"deleted": True, "notice": deleted}
