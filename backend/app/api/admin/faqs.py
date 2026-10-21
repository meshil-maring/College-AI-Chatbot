"""Admin faqs endpoints."""

from uuid import UUID

from fastapi import Depends

from app.services.admin import admin_faq
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/faqs")
def list_faqs(
    institution_id: UUID | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    institution_id = common.scope_institution(current_user, institution_id)
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
    payload = payload.model_copy(
        update={"institution_id": common.scope_institution(current_user, payload.institution_id)}
    )
    faq = admin_faq.create_faq(payload, current_user["user_id"])
    common.record_audit(
        current_user,
        "faq.create",
        "faqs",
        faq["faq_id"],
        {"question": payload.question, "institution_id": payload.institution_id},
    )
    return faq


@router.get("/faqs/{faq_id}")
def get_faq(faq_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    faq = admin_faq.get_faq(faq_id)
    common.assert_row_tenant(current_user, faq.get("institution_id"))
    return faq


@router.patch("/faqs/{faq_id}")
def update_faq(
    faq_id: UUID,
    payload: admin_faq.FaqUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_row_tenant(current_user, admin_faq.get_faq(faq_id).get("institution_id"))
    updated = admin_faq.update_faq(faq_id, payload, current_user["user_id"])
    common.record_audit(
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
    common.assert_row_tenant(current_user, admin_faq.get_faq(faq_id).get("institution_id"))
    published = admin_faq.publish_faq(faq_id, current_user["user_id"])
    common.record_audit(
        current_user,
        "faq.publish",
        "faqs",
        str(faq_id),
        None,
    )
    return published


@router.delete("/faqs/{faq_id}")
def delete_faq(faq_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    common.assert_row_tenant(current_user, admin_faq.get_faq(faq_id).get("institution_id"))
    deleted = admin_faq.delete_faq(faq_id)
    common.record_audit(current_user, "faq.delete", "faqs", str(faq_id), None)
    return {"deleted": True, "faq": deleted}
