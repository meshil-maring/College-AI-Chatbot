"""Platform platform audit."""

from datetime import datetime
from uuid import UUID
from fastapi import Depends
from app.schemas.invitations.admin_invitations import PlatformAuditListResponse
from app.services.invitations import platform_admin_invitations as invitations_service
from fastapi import APIRouter
from app.api.platform.dependencies import _SUPER_ADMIN

router = APIRouter(prefix="/platform")


@router.get(
    "/audit",
    response_model=PlatformAuditListResponse,
    summary="Read the platform audit ledger (Super Admin, read-only)",
)
async def read_platform_audit(
    institution_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> PlatformAuditListResponse:
    """Return one bounded page of platform audit records, newest first.

    Read-only by construction: there is no write, update or delete route for
    this ledger anywhere in the API. The optional filters are deliberately few —
    the platform audit volume is small and an over-engineered filter surface
    would be a disclosure risk rather than a feature.
    """
    return invitations_service.list_platform_audit(
        institution_id=institution_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
