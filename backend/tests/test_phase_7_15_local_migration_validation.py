"""Phase 7.15 physical local-database validation.

Complements the mocked contract tests in
``test_phase_7_15_invitation_delivery_email_verification.py``: those prove the
application logic, THIS proves the migration really is applied to a database and
that its constraints actually hold.

It talks to the GUARDED LOCAL stack through exactly the same PostgREST surface
the application uses. It refuses to run if ``SUPABASE_URL`` is not a local
address, so it can never touch the linked remote project, and it skips (rather
than fails) when the local stack is not running, so a developer machine without
Docker still gets a green suite.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest

from app.config import settings

LOCAL_URL_MARKERS = ("127.0.0.1", "localhost")
MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20261001030000_phase_7_15_invitation_delivery_email_verification.sql"
)


@pytest.fixture(scope="module")
def local_db():
    url = (settings.supabase_url or "").strip()
    if not url or not any(marker in url for marker in LOCAL_URL_MARKERS):
        pytest.skip("SUPABASE_URL is not the guarded local stack")
    from app.db.supabase import get_admin_client

    client = get_admin_client()
    try:
        client.table("institutions").select("institution_id").limit(1).execute()
    except Exception:  # noqa: BLE001 - any connection failure means "not running"
        pytest.skip("local Supabase database is not reachable")
    return client


def _first(local_db, table: str, column: str) -> str:
    rows = local_db.table(table).select(column).limit(1).execute().data
    assert rows, f"expected at least one seeded row in {table}"
    return str(rows[0][column])


@pytest.fixture(scope="module")
def actor_id(local_db) -> str:
    """A real ``users`` id to satisfy the ``created_by`` / ``actor_user_id`` FKs.

    A freshly reset local database has no seeded accounts, so this module
    provisions a throwaway one rather than depending on developer seed data.

    ``users.auth_user_id`` is a foreign key into Supabase Auth, so the probe
    account is created the same way the application creates one: an Auth user
    first, then the ``public.users`` link row. It is LOCAL ONLY (the fixture
    refuses to run against a non-local ``SUPABASE_URL``), receives no role
    grant, and exists solely to satisfy the FK for the duration of this module.
    """
    rows = local_db.table("users").select("id").limit(1).execute().data
    if rows:
        return str(rows[0]["id"])

    email = f"p715-probe-{uuid.uuid4().hex[:8]}@unico.example"
    auth_user = local_db.auth.admin.create_user(
        {"email": email, "password": uuid.uuid4().hex, "email_confirm": True}
    ).user
    created = (
        local_db.table("users")
        .insert(
            {
                "auth_user_id": str(auth_user.id),
                "email": email,
                "first_name": "Phase",
                "last_name": "Probe",
                "status": "active",
            }
        )
        .execute()
        .data
    )
    assert created, "could not provision a probe user in the local database"
    return str(created[0]["id"])


@pytest.fixture(scope="module")
def institution_id(local_db) -> str:
    """A real ``institutions`` id to satisfy the invitation's tenant FK."""
    rows = local_db.table("institutions").select("institution_id").limit(1).execute().data
    if rows:
        return str(rows[0]["institution_id"])
    organization_id = (
        local_db.table("organizations")
        .select("organization_id")
        .limit(1)
        .execute()
        .data
    )
    if not organization_id:
        pytest.skip("no institution and no organization to create one from")
    created = (
        local_db.table("institutions")
        .insert(
            {
                "organization_id": str(organization_id[0]["organization_id"]),
                "name": f"P715 Probe {uuid.uuid4().hex[:6]}",
                "code": f"P715{uuid.uuid4().hex[:4].upper()}",
                "status": "active",
            }
        )
        .execute()
        .data
    )
    assert created, "could not provision a probe institution in the local database"
    return str(created[0]["institution_id"])


def _insert_invitation(local_db, **overrides):
    payload = {
        "institution_id": overrides.pop("institution_id"),
        "email": f"probe-{uuid.uuid4().hex[:8]}@unico.example",
        "token_hash": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        "role_name": "admin",
        "status": "invited",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "created_by": overrides.pop("created_by"),
    }
    payload.update(overrides)
    return local_db.table("platform_admin_invitations").insert(payload).execute().data[0]


def _expect_refused(fragment: str, call) -> None:
    with pytest.raises(Exception) as excinfo:  # noqa: BLE001 - any DB refusal
        call()
    assert fragment in str(excinfo.value).lower(), str(excinfo.value)


# ===========================================================================
# The Phase 7.15 columns physically exist and are readable/writable
# ===========================================================================


def test_the_delivery_and_verification_columns_exist(local_db) -> None:
    """A missing column would make the whole service layer fail at runtime."""
    row = local_db.table("platform_admin_invitations").select(
        "invitation_id, email_verified_at, email_delivery_status, "
        "email_delivery_at, email_delivery_attempts, resend_count, last_sent_at"
    ).limit(1).execute()
    assert row is not None


def test_a_new_invitation_defaults_to_a_pending_delivery(local_db, institution_id, actor_id) -> None:
    created_by = actor_id

    row = _insert_invitation(
        local_db, institution_id=institution_id, created_by=created_by
    )
    assert row["email_delivery_status"] == "pending"
    assert row["email_delivery_attempts"] == 0
    assert row["resend_count"] == 0
    assert row["email_verified_at"] is None


