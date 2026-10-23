"""Verify academic removal only in an owned, network-isolated local PostgreSQL."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/validation"))
from disposable_container import (
    EXPECTED_IMAGE, docker_arguments, expected_name, validate_cleanup_target,
    validate_disposable_target, validate_local_engine,
)
from release_contracts import prepare_verified_release

MIGRATION = "20261023000000_decommission_academic_domain.sql"


def checked(arguments: list[str], *, sql: str | None = None, timeout: int = 120) -> str:
    result = subprocess.run(arguments, input=sql, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-12000:] or result.stdout[-12000:])
    return result.stdout.strip()


def validate_with_retry(validator, *arguments):
    for attempt in range(3):
        try:
            return validator(*arguments)
        except subprocess.TimeoutExpired:
            if attempt == 2:
                raise
            print("Retrying local Docker ownership validation", flush=True)


def sql_arguments(container: str) -> list[str]:
    return docker_arguments("exec", "-i", container, "psql", "-U", "postgres", "-d", "postgres",
                            "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose", "-At")


def expect_rollback(container: str, migration: str, expected: str) -> None:
    result = subprocess.run(sql_arguments(container), input=migration, capture_output=True,
                            text=True, timeout=120)
    if result.returncode == 0 or expected not in result.stderr:
        raise RuntimeError(f"Expected atomic rejection containing {expected!r}: {result.stderr[-5000:]}")
    retained = checked(sql_arguments(container), sql="SELECT to_regclass('public.programs') IS NOT NULL "
        "AND to_regprocedure('public.academic_package_command(uuid,uuid,text,jsonb)') IS NOT NULL")
    if retained != "t":
        raise RuntimeError("A rejected decommission left partial schema removal")
    print(f"PASS: {expected}; all preceding removal rolled back", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-baseline", action="store_true")
    args = parser.parse_args()
    validate_with_retry(validate_local_engine)
    checked([sys.executable, str(ROOT / "scripts/maintenance/migrations/build_academic_decommission.py"), "--check"])
    token, purpose = uuid4().hex, "academic-setup"
    container = None
    try:
        container = checked(docker_arguments(
            "run", "--pull=never", "--rm", "-d", "--network", "none",
            "--tmpfs", "/var/lib/postgresql/data:rw,size=536870912",
            "--name", expected_name(token, purpose), "--label", "collegeai.validation.disposable=true",
            "--label", f"collegeai.validation.run={token}", "--label", f"collegeai.validation.purpose={purpose}",
            "-e", "PGDATA=/var/lib/postgresql/data", "-e", f"POSTGRES_PASSWORD={uuid4().hex}", EXPECTED_IMAGE,
        ))
        if not re.fullmatch(r"[a-f0-9]{64}", container):
            raise RuntimeError("Expected full disposable container identifier")
        validate_with_retry(validate_disposable_target, container, token, purpose)
        for _ in range(100):
            ready = subprocess.run(docker_arguments("exec", container, "pg_isready", "-U", "postgres"),
                                   capture_output=True, timeout=10)
            if ready.returncode == 0:
                process = checked(docker_arguments("exec", container, "cat", "/proc/1/comm"))
                if re.match(r"^\.?postgres(?:-|$)", process):
                    break
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable PostgreSQL did not become ready")
        directory = ROOT / "supabase/migrations"
        excluded = {"20261017000000_b05_invitation_acceptance_security.sql",
                    "20261019000000_student_approval_deployment_repair.sql"} if args.remote_baseline else set()
        paths = [p for p in sorted(directory.glob("*.sql")) if p.name < MIGRATION and p.name not in excluded]
        checked(docker_arguments("cp", str(directory), f"{container}:/tmp/migrations"))
        for path in paths:
            print(f"REPLAY {path.name}", flush=True)
            checked(docker_arguments("exec", container, "psql", "-U", "postgres", "-d", "postgres",
                                     "-v", "ON_ERROR_STOP=1", "-q", "-f", f"/tmp/migrations/{path.name}"))
        if args.remote_baseline:
            absent = checked(sql_arguments(container), sql="SELECT to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NULL "
                "AND NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name='admin_audit_log' AND column_name='decision_key')")
            if absent != 't':
                raise RuntimeError('Remote-like baseline already has approval artifacts; conditional adapter was not exercised')
        fixture_dir = Path(__file__).parent
        print(checked(sql_arguments(container), sql=(fixture_dir / "seed.sql").read_text()), flush=True)
        migration = (directory / MIGRATION).read_text(encoding="utf-8")
        release = prepare_verified_release(container, paths, checked, sql_arguments, migration, expect_rollback)
        checked(sql_arguments(container), sql="CREATE TABLE public.retained_dependency_probe("
            "id uuid PRIMARY KEY, program uuid REFERENCES public.programs(program_id))")
        expect_rollback(container, migration, "Unexpected preserved-table foreign key")
        checked(sql_arguments(container), sql="DROP TABLE public.retained_dependency_probe")
        checked(sql_arguments(container), sql="CREATE TABLE public.retained_permission_probe("
            "permission uuid REFERENCES public.permissions(permission_id) ON DELETE CASCADE)")
        expect_rollback(container, migration, "Unexpected consumer of academic permission identities")
        checked(sql_arguments(container), sql="DROP TABLE public.retained_permission_probe")
        checked(sql_arguments(container), sql="CREATE FUNCTION public.retained_dependency_probe() RETURNS SETOF public.programs "
            "LANGUAGE sql AS 'SELECT * FROM public.programs'")
        expect_rollback(container, migration, "depend")
        checked(sql_arguments(container), sql="DROP FUNCTION public.retained_dependency_probe()")
        tamper = migration.replace("-- SOURCE verification.sql", "UPDATE public.users SET first_name='Tamper probe' "
            "WHERE id=(SELECT value FROM academic_decommission_fixture.ids WHERE name='admin');\n-- SOURCE verification.sql", 1)
        expect_rollback(container, tamper, "Preserved data changed")
        print("APPLY decommission after all negative contracts", flush=True)
        print(checked(sql_arguments(container), sql=release), flush=True)
        print(checked(sql_arguments(container), sql=(fixture_dir / "contracts.sql").read_text()), flush=True)
        print(checked(sql_arguments(container), sql=(fixture_dir / "approval.sql").read_text()), flush=True)
        mode = "remote-like ledger" if args.remote_baseline else "complete local ledger"
        print(f"PASS: {len(paths)} prior migrations ({mode}); removal, rollback and account/nonacademic preservation", flush=True)
        return 0
    finally:
        if container and re.fullmatch(r"[a-f0-9]{64}", container):
            owned = validate_with_retry(validate_cleanup_target, container, token, purpose)
            checked(docker_arguments("stop", "--timeout", "10", owned))


if __name__ == "__main__":
    raise SystemExit(main())
