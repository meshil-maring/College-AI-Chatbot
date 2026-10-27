"""Organization and institution foundation regressions: repository."""

from __future__ import annotations

from .support import (
    INST_A1,
    MagicMock,
    ORG_A,
    USER_ID,
    UUID,
    tenancy_repo,
)


# ============================================================================
# 2. ORGANIZATION -> INSTITUTION RELATIONSHIP (repository + resolution)
# ============================================================================


def test_organization_lookup_is_by_public_code_and_case_insensitive() -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value.ilike.return_value
    query.maybe_single.return_value.execute.return_value.data = {
        "organization_id": ORG_A
    }
    assert tenancy_repo.organization_code_exists(client, "nielit") is True
    client.table.assert_called_with("organizations")
    assert (
        client.table.return_value.select.return_value.ilike.call_args.args[0]
        == "organization_code"
    )


def test_list_institutions_for_organization_is_organization_scoped() -> None:
    client = MagicMock()
    rows = [{"institution_id": INST_A1, "organization_id": ORG_A}]
    query = client.table.return_value.select.return_value.eq.return_value
    query.order.return_value.execute.return_value.data = rows
    assert tenancy_repo.list_institutions_for_organization(client, ORG_A) == rows
    client.table.assert_called_with("institutions")
    assert client.table.return_value.select.return_value.eq.call_args.args == (
        "organization_id",
        ORG_A,
    )


def test_get_institution_organization_returns_the_owning_organization() -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value.eq.return_value
    query.maybe_single.return_value.execute.return_value.data = {
        "organization_id": ORG_A
    }
    assert tenancy_repo.get_institution_organization(client, INST_A1) == UUID(ORG_A)


def test_get_institution_organization_absent_row_resolves_to_none() -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value.eq.return_value
    query.maybe_single.return_value.execute.return_value.data = None
    assert tenancy_repo.get_institution_organization(client, INST_A1) is None


def test_insert_institution_carries_exactly_one_owning_organization() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"institution_id": INST_A1, "organization_id": ORG_A}
    ]
    tenancy_repo.insert_institution(
        client,
        organization_id=ORG_A,
        name="NIELIT Imphal",
        code="nielit-imphal",
        email="imphal@nielit.example",
        address="Imphal, Manipur",
    )
    payload = client.table.return_value.insert.call_args.args[0]
    assert payload["organization_id"] == ORG_A
    assert payload["code"] == "NIELIT-IMPHAL"  # normalised; still globally unique
    # A new institution starts unavailable until its organization admits it.
    assert payload["status"] == "pending"
    assert payload["is_active"] is False


def test_reject_cleanup_preserves_all_existing_memberships() -> None:
    """Pending requests grant nothing; rejecting one cannot revoke another grant."""
    client = MagicMock()
    tenancy_repo.remove_membership_on_reject(
        client, user_id=USER_ID, institution_id=INST_A1
    )
    client.table.assert_not_called()
    client.rpc.assert_not_called()
