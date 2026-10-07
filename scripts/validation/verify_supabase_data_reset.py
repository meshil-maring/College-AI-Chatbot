"""Exercise maintenance SQL only against a new disposable Docker database."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "public.ecr.aws/supabase/postgres:17.6.1.166"
CATALOGS = (
    "roles",
    "permissions",
    "role_permissions",
    "responsibility_definitions",
    "responsibility_permissions",
    "test_types",
)


def docker(*args: str, sql: str | None = None, expect_success: bool = True) -> str:
    result = subprocess.run(
        ["docker", "--context", "desktop-linux", *args],
        input=sql,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if expect_success and result.returncode != 0:
        raise RuntimeError(f"Docker verification failed: {result.stderr[-2000:]}")
    if not expect_success and result.returncode == 0:
        raise AssertionError("Expected SQL refusal, but the operation succeeded")
    return result.stdout.strip()


def main() -> None:
    if os.environ.get("DOCKER_HOST"):
        raise RuntimeError("Refusing an ambiguous DOCKER_HOST")
    if docker("info", "--format", "{{.Name}} {{.OSType}}") != "docker-desktop linux":
        raise RuntimeError("Only the local Docker Desktop Linux engine is permitted")

    container_name = f"collegeai-reset-verify-{uuid4().hex[:12]}"
    container_id = docker(
        "run",
        "--pull=never",
        "--rm",
        "-d",
        "--name",
        container_name,
        "--label",
        "collegeai.data-reset-verification=true",
        "-e",
        f"POSTGRES_PASSWORD={uuid4().hex}",
        IMAGE,
    )
    if not re.fullmatch(r"[a-f0-9]{64}", container_id):
        raise RuntimeError("Disposable container creation did not return a valid ID")

    def execute(
        sql: str, *, expect_success: bool = True, user: str = "postgres"
    ) -> str:
        return docker(
            "exec",
            "-i",
            container_id,
            "psql",
            "-U",
            user,
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-q",
            "-A",
            "-t",
            sql=sql,
            expect_success=expect_success,
        )

    def config() -> dict:
        values = ", ".join(
            f"'{table}', (SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), "
            f"'[]'::jsonb) FROM public.{table} t)"
            for table in CATALOGS
        )
        return json.loads(execute(f"SELECT jsonb_build_object({values});"))

    def user_counts() -> tuple[int, int]:
        value = execute(
            "SELECT (SELECT count(*) FROM public.users)::text || ',' || "
            "(SELECT count(*) FROM auth.users)::text;"
        )
        return tuple(map(int, value.split(",")))

    try:
        print(
            "Disposable local database created; waiting for initialization", flush=True
        )
        for _ in range(100):
            process = docker("exec", container_id, "cat", "/proc/1/comm")
            readiness = subprocess.run(
                [
                    "docker",
                    "--context",
                    "desktop-linux",
                    "exec",
                    container_id,
                    "pg_isready",
                    "-U",
                    "postgres",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            # The cached image uses a .postgres wrapper process name. Match
            # the established Faculty verifier's prefix check, not equality.
            if readiness.returncode == 0 and process.strip().lstrip(".").startswith(
                "postgres"
            ):
                execute("SELECT 1;")
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable PostgreSQL did not finish initialization")

        migrations = sorted((ROOT / "supabase/migrations").glob("*.sql"))
        for index, migration in enumerate(migrations, start=1):
            execute(migration.read_text(encoding="utf-8-sig"))
            if index % 10 == 0:
                print(f"Replayed {index}/{len(migrations)} migrations", flush=True)
        print(f"PASS: {len(migrations)} migrations replayed locally", flush=True)

        # The standalone Postgres image does not run Storage's separate
        # service migrator. Fixture metadata covers only the two tables and
        # columns used by these maintenance scripts; no real files exist.
        execute(
            """
            CREATE SCHEMA IF NOT EXISTS storage;
            CREATE TABLE IF NOT EXISTS storage.buckets (
                id text PRIMARY KEY, name text NOT NULL
            );
            CREATE TABLE IF NOT EXISTS storage.objects (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                bucket_id text NOT NULL REFERENCES storage.buckets(id),
                name text NOT NULL
            );
            GRANT USAGE ON SCHEMA storage TO postgres;
            GRANT ALL ON storage.buckets, storage.objects TO postgres;
        """,
            user="supabase_admin",
        )

        reset = (ROOT / "scripts/maintenance/reset_supabase_data.sql").read_text(
            encoding="utf-8"
        )
        restore = (
            ROOT / "scripts/maintenance/restore_platform_organization.sql"
        ).read_text(encoding="utf-8")
        inspect = (
            ROOT / "scripts/maintenance/inspect_supabase_data_reset.sql"
        ).read_text(encoding="utf-8")
        assert reset.rstrip().endswith("ROLLBACK;")
        commit_reset = reset.rstrip()[: -len("ROLLBACK;")] + "COMMIT;\n"

        # A minimal synthetic organization and linked Auth/application identity.
        execute("""
            INSERT INTO public.organizations(name, organization_code, official_email, contact_information, status)
            VALUES ('Disposable test organization', 'RESET-FIXTURE', 'org@reset.example', 'Local fixture only', 'active');
            INSERT INTO auth.users(id, email)
            VALUES ('91000000-0000-0000-0000-000000000001', 'user@reset.example');
            INSERT INTO public.users(auth_user_id, email, first_name, last_name)
            VALUES ('91000000-0000-0000-0000-000000000001', 'user@reset.example', 'Reset', 'Fixture');
        """)
        original_config = config()
        original_platform_id = execute(
            "SELECT organization_id FROM public.organizations WHERE organization_code = 'COLLEGE-AI-PLATFORM';"
        )
        execute(restore)
        execute(restore)
        assert (
            execute(
                "SELECT organization_id FROM public.organizations WHERE organization_code = 'COLLEGE-AI-PLATFORM';"
            )
            == original_platform_id
        )
        assert user_counts() == (1, 1)
        print(
            "PASS: restoration is idempotent and preserves existing records", flush=True
        )

        execute(
            "UPDATE public.organizations SET status = 'suspended' WHERE organization_code = 'COLLEGE-AI-PLATFORM';"
        )
        execute(restore, expect_success=False)
        assert (
            execute(
                "SELECT status FROM public.organizations WHERE organization_code = 'COLLEGE-AI-PLATFORM';"
            )
            == "suspended"
        )
        execute(
            "UPDATE public.organizations SET status = 'active' WHERE organization_code = 'COLLEGE-AI-PLATFORM';"
        )
        print("PASS: restoration refuses to override restricted onboarding", flush=True)

        execute(reset)
        assert user_counts() == (1, 1)
        assert execute("SELECT count(*) FROM public.organizations;") == "2"
        assert config() == original_config
        print("PASS: default rehearsal rolls back without data loss", flush=True)

        execute("""
            INSERT INTO storage.buckets(id, name) VALUES ('reset-fixture', 'reset-fixture');
            INSERT INTO storage.objects(bucket_id, name) VALUES ('reset-fixture', 'synthetic-metadata-only');
        """)
        execute(commit_reset, expect_success=False)
        assert user_counts() == (1, 1)
        execute("DELETE FROM storage.objects WHERE bucket_id = 'reset-fixture';")
        print("PASS: nonempty Storage blocks reset before deletion", flush=True)

        execute("""
            CREATE SCHEMA reset_guard;
            CREATE TABLE reset_guard.organization_reference(organization_id uuid REFERENCES public.organizations(organization_id));
            INSERT INTO reset_guard.organization_reference SELECT organization_id FROM public.organizations WHERE organization_code = 'RESET-FIXTURE';
        """)
        execute(commit_reset, expect_success=False)
        assert user_counts() == (1, 1)
        execute(
            "DROP TABLE reset_guard.organization_reference; DROP SCHEMA reset_guard;"
        )
        print("PASS: cross-schema foreign keys cause atomic refusal", flush=True)

        execute(commit_reset)
        inventory = json.loads(execute(inspect))
        assert inventory["application_rows"] == 0
        assert inventory["auth_users"] == 0
        assert inventory["storage_objects"] == 0
        assert inventory["platform_onboarding"] == {
            "organization_code": "COLLEGE-AI-PLATFORM",
            "status": "active",
            "join_code_required": False,
        }
        assert config() == original_config
        assert execute("SELECT count(*) FROM public.organizations;") == "1"
        assert (
            execute("SELECT count(*) FROM storage.buckets WHERE id = 'reset-fixture';")
            == "1"
        )
        print(
            "PASS: committed reset removes user data and retains usable onboarding/configuration",
            flush=True,
        )

        execute(
            "DELETE FROM public.organizations WHERE organization_code = 'COLLEGE-AI-PLATFORM';"
        )
        execute(restore)
        assert json.loads(execute(inspect))["platform_onboarding"]["status"] == "active"
        print("PASS: missing platform seed is restored", flush=True)
    finally:
        # Only stop the exact container created above. No mounts, volumes or ports.
        docker("stop", container_id)


if __name__ == "__main__":
    main()
