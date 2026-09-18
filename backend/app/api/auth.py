"""Authentication endpoints (Phase 5.4 + Phase 6.13.6).

``POST /auth/signup`` — existing Supabase Auth signup (unchanged).
``POST /auth/login``  — email + password sign-in for every account that uses
the existing email identity model (admins, faculty, staff, and the demo
accounts). Phase 6.13.6 extends this endpoint IN PLACE — no duplicate
endpoint, no second authentication system:

    1. Credentials are verified by Supabase Auth (GoTrue), the SINGLE
       credential authority. The password is never stored, hashed, compared,
       logged, or echoed by this application.
    2. After successful authentication the account is resolved server-side
       through the existing tenant-resolution chain
       (``auth.users -> public.users -> students -> institutions``) via
       ``get_sign_in_context`` (additive sibling of ``get_user_by_auth_id``).
    3. Status guard (fail-closed): sign-in completes only when
           * the ``public.users`` row exists,
           * ``users.status == 'active'``,
           * tenant-bound (students profile) accounts are Phase 6.4 approved,
             lifecycle-active, and their institution is active.
       All denials normalize to the LOCKED Phase 5.4 login failure contract —
       ``400 INVALID_CREDENTIALS`` with the same message Supabase Auth emits
       for a wrong password — so account existence, approval state, and
       lifecycle state are never disclosed (anti-enumeration), and the
       existing frontend mapping (400 + ``INVALID_CREDENTIALS`` ->
       ``invalid_credentials``) keeps working unchanged.

Authorization (role, organization/institution scope) is NEVER accepted from
the client: the request schema uses ``extra="forbid"`` and role/scope are
always resolved from trusted server-side records after authentication.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.db.supabase import (
    create_supabase_client,
    get_admin_client,
    get_sign_in_context,
)
from app.services.sign_in import assert_sign_in_allowed
from app.services.student_auth import SafeAuthFailure

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    """Login / signup payload.

    ``extra="forbid"`` — clients can NEVER inject ``role``, ``scope_type``,
    ``scope_id``, ``institution_id``, ``organization_id``, ``status``, or any
    other authorization-control field. Role and scope are resolved ONLY from
    trusted server-side records after authentication.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


@router.post("/signup", status_code=201)
def signup(body: AuthRequest):
    try:
        client = create_supabase_client()
        response = client.auth.sign_up({"email": body.email, "password": body.password})
        if response.session is None:
            return {
                "access_token": None,
                "message": "Signup successful. Please check your email to confirm your account.",
                "user": {"id": response.user.id, "email": response.user.email},
            }
        return {
            "access_token": response.session.access_token,
            "message": "Signup successful.",
            "user": {"id": response.user.id, "email": response.user.email},
        }
    except AuthApiError as e:
        raise AppError(e.message, status_code=e.status, code="AUTH_ERROR")


@router.post("/login")
async def login(body: AuthRequest):
    """Authenticate with email + password and return a Supabase Auth session.

    Response shape (locked by the Phase 5.4 frontend contract):
        ``{"access_token": ..., "message": ..., "user": {"id", "email"}}``

    The password is forwarded to Supabase Auth only; it is never returned,
    logged, or persisted anywhere. After credential verification the Phase
    6.13.6 status guard decides — server-side — whether the account may
    complete sign-in (public.users row present, ``users.status == 'active'``,
    and tenant-bound accounts approved + active with an active institution).
    """
    try:
        client = create_supabase_client()
        response = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as e:
        status = e.status or 400
        code = "INVALID_CREDENTIALS" if status == 400 else "AUTH_ERROR"
        raise AppError(e.message, status_code=status, code=code)

    # Phase 6.13.6 — post-authentication status guard (fail-closed). The
    # account context is resolved from trusted server-side records only; the
    # client cannot influence user, organization, institution, role, or scope.
    account = await get_sign_in_context(response.user.id)
    try:
        assert_sign_in_allowed(get_admin_client(), account)
    except SafeAuthFailure as exc:
        # Normalize every status denial to the LOCKED Phase 5.4 login failure
        # response: 400 INVALID_CREDENTIALS with Supabase's own wording, so the
        # response is byte-for-byte indistinguishable from a wrong password and
        # account existence / approval / lifecycle state is never disclosed.
        raise AppError(
            "Invalid login credentials",
            status_code=400,
            code="INVALID_CREDENTIALS",
        ) from exc

    return {
        "access_token": response.session.access_token,
        "message": "Login successful.",
        "user": {"id": response.user.id, "email": response.user.email},
    }
