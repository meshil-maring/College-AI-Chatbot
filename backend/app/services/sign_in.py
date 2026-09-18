"""Phase 6.13.6 — Post-authentication sign-in status guard.

Authentication proves WHO the user is (Supabase Auth — the single credential
authority). This module decides, from trusted server-side records ONLY,
whether the authenticated account may complete sign-in. It is a thin ADDITIVE
guard on the existing authentication flows: no new authentication system, no
new token mechanism, and no password handling of any kind.

Decision chain (mirrors the Phase 6.13 architecture:

    User -> Organization -> Institution -> Role -> Scope):

    * User        -> the ``public.users`` row must exist and
                     ``users.status`` must be 'active'
    * Institution -> tenant-bound accounts (students profile) require an
                     ACTIVE institution (the Phase 6.5 gate, REUSED here)
    * Role/Scope  -> NOT decided here. Roles and organization/institution
                     scope always come from ``user_roles`` / ``students`` via
                     ``get_user_by_auth_id`` + ``resolve_authorization_context``
                     (existing RBAC + scope checks) — never from the client.

Expected behaviour (locked):

    PENDING user   -> sign-in denied (students) / protected access denied
                      through RBAC (faculty/staff: no role granted yet)
    REJECTED user  -> sign-in denied (students) / protected access denied
    ACTIVE user    -> normal authenticated access

    ACTIVE institution                     -> access allowed per user scope
    PENDING/REJECTED/INACTIVE institution  -> protected access denied
                                              (``is_active`` is derived from
                                              ``status`` by the Phase 6.13
                                              trigger, so one check covers
                                              every non-active status)

Every denial raises ``SafeAuthFailure`` (401 INVALID_CREDENTIALS) so account
existence, approval state, and lifecycle state are never disclosed to the
client (Phase 6.5 anti-enumeration contract).
"""

from __future__ import annotations

from app.services.student_auth import SafeAuthFailure, _assert_institution_active

ACTIVE = "active"


def _has_student_profile(account: dict) -> bool:
    """A students profile is present when any profile-only field resolved.

    ``students.approval_status`` and ``students.institution_id`` are NOT NULL,
    so a resolved profile always carries them; a platform / faculty / staff
    account (no students row) resolves both to None.
    """
    return (
        account.get("approval_status") is not None
        or account.get("institution_id") is not None
    )


def assert_sign_in_allowed(db, account: dict | None) -> None:
    """Raise ``SafeAuthFailure`` unless the account may complete sign-in.

    ``db`` is the service-role client used by the reused Phase 6.5 institution
    activity check. ``account`` is the server-resolved context from
    ``app.db.supabase.get_sign_in_context`` — it is NEVER client-supplied and
    contains no role, scope, organization, or institution field a client could
    influence.
    """
    # Fail-closed: no public.users row -> no application account -> no sign-in.
    if account is None:
        raise SafeAuthFailure()

    # Account lifecycle (users.status CHECK: active | inactive | deactivated).
    # Anything other than 'active' is denied — fail-closed on unknown values.
    if account.get("status") != ACTIVE:
        raise SafeAuthFailure()

    if not _has_student_profile(account):
        # Platform-level accounts (admins, faculty, staff). Pending/rejected
        # faculty & staff hold no role yet, so protected access stays denied
        # through the existing Phase 6.6 RBAC; sign-in compatibility for the
        # existing email + password identity model is preserved (Phase 6.13.5).
        return

    # Tenant-bound (students profile) account — Phase 6.4 approval lifecycle:
    # only approval_status == 'approved' students may authenticate.
    if account.get("approval_status") != "approved":
        raise SafeAuthFailure()

    # Phase 6.2 lifecycle flag: inactive student profiles are blocked.
    if account.get("student_is_active") is False:
        raise SafeAuthFailure()

    # Phase 6.5 institution gate — reused, not duplicated. Pending/rejected/
    # suspended institutions all carry is_active = False (Phase 6.13 trigger).
    institution_id = account.get("institution_id")
    if institution_id is not None:
        _assert_institution_active(db, institution_id)