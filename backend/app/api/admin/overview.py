"""Admin overview endpoints."""

from fastapi import Depends

from app.schemas.admin.admin_dashboard import DashboardResponse
from app.services.admin import admin_dashboard
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


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


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    current_user: dict = Depends(_ADMIN),
) -> DashboardResponse:
    """Operational overview of the authenticated admin's own institution.

    Phase 7.21 — the institution comes from ``require_institution_roles`` (the
    server-resolved Phase 7.20 authorization context), never from a query
    parameter. The previous optional ``institution_id`` query parameter is
    GONE: a client-supplied tenant can no longer even be *accepted*, so it can
    neither widen nor redirect the scope. FastAPI ignores unknown query
    parameters, so an old client sending ``?institution_id=<other tenant>``
    simply receives its own institution's data.

    The response is an explicit ``DashboardResponse`` (see
    ``app/schemas/admin/admin_dashboard.py``): counts, display strings, and bounded
    recent notices only. No raw database row, no audit record, no internal id,
    no platform or provider information is ever serialized here.
    """
    return admin_dashboard.get_dashboard_summary(
        institution_id=common.required_institution(current_user),
    )
