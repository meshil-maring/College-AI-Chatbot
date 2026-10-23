"""Exercise offline release SQL in the caller's owned disposable database."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/maintenance/academic_decommission"))
from release_sql import guard, ledger_insert, literal, summary
from prepare_release import MIGRATION_SHA256, NAME, VERSION


def result_object(output: str, key: str) -> dict:
    for line in output.splitlines():
        if line.startswith("{"):
            value = json.loads(line)
            if key in value:
                return value
    raise RuntimeError(f"Missing release SQL evidence containing {key}")


def prepare_verified_release(
    container, paths, checked, sql_arguments, migration, expect_rollback
):
    """Return commit SQL only after refusal and rollback artifacts pass locally."""
    ledger = (
        "CREATE SCHEMA supabase_migrations; CREATE TABLE supabase_migrations.schema_migrations("
        "version text PRIMARY KEY,statements text[],name text);"
    )
    ledger += (
        "INSERT INTO supabase_migrations.schema_migrations(version) VALUES "
        + ",".join("(" + literal(path.name.split("_", 1)[0]) + ")" for path in paths)
        + ";"
    )
    checked(sql_arguments(container), sql=ledger)
    output = checked(
        sql_arguments(container),
        sql=(
            ROOT / "scripts/maintenance/academic_decommission/inspect.sql"
        ).read_text(),
    )
    inspection = result_object(output, "ledger")
    body = migration.replace("\nBEGIN;\n", "\n", 1).removesuffix("COMMIT;\n")

    def payload(expected, ending):
        return (
            guard(expected)
            + body
            + ledger_insert(migration, expected["ledger_columns"], VERSION, NAME)
            + summary(VERSION, MIGRATION_SHA256, ending)
        )

    wrong = deepcopy(inspection)
    wrong["tables"][0]["fingerprint"] = "0" * 32
    expect_rollback(container, payload(wrong, "ROLLBACK"), "Inspected data changed")
    rehearsal = result_object(
        checked(sql_arguments(container), sql=payload(inspection, "ROLLBACK")),
        "migration_version",
    )
    if (
        rehearsal["remaining_retired_tables"] != 0
        or rehearsal["retired_table_count"] != 39
        or not rehearsal["ledger_version_exists"]
    ):
        raise RuntimeError(
            "Release rehearsal did not verify bounded schema removal and atomic ledger entry"
        )
    restored = checked(
        sql_arguments(container),
        sql="SELECT to_regclass('public.programs') IS NOT NULL "
        "AND NOT EXISTS(SELECT 1 FROM supabase_migrations.schema_migrations WHERE version='20261023000000')",
    )
    if restored != "t":
        raise RuntimeError(
            "Release rehearsal failed to restore schema and migration ledger"
        )
    print(
        "PASS: release guards reject changed snapshots; rehearsal restores schema/data/ledger together",
        flush=True,
    )
    return payload(inspection, "COMMIT")
