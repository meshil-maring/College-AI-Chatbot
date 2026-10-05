"""Public Super Admin registration boundary (Phase 9).

Authorized solely by possession of a single-use, expiring invitation token.
"""

from fastapi import APIRouter, Request, status

from app.schemas.super_admin_registration import (
    SuperAdminInvitePublicView,
    SuperAdminRegisteredResponse,
    SuperAdminRegisterRequest,
)
from app.services import super_admin_registration as service

router = APIRouter(prefix="/super-admin-invitations", tags=["super-admin-invitations"])


def _peer(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


@router.get("/{token}", response_model=SuperAdminInvitePublicView)
def inspect_super_admin_invitation(token: str, request: Request):
    return service.inspect_invitation(token, peer=_peer(request))


@router.post(
    "/{token}/register",
    response_model=SuperAdminRegisteredResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_super_admin(token: str, body: SuperAdminRegisterRequest, request: Request):
    return service.register_super_admin(token, body, peer=_peer(request))
