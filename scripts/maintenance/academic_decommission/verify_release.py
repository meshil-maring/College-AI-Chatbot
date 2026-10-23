"""Verify committed release evidence offline without exporting private row data."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from prepare_release import MIGRATION_SHA256, ROOT, VERSION, load_inspection


def evidence(path: Path, name: str) -> dict:
    captured = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = captured.get("rows", [])
    if len(rows) != 1 or not isinstance(rows[0].get(name), dict):
        raise ValueError(f"Expected one {name} evidence row")
    return rows[0][name]


def demand(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def manifest() -> tuple[set[str], set[str]]:
    migration = (
        ROOT / "supabase/migrations/20261023000000_decommission_academic_domain.sql"
    )
    demand(
        sha256(migration.read_bytes()).hexdigest() == MIGRATION_SHA256,
        "Frozen migration changed",
    )
    scope = (
        ROOT / "supabase/migration_sources/academic_decommission/scope.sql"
    ).read_text()
    tables, remainder = scope.split(
        "CREATE TEMP TABLE academic_decommission_functions", 1
    )
    functions = remainder.split(
        "CREATE TEMP TABLE academic_decommission_permissions", 1
    )[0]
    retired_tables = set(re.findall(r"\('([a-z0-9_]+)'\)", tables))
    retired_functions = set(re.findall(r"\('([a-z0-9_]+)'\)", functions))
    demand(
        len(retired_tables) == 39 and len(retired_functions) == 71,
        "Unexpected retirement manifest",
    )
    return retired_tables, retired_functions


def routine_name(identity: str) -> str:
    return identity.split("(", 1)[0].split(".")[-1].strip('"')


def verify(before: dict, after: dict, commit: dict, checks: dict) -> dict:
    retired_tables, retired_functions = manifest()
    for key in (
        "project_ref",
        "database",
        "principal",
        "institutions",
        "ledger_columns",
    ):
        demand(
            after.get(key) == before[key],
            f"Retained deployment identity/contract changed: {key}",
        )
    demand(
        after.get("ledger") == sorted([*before["ledger"], VERSION]),
        "Expected exact prior ledger plus one release",
    )
    old = {(t["schema_name"], t["table_name"]): t for t in before["tables"]}
    new = {(t["schema_name"], t["table_name"]): t for t in after["tables"]}
    removed = {("public", name) for name in retired_tables}
    demand(removed <= old.keys(), "Before-evidence lacks retired tables")
    demand(
        new.keys() == old.keys() - removed, "Unexpected post-release table inventory"
    )
    permission_tables = {"permissions", "role_permissions", "user_permission_grants"}
    unchanged = 0
    for key, current in new.items():
        previous = old[key]
        if key[0] == "public" and key[1] in permission_tables:
            demand(
                current["row_count"] <= previous["row_count"],
                "Permission rows increased unexpectedly",
            )
            if current["row_count"] == previous["row_count"]:
                demand(
                    current["fingerprint"] == previous["fingerprint"],
                    "Unremoved permission rows changed",
                )
        elif key == ("public", "students") and previous["row_count"] > 0:
            # The frozen migration compared every identity row after removing
            # only the two retired academic keys. Full-row hashes necessarily
            # differ when those keys existed, so use its atomic proof here.
            demand(
                current["row_count"] == previous["row_count"],
                "Student identity count changed",
            )
        else:
            demand(current == previous, f"Retained rows changed in {key[0]}.{key[1]}")
            unchanged += 1
    demand(
        old[("public", "permissions")]["row_count"]
        - new[("public", "permissions")]["row_count"]
        == 31,
        "Expected exactly 31 retired permission identities",
    )
    old_routines = {r["identity"]: r["fingerprint"] for r in before["routines"]}
    new_routines = {r["identity"]: r["fingerprint"] for r in after["routines"]}
    demand(
        retired_functions <= {routine_name(identity) for identity in old_routines},
        "Before-evidence lacks retired routines",
    )
    retained = {
        identity: fingerprint
        for identity, fingerprint in old_routines.items()
        if routine_name(identity) not in retired_functions
    }
    demand(
        not any(
            routine_name(identity) in retired_functions for identity in new_routines
        ),
        "Retired routine remains",
    )
    added = new_routines.keys() - retained.keys()
    expected_added = (
        set()
        if any(routine_name(identity) == "b05_approve_student" for identity in retained)
        else {
            identity
            for identity in new_routines
            if routine_name(identity) == "b05_approve_student"
        }
    )
    approval_existed = any(
        routine_name(identity) == "b05_approve_student" for identity in retained
    )
    demand(
        len(expected_added) == (0 if approval_existed else 1)
        and added == expected_added,
        "Unexpected nonacademic routine added",
    )
    demand(retained.keys() <= new_routines.keys(), "Retained routine was removed")
    for identity, fingerprint in retained.items():
        if routine_name(identity) != "phase81_manage_staff_permission_grants":
            demand(
                new_routines[identity] == fingerprint,
                f"Retained routine changed: {identity}",
            )
    expected_commit = {
        "migration_version": VERSION,
        "migration_sha256": MIGRATION_SHA256,
        "transaction_end": "COMMIT",
        "retired_table_count": 39,
        "retired_routine_name_count": 71,
        "retired_permission_count": 31,
        "remaining_retired_tables": 0,
        "remaining_retired_routines": 0,
        "preserved_table_count": len(new),
        "preserved_row_count": sum(t["row_count"] for t in new.values()),
        "auth_user_count": new[("auth", "users")]["row_count"],
        "application_user_count": new[("public", "users")]["row_count"],
        "user_role_count": new[("public", "user_roles")]["row_count"],
        "institution_count": new[("public", "institutions")]["row_count"],
        "student_identity_count": new[("public", "students")]["row_count"],
        "approval_rpc_present": True,
        "ledger_version_exists": True,
    }
    for key, expected in expected_commit.items():
        demand(commit.get(key) == expected, f"Atomic commit proof differs: {key}")
    expected_checks = {
        "student_academic_columns": [],
        "student_identity_columns": sorted(
            [
                "student_id",
                "user_id",
                "institution_id",
                "email",
                "approval_status",
                "status",
                "is_active",
            ]
        ),
        "approval_rpc_present": True,
        "approval_authenticated_execute": False,
        "approval_service_role_execute": True,
        "retired_permissions_remaining": 0,
        "release_ledger_count": 1,
    }
    for key, expected in expected_checks.items():
        demand(
            checks.get(key) == expected,
            f"Post-release identity/security check differs: {key}",
        )
    return {
        "status": "PASS",
        "migration_version": VERSION,
        "retired_tables": 39,
        "retired_routine_names": 71,
        "retired_permissions": 31,
        "retained_tables": len(new),
        "unchanged_table_fingerprints": unchanged,
        "auth_accounts_preserved": expected_commit["auth_user_count"],
        "ledger_versions": len(after["ledger"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "after", "commit", "postchecks"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = verify(
        load_inspection(args.before),
        evidence(args.after, "academic_decommission_inspection"),
        evidence(args.commit, "academic_decommission_release"),
        evidence(args.postchecks, "academic_decommission_postchecks"),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
