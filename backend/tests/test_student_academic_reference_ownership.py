"""Student academic ownership checks using mocked database responses."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.errors import AppError
from app.services.admin import admin_academics as svc

INSTITUTION_ID = str(uuid4())
FOREIGN_INSTITUTION_ID = str(uuid4())
STUDENT_ID = str(uuid4())
PROGRAM_ID = str(uuid4())
YEAR_ID = str(uuid4())


def _set_lookup(table, row, *, no_response=False):
    table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        None if no_response else SimpleNamespace(data=row)
    )


@pytest.fixture
def student_db(monkeypatch):
    db = MagicMock()
    tables = {name: MagicMock() for name in ("students", "programs", "academic_years")}
    db.table.side_effect = tables.__getitem__
    _set_lookup(tables["students"], {
        "student_id": STUDENT_ID,
        "institution_id": INSTITUTION_ID,
        "program_id": PROGRAM_ID,
        "academic_year_id": YEAR_ID,
    })
    _set_lookup(tables["programs"], {
        "program_id": PROGRAM_ID,
        "departments": {"institution_id": INSTITUTION_ID},
    })
    _set_lookup(tables["academic_years"], {
        "academic_year_id": YEAR_ID,
        "institution_id": INSTITUTION_ID,
    })
    saved = SimpleNamespace(data=[{"student_id": STUDENT_ID}])
    tables["students"].insert.return_value.execute.return_value = saved
    tables["students"].update.return_value.eq.return_value.execute.return_value = saved
    monkeypatch.setattr(svc, "get_admin_client", lambda: db)
    return db, tables


def _write_student(operation, fields):
    if operation == "create":
        return svc.create_student(svc.StudentCreate(
            user_id=uuid4(), institution_id=INSTITUTION_ID,
            student_number="S001", enrollment_date="2026-08-01", **fields,
        ))
    return svc.update_student(STUDENT_ID, svc.StudentUpdate(**fields))


def _assert_no_writes(tables):
    for table in tables.values():
        table.insert.assert_not_called()
        table.update.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("table,row,no_response,code,status", [
    ("programs", {"departments": {"institution_id": FOREIGN_INSTITUTION_ID}}, False,
     "TENANT_MISMATCH", 403),
    ("academic_years", {"institution_id": FOREIGN_INSTITUTION_ID}, False,
     "TENANT_MISMATCH", 403),
    ("programs", None, False, "PROGRAM_NOT_FOUND", 404),
    ("programs", None, True, "PROGRAM_NOT_FOUND", 404),
    ("academic_years", None, False, "ACADEMIC_CONTEXT_INVALID", 404),
    ("academic_years", None, True, "ACADEMIC_CONTEXT_INVALID", 404),
    ("programs", {"departments": None}, False, "PROGRAM_NOT_FOUND", 404),
    ("programs", {"departments": {}}, False, "PROGRAM_NOT_FOUND", 404),
    ("programs", {"departments": {"institution_id": None}}, False,
     "PROGRAM_NOT_FOUND", 404),
    ("academic_years", {"institution_id": None}, False, "ACADEMIC_CONTEXT_INVALID", 404),
])
def test_student_rejects_invalid_academic_references_before_write(
    student_db, operation, table, row, no_response, code, status,
):
    _, tables = student_db
    _set_lookup(tables[table], row, no_response=no_response)
    # Include both references so a valid first lookup cannot permit a partial write.
    with pytest.raises(AppError) as exc:
        _write_student(operation, {"program_id": PROGRAM_ID, "academic_year_id": YEAR_ID})
    assert (exc.value.code, exc.value.status_code) == (code, status)
    _assert_no_writes(tables)


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("owner_type", [str, UUID])
def test_student_accepts_same_institution_academic_references(student_db, operation, owner_type):
    _, tables = student_db
    _set_lookup(tables["programs"], {"departments": {"institution_id": owner_type(INSTITUTION_ID)}})
    _set_lookup(tables["academic_years"], {"institution_id": owner_type(INSTITUTION_ID)})
    fields = {"program_id": PROGRAM_ID, "academic_year_id": YEAR_ID}
    assert _write_student(operation, fields) == {"student_id": STUDENT_ID}
    writer = tables["students"].insert if operation == "create" else tables["students"].update
    writer.assert_called_once()
    persisted = writer.call_args.args[0]
    assert {key: persisted[key] for key in fields} == fields
    tables["programs"].select.assert_called_once_with("program_id, departments(institution_id)")
    tables["programs"].select.return_value.eq.assert_called_once_with("program_id", PROGRAM_ID)
    tables["academic_years"].select.assert_called_once_with("academic_year_id, institution_id")
    tables["academic_years"].select.return_value.eq.assert_called_once_with("academic_year_id", YEAR_ID)


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("fields", [
    {"program_id": None, "academic_year_id": None},
    {"program_id": None, "academic_year_id": YEAR_ID},
    {"program_id": PROGRAM_ID, "academic_year_id": None},
])
def test_student_preserves_supported_null_references(student_db, operation, fields):
    _, tables = student_db
    _write_student(operation, fields)
    writer = tables["students"].insert if operation == "create" else tables["students"].update
    persisted = writer.call_args.args[0]
    assert {key: persisted[key] for key in fields} == fields
    for field, table in (("program_id", "programs"), ("academic_year_id", "academic_years")):
        if fields[field] is None:
            tables[table].select.assert_not_called()


def test_create_student_allows_omitted_academic_references(student_db):
    _, tables = student_db
    _write_student("create", {})
    persisted = tables["students"].insert.call_args.args[0]
    assert persisted["program_id"] is None
    assert persisted["academic_year_id"] is None
    tables["programs"].select.assert_not_called()
    tables["academic_years"].select.assert_not_called()


@pytest.mark.parametrize("fields,unused_table", [
    ({"program_id": PROGRAM_ID}, "academic_years"),
    ({"academic_year_id": YEAR_ID}, "programs"),
    ({"student_number": "S002"}, "programs"),
])
def test_student_partial_update_preserves_omitted_references(student_db, fields, unused_table):
    _, tables = student_db
    _write_student("update", fields)
    tables["students"].update.assert_called_once_with(fields)
    tables[unused_table].select.assert_not_called()
    if "academic_year_id" not in fields:
        tables["academic_years"].select.assert_not_called()


@pytest.mark.parametrize("field,table", [
    ("program_id", "programs"), ("academic_year_id", "academic_years"),
])
@pytest.mark.parametrize("foreign_reference", [False, True])
def test_student_update_uses_existing_institution_despite_forged_payload(
    student_db, field, table, foreign_reference,
):
    _, tables = student_db
    if foreign_reference:
        row = {"institution_id": FOREIGN_INSTITUTION_ID}
        _set_lookup(tables[table], {"departments": row} if table == "programs" else row)
    fields = {field: PROGRAM_ID if field == "program_id" else YEAR_ID,
              "institution_id": FOREIGN_INSTITUTION_ID}
    if foreign_reference:
        with pytest.raises(AppError) as exc:
            _write_student("update", fields)
        assert exc.value.code == "TENANT_MISMATCH"
        _assert_no_writes(tables)
    else:
        _write_student("update", fields)
        tables["students"].update.assert_called_once_with({field: fields[field]})


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("table", ["programs", "academic_years"])
def test_student_lookup_failure_prevents_writes(student_db, operation, table):
    _, tables = student_db
    tables[table].select.return_value.eq.return_value.maybe_single.return_value.execute.side_effect = (
        RuntimeError("Academic lookup unavailable")
    )
    with pytest.raises(RuntimeError, match="Academic lookup unavailable"):
        _write_student(operation, {"program_id": PROGRAM_ID, "academic_year_id": YEAR_ID})
    _assert_no_writes(tables)


def test_student_update_missing_target_prevents_writes(student_db):
    _, tables = student_db
    _set_lookup(tables["students"], None, no_response=True)
    with pytest.raises(AppError) as exc:
        _write_student("update", {"program_id": PROGRAM_ID, "academic_year_id": YEAR_ID})
    assert exc.value.code == "STUDENT_NOT_FOUND"
    _assert_no_writes(tables)
    tables["programs"].select.assert_not_called()
    tables["academic_years"].select.assert_not_called()
