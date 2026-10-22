"""Replay and test packages using a fresh, owned, network-isolated PostgreSQL."""

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
from concurrency_contract import verify_concurrency


def checked(arguments: list[str], *, timeout: int = 120) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-12000:] or result.stdout[-12000:])
    return result.stdout.strip()


def validate_with_retry(validator, *arguments):
    """Retry a slow Docker response without relaxing any ownership checks."""
    for attempt in range(3):
        try:
            return validator(*arguments)
        except subprocess.TimeoutExpired:
            if attempt == 2:
                raise
            print("Retrying Docker validation after a local engine timeout", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-baseline", action="store_true",
                        help="Match the installed ledger without unrelated B05 draft/approval migrations")
    args = parser.parse_args()
    validate_with_retry(validate_local_engine)
    checked([sys.executable, str(ROOT / "scripts/maintenance/migrations/build_academic_packages.py"), "--check"])
    token, purpose = uuid4().hex, "academic-setup"
    container = None
    try:
        container = checked(docker_arguments(
            "run", "--pull=never", "--rm", "-d", "--network", "none",
            "--tmpfs", "/var/lib/postgresql/data:rw,size=536870912",
            "--name", expected_name(token, purpose),
            "--label", "collegeai.validation.disposable=true",
            "--label", f"collegeai.validation.run={token}",
            "--label", f"collegeai.validation.purpose={purpose}",
            "-e", "PGDATA=/var/lib/postgresql/data",
            "-e", f"POSTGRES_PASSWORD={uuid4().hex}", EXPECTED_IMAGE,
        ))
        if not re.fullmatch(r"[a-f0-9]{64}", container):
            raise RuntimeError("Docker did not return a full disposable container ID")
        validate_with_retry(validate_disposable_target, container, token, purpose)
        for _ in range(100):
            ready = subprocess.run(docker_arguments("exec", container, "pg_isready", "-U", "postgres"),
                                   capture_output=True, timeout=10)
            if ready.returncode == 0:
                # The image briefly starts a temporary server during initialization.
                # Wait for its final PID 1 server before replaying schema changes.
                process = checked(docker_arguments("exec", container, "cat", "/proc/1/comm"))
                if re.match(r"^\.?postgres(?:-|$)", process):
                    break
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable PostgreSQL did not become ready")
        migrations = ROOT / "supabase/migrations"
        checked(docker_arguments("cp", str(migrations), f"{container}:/tmp/migrations"))
        excluded = {"20261017000000_b05_invitation_acceptance_security.sql",
                    "20261019000000_student_approval_deployment_repair.sql"} if args.remote_baseline else set()
        replayed = [path for path in sorted(migrations.glob("*.sql")) if path.name not in excluded]
        for path in replayed:
            print(f"REPLAY {path.name}", flush=True)
            checked(docker_arguments("exec", container, "psql", "-U", "postgres", "-d", "postgres",
                                     "-v", "ON_ERROR_STOP=1", "-q", "-f", f"/tmp/migrations/{path.name}"))
        if args.remote_baseline:
            absent = checked(docker_arguments("exec", container, "psql", "-U", "postgres", "-d", "postgres", "-Atc",
                "SELECT to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name='admin_audit_log' AND column_name='decision_key')"))
            if absent != "t":
                raise RuntimeError("Remote-like baseline unexpectedly includes unrelated B05 approval artifacts")
        package_fixtures = sorted(Path(__file__).parent.glob("*.sql"))
        if not package_fixtures:
            raise RuntimeError("No package SQL contract fixtures found")
        legacy_fixtures = [ROOT / "scripts/validation" / name for name in (
            "academic_setup_sql_lint.sql", "academic_setup_database.sql",
            "faculty_responsibilities_database.sql", "faculty_attendance_database.sql",
            "faculty_tests_database.sql",
        )]
        fixtures = [*legacy_fixtures, *package_fixtures]
        if args.remote_baseline:
            fixture_names = {"academic_package_lint.sql", "academic_package_seed.sql",
                             "academic_package_zzzzzzz_teaching.sql"}
            fixtures = [path for path in package_fixtures if path.name in fixture_names]
        for path in fixtures:
            print(f"CONTRACT {path.name}", flush=True)
            checked(docker_arguments("cp", str(path), f"{container}:/tmp/{path.name}"))
            output = checked(docker_arguments("exec", container, "psql", "-U", "postgres", "-d", "postgres",
                                              "-v", "ON_ERROR_STOP=1", "-f", f"/tmp/{path.name}"))
            print(output, flush=True)
        if not args.remote_baseline:
            verify_concurrency(container, token, purpose, docker_arguments, checked)
            legacy_races = checked([
                sys.executable, str(ROOT / "scripts/validation/academic_setup_concurrency.py"),
                container, token, purpose,
            ], timeout=180)
            print(legacy_races, flush=True)
        mode = "remote-like baseline, no B05 artifacts; lint/preparation/assignment" if args.remote_baseline else "legacy/package SQL and concurrency contracts"
        print(f"PASS: {len(replayed)} migrations; {mode}", flush=True)
        return 0
    finally:
        if container and re.fullmatch(r"[a-f0-9]{64}", container):
            owned = validate_with_retry(validate_cleanup_target, container, token, purpose)
            checked(docker_arguments("stop", "--timeout", "10", owned))


if __name__ == "__main__":
    raise SystemExit(main())
