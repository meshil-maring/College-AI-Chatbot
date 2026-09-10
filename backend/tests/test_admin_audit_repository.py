"""Phase Admin-2 tests for the admin audit repository."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories import admin_audit as repo
from app.schemas.admin import AdminAuditLogCreate

ACTOR_ID = uuid4()
AUDIT_ID = uuid4()


def test_record_admin_action_inserts_serialized_payload() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"audit_id": str(AUDIT_ID)}
    ]

    payload = AdminAuditLogCreate(
        actor_user_id=ACTOR_ID,
        action="faq.update",
        table_name="faqs",
        record_id="1",
        record_data={"answer": "A2"},
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    row = repo.record_admin_action(client, payload)

    assert row == {"audit_id": str(AUDIT_ID)}
    client.table.assert_called_once_with("admin_audit_log")
    inserted = client.table.return_value.insert.call_args.args[0]
    assert inserted["actor_user_id"] == str(ACTOR_ID)
    assert inserted["action"] == "faq.update"
    assert inserted["table_name"] == "faqs"
    assert inserted["record_id"] == "1"
    assert inserted["record_data"] == {"answer": "A2"}
    assert inserted["status"] == "success"


def test_get_audit_entry_returns_row_or_none() -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "audit_id": str(AUDIT_ID)
    }

    row = repo.get_audit_entry(client, AUDIT_ID)

    assert row == {"audit_id": str(AUDIT_ID)}
    client.table.assert_called_once_with("admin_audit_log")
    client.table.return_value.select.return_value.eq.assert_called_once_with(
        "audit_id", str(AUDIT_ID)
    )


def test_list_audit_entries_orders_by_performed_at_desc() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain.order.return_value.limit.return_value.execute.return_value.data = [
        {"audit_id": str(AUDIT_ID)}
    ]

    rows = repo.list_audit_entries(client)

    assert rows == [{"audit_id": str(AUDIT_ID)}]
    client.table.assert_called_once_with("admin_audit_log")
    chain.order.assert_called_once_with("performed_at", desc=True)
    chain.eq.assert_not_called()


def test_list_audit_entries_applies_all_filters() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain.eq.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    rows = repo.list_audit_entries(
        client,
        actor_user_id=ACTOR_ID,
        table_name="faqs",
        action="faq.update",
        status="success",
    )

    assert rows == []
    first_eq = chain.eq
    first_eq.assert_called_once_with("actor_user_id", str(ACTOR_ID))
    assert first_eq.return_value.eq.call_args.args == ("table_name", "faqs")
    assert first_eq.return_value.eq.return_value.eq.call_args.args == (
        "action",
        "faq.update",
    )
    assert (
        first_eq.return_value.eq.return_value.eq.return_value.eq.call_args.args
        == ("status", "success")
    )