def test_only_the_three_delivery_statuses_are_representable(local_db, institution_id, actor_id) -> None:
    created_by = actor_id

    _expect_refused(
        "delivery_status",
        lambda: _insert_invitation(
            local_db,
            institution_id=institution_id,
            created_by=created_by,
            email_delivery_status="delivered",
        ),
    )


# ===========================================================================
# Token rotation: permitted while pending, refused once terminal
# ===========================================================================


def test_a_pending_invitation_token_can_be_rotated(local_db, institution_id, actor_id) -> None:
    """This is exactly what resend does, and the database must permit it."""
    created_by = actor_id

    row = _insert_invitation(
        local_db, institution_id=institution_id, created_by=created_by
    )
    new_hash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    updated = (
        local_db.table("platform_admin_invitations")
        .update({"token_hash": new_hash, "expires_at": "2099-06-01T00:00:00+00:00"})
        .eq("invitation_id", str(row["invitation_id"]))
        .eq("status", "invited")
        .execute()
        .data
    )
    assert updated and updated[0]["token_hash"] == new_hash


def test_a_terminal_invitation_token_cannot_be_rotated(local_db, institution_id, actor_id) -> None:
    """A cancelled or expired invitation keeps its digest forever."""
    created_by = actor_id

    for terminal, extra in (
        ("cancelled", {"cancelled_at": "2026-01-02T00:00:00+00:00"}),
        ("expired", {}),
    ):
        row = _insert_invitation(
            local_db, institution_id=institution_id, created_by=created_by
        )
        local_db.table("platform_admin_invitations").update(
            {"status": terminal, **extra}
        ).eq("invitation_id", str(row["invitation_id"])).execute()

        _expect_refused(
            "pending invitation token may be rotated",
            lambda row=row: local_db.table("platform_admin_invitations")
            .update({"token_hash": hashlib.sha256(uuid.uuid4().bytes).hexdigest()})
            .eq("invitation_id", str(row["invitation_id"]))
            .execute(),
        )


def test_an_invitation_can_never_be_repointed_at_another_institution(local_db, institution_id, actor_id) -> None:
    """The binding Phase 7.14 froze stays frozen in Phase 7.15."""
    created_by = actor_id

    institutions = (
        local_db.table("institutions").select("institution_id").execute().data
    )
    other = next(
        (
            str(r["institution_id"])
            for r in institutions
            if str(r["institution_id"]) != institution_id
        ),
        None,
    )
    if other is None:
        pytest.skip("only one seeded institution; nothing to cross to")
    row = _insert_invitation(
        local_db, institution_id=institution_id, created_by=created_by
    )
    _expect_refused(
        "identity is immutable",
        lambda: local_db.table("platform_admin_invitations")
        .update({"institution_id": other})
        .eq("invitation_id", str(row["invitation_id"]))
        .execute(),
    )


def test_verification_requires_an_accepted_invitation(local_db, institution_id, actor_id) -> None:
    """A still-pending invitation can never be made to look verified."""
    created_by = actor_id

    row = _insert_invitation(
        local_db, institution_id=institution_id, created_by=created_by
    )
    _expect_refused(
        "verified_requires_accepted",
        lambda: local_db.table("platform_admin_invitations")
        .update({"email_verified_at": "2026-01-02T00:00:00+00:00"})
        .eq("invitation_id", str(row["invitation_id"]))
        .execute(),
    )


# ===========================================================================
# Audit vocabulary: additive, with every event actually writable
# ===========================================================================


@pytest.mark.parametrize(
    "action",
    [
        "institution_admin_invitation_email_sent",
        "institution_admin_invitation_email_failed",
        "institution_admin_invitation_resent",
        "institution_admin_invitation_verified",
    ],
)
def test_each_new_audit_action_is_representable(local_db, institution_id, actor_id, action) -> None:
    created_by = actor_id

    written = (
        local_db.table("platform_institution_audit_log")
        .insert(
            {
                "actor_user_id": created_by,
                "action": action,
                "institution_id": institution_id,
                "result": "failed" if action.endswith("failed") else "success",
                "details": {"probe": True},
            }
        )
        .execute()
        .data
    )
    assert written and written[0]["action"] == action


def test_phase_7_14_audit_actions_still_work(local_db, institution_id, actor_id) -> None:
    """The migration is additive: no existing event was renamed or dropped."""
    created_by = actor_id

    for action in (
        "institution_admin_invited",
        "institution_admin_invitation_accepted",
        "institution_admin_invitation_expired",
        "institution_admin_invitation_cancelled",
        "institution_admin_revoked",
    ):
        written = (
            local_db.table("platform_institution_audit_log")
            .insert(
                {
                    "actor_user_id": created_by,
                    "action": action,
                    "institution_id": institution_id,
                    "result": "success",
                    "details": {},
                }
            )
            .execute()
            .data
        )
        assert written and written[0]["action"] == action


def test_the_migration_file_remains_an_ordered_ledger_entry() -> None:
    """Later phases may append migrations but cannot replace Phase 7.15."""
    assert MIGRATION.exists()
    siblings = sorted(p.name for p in MIGRATION.parent.glob("*.sql"))
    assert MIGRATION.name in siblings
    assert siblings.index(MIGRATION.name) < siblings.index(
        "20261002000000_phase_7_17_email_outbox_worker.sql"
    )
