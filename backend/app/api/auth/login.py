"""Authentication login endpoints."""

import logging

import httpx
from fastapi import Request
from supabase_auth.errors import AuthApiError, AuthRetryableError

from app.core.errors import AppError
from app.services.auth.sign_in import assert_sign_in_allowed
from app.services.auth.student_auth import SafeAuthFailure
from app.repositories.platform import tenancy as tenancy_repo
from app.api.auth import common
from app.schemas.auth.auth import AuthRequest


logger = logging.getLogger(__name__)


router = common.create_feature_router()


def _pending_registration_for_email(email: str) -> dict | None:
    """Resolve a pending staff/faculty request from a trusted account email."""
    db = common.get_admin_client()
    user = tenancy_repo.get_user_by_email(db, email)
    if user is None:
        return None
    return tenancy_repo.get_pending_membership_request_for_user(db, user["user_id"])


def _raise_registration_pending(request: dict) -> None:
    role = str(request.get("requested_role") or "faculty")
    raise AppError(
        f"Your {role} registration is pending. Contact your institution administrator to continue.",
        status_code=403,
        code="REGISTRATION_PENDING",
    )


@router.post("/login")
async def login(body: AuthRequest, request: Request):
    """Authenticate with email + password and return a Supabase Auth session.

    Response shape includes the provider access/refresh tokens and
    ``expires_in`` alongside the locked message/user fields.

    The password is forwarded to Supabase Auth only; it is never returned,
    logged, or persisted anywhere. After credential verification the Phase
    6.13.6 status guard decides — server-side — whether the account may
    complete sign-in (public.users row present, ``users.status == 'active'``,
    and tenant-bound accounts approved + active with an active institution).
    """
    common.enforce_auth_rate_limit("login", request)
    try:
        return await _authenticate_email_login(body, request)
    except (httpx.TransportError, AuthRetryableError):
        logger.warning("event=auth_login_unavailable category=dependency_unavailable")
        raise AppError(
            "Authentication is temporarily unavailable. Please try again shortly.",
            status_code=503,
            code="AUTH_SERVICE_UNAVAILABLE",
            headers={"Retry-After": "5"},
        ) from None


async def _authenticate_email_login(body: AuthRequest, request: Request) -> dict:
    """Issue a login response only after all provider and account checks succeed."""
    try:
        client = common.create_supabase_client()
        response = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as e:
        # GoTrue may block a newly self-registered account as unconfirmed
        # before issuing a session. This response is only produced after the
        # submitted password has matched, so translating it does not expose a
        # pending account to callers with incorrect credentials.
        auth_code = str(getattr(e, "code", "") or "").lower()
        auth_message = str(getattr(e, "message", "") or "").lower()
        if auth_code == "email_not_confirmed" or "email not confirmed" in auth_message:
            pending = _pending_registration_for_email(str(body.email))
            if pending is not None:
                _raise_registration_pending(pending)
        common.record_auth_security_event(
            event="login",
            status="failure",
            request=request,
        )
        raise AppError(
            "Invalid login credentials",
            status_code=400,
            code="INVALID_CREDENTIALS",
        ) from e

    # Phase 6.13.6 — post-authentication status guard (fail-closed). The
    # account context is resolved from trusted server-side records only; the
    # client cannot influence user, organization, institution, role, or scope.
    account = await common.get_sign_in_context(response.user.id)
    # Credentials have already been verified, so it is safe and useful to
    # explain why a self-registered staff/faculty account cannot continue.
    # Incorrect passwords still receive the generic INVALID_CREDENTIALS error
    # above and cannot be used to discover registration state.
    if account is not None:
        pending_request = tenancy_repo.get_pending_membership_request_for_user(
            common.get_admin_client(), account["user_id"]
        )
        if pending_request is not None:
            _raise_registration_pending(pending_request)
    try:
        assert_sign_in_allowed(common.get_admin_client(), account)
    except SafeAuthFailure as exc:
        # Normalize every status denial to the LOCKED Phase 5.4 login failure
        # response: 400 INVALID_CREDENTIALS with Supabase's own wording, so the
        # response is byte-for-byte indistinguishable from a wrong password and
        # account existence / approval / lifecycle state is never disclosed.
        common.record_auth_security_event(
            event="login",
            status="failure",
            request=request,
            user_id=str(account["user_id"]) if account is not None else None,
            auth_user_id=str(response.user.id),
        )
        raise AppError(
            "Invalid login credentials",
            status_code=400,
            code="INVALID_CREDENTIALS",
        ) from exc

    common.record_auth_security_event(
        event="login",
        status="success",
        request=request,
        user_id=str(account["user_id"]),
        auth_user_id=str(response.user.id),
    )
    return common.session_payload(response.session, response.user)
