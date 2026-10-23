"""Prepare scoped live release artifacts offline from read-only inspection JSON."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from release_sql import guard, ledger_insert, summary

ROOT = Path(__file__).resolve().parents[3]
VERSION = "20261023000000"
NAME = "decommission_academic_domain"
PROJECT = "rjnfmjcvkfotneswpygr"
INSTITUTION = {
    "institution_id": "93d79749-0164-4cbf-b378-5fdff295d7af",
    "code": "QUEST123",
}
LEDGER_SHA256 = "9b87d3f5c31ab2e80f8cbacf15e57f47038cfdc45a87ad9301ba8076c892bb99"
MIGRATION_SHA256 = "7c3a06e4773093d7f1a358bd996c3a860137fa306a6817759cca1ea0f59d809c"


def load_inspection(path: Path) -> dict:
    captured = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = captured.get("rows") if isinstance(captured, dict) else None
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("Expected one CLI inspection result row")
    inspection = rows[0].get("academic_decommission_inspection")
    if not isinstance(inspection, dict):
        raise ValueError("Missing academic decommission inspection")
    if (
        inspection.get("project_ref") != PROJECT
        or inspection.get("principal") != "postgres"
        or inspection.get("database") != "postgres"
    ):
        raise ValueError(
            "Inspection does not match the pinned project/database/principal"
        )
    if inspection.get("institutions") != [INSTITUTION]:
        raise ValueError("Expected only the explicitly authorized Quest institution")
    ledger = inspection.get("ledger")
    if (
        not isinstance(ledger, list)
        or len(ledger) != 43
        or any(not isinstance(v, str) or not re.fullmatch(r"\d{14}", v) for v in ledger)
    ):
        raise ValueError("Expected the observed 43-migration ledger")
    if (
        sha256(json.dumps(ledger, separators=(",", ":")).encode()).hexdigest()
        != LEDGER_SHA256
    ):
        raise ValueError("Inspection differs from the pinned 43 migration versions")
    columns = inspection.get("ledger_columns")
    if not isinstance(columns, list) or not any(
        c.get("name") == "version" and c.get("type") == "text" for c in columns
    ):
        raise ValueError("Unsupported migration ledger version contract")
    for column in columns:
        expected_type = {"version": "text", "name": "text", "statements": "ARRAY"}.get(
            column.get("name")
        )
        if expected_type is not None and column.get("type") != expected_type:
            raise ValueError("Unsupported migration ledger column type")
        if (
            expected_type is None
            and column.get("nullable") != "YES"
            and column.get("default") is None
        ):
            raise ValueError("Unrecognized required migration ledger column")
    tables = inspection.get("tables")
    if (
        not isinstance(tables, list)
        or not tables
        or len({(t.get("schema_name"), t.get("table_name")) for t in tables})
        != len(tables)
    ):
        raise ValueError("Expected unique application-table snapshots")
    for table in tables:
        if table.get("schema_name") not in {"public", "auth"} or (
            table["schema_name"] == "auth" and table.get("table_name") != "users"
        ):
            raise ValueError("Unexpected table snapshot scope")
        if (
            not isinstance(table.get("row_count"), int)
            or table["row_count"] < 0
            or not re.fullmatch(r"[a-f0-9]{32}", table.get("fingerprint", ""))
        ):
            raise ValueError("Malformed table count/fingerprint")
    if not any(
        t["schema_name"] == "auth" and t["table_name"] == "users" for t in tables
    ):
        raise ValueError("Auth identity preservation snapshot is required")
    if not isinstance(inspection.get("routines"), list):
        raise ValueError("Application routine snapshots are required")
    return inspection


def render(inspection: dict) -> tuple[str, str]:
    path = ROOT / f"supabase/migrations/{VERSION}_{NAME}.sql"
    migration = path.read_text(encoding="utf-8")
    if sha256(path.read_bytes()).hexdigest() != MIGRATION_SHA256:
        raise ValueError("Migration differs from the reviewed and tested frozen source")
    if migration.count("\nBEGIN;\n") != 1 or not migration.endswith("COMMIT;\n"):
        raise ValueError(
            "Expected generated migration with exactly one outer transaction"
        )
    body = migration.replace("\nBEGIN;\n", "\n", 1).removesuffix("COMMIT;\n")
    payload = (
        "-- Prepared offline; execute only against explicitly pinned Supabase project.\n"
        + guard(inspection)
    )
    payload += (
        body
        + "\n"
        + ledger_insert(migration, inspection["ledger_columns"], VERSION, NAME)
    )
    return tuple(
        payload + summary(VERSION, MIGRATION_SHA256, ending)
        for ending in ("ROLLBACK", "COMMIT")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inspection", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "logs/backend/academic-decommission-release",
    )
    args = parser.parse_args()
    directory = args.output_dir.resolve()
    if (
        not directory.is_relative_to((ROOT / "logs/backend").resolve())
        or directory == (ROOT / "logs/backend").resolve()
    ):
        raise ValueError(
            "Generated release SQL must remain in a dedicated ignored backend-log folder"
        )
    inspection = load_inspection(args.inspection)
    rehearsal, commit = render(inspection)
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in (("rehearsal.sql", rehearsal), ("commit.sql", commit)):
        (directory / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"Prepared scoped release SQL offline in {directory.relative_to(ROOT)}")
    print(
        f"Migration SHA256: {MIGRATION_SHA256}; ledger: 43 versions; institution: QUEST123"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
