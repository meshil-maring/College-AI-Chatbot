"""Test the academic-only reset in an owned, network-isolated PostgreSQL."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/validation/academic_packages"))
from verify_database import (
    EXPECTED_IMAGE, checked, docker_arguments, expected_name, validate_cleanup_target,
    validate_disposable_target, validate_local_engine, validate_with_retry,
)

spec = importlib.util.spec_from_file_location("academic_reset_builder", ROOT / "scripts/maintenance/academic_reset/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def main() -> None:
    validate_with_retry(validate_local_engine)
    token, purpose, container = uuid4().hex, "data-reset", None
    try:
        container = checked(docker_arguments(
            "run", "--pull=never", "--rm", "-d", "--network", "none",
            "--tmpfs", "/var/lib/postgresql/data:rw,size=536870912",
            "--name", expected_name(token,purpose), "--label", "collegeai.validation.disposable=true",
            "--label", f"collegeai.validation.run={token}", "--label", f"collegeai.validation.purpose={purpose}",
            "-e", "PGDATA=/var/lib/postgresql/data", "-e", f"POSTGRES_PASSWORD={uuid4().hex}", EXPECTED_IMAGE))
        if not re.fullmatch(r"[a-f0-9]{64}", container):
            raise RuntimeError("Expected full disposable container identifier")
        validate_with_retry(validate_disposable_target,container,token,purpose)

        def sql(content: str, *, success: bool = True) -> str:
            result = subprocess.run(docker_arguments("exec","-i",container,"psql","-U","postgres","-d","postgres",
                "-v","ON_ERROR_STOP=1","-qAt"),input=content,capture_output=True,text=True,encoding="utf-8",timeout=120)
            if success != (result.returncode == 0):
                raise RuntimeError(result.stderr[-7000:] or "Expected SQL refusal")
            return result.stdout.strip()

        for _ in range(100):
            ready = subprocess.run(docker_arguments("exec",container,"pg_isready","-U","postgres"),capture_output=True,timeout=10)
            if ready.returncode == 0 and re.match(r"^\.?postgres(?:-|$)",checked(docker_arguments("exec",container,"cat","/proc/1/comm"))):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable database did not become ready")
        for path in sorted((ROOT / "supabase/migrations").glob("*.sql")):
            if path.name.startswith(("20261017000000_","20261019000000_")):
                continue
            print(f"REPLAY {path.name}",flush=True)
            sql(path.read_text(encoding="utf-8"))
        for name in ("academic_package_seed.sql","academic_package_workflow.sql"):
            sql((ROOT / "scripts/validation/academic_packages" / name).read_text(encoding="utf-8"))
        sql(Path(__file__).with_name("fixtures.sql").read_text(encoding="utf-8"))
        target = json.loads(sql("SELECT jsonb_build_object('id',i.institution_id,'code',i.code) FROM public.institutions i "
            "WHERE institution_id=academic_package_fixture.id('tenant');"))
        before = sql("SELECT jsonb_build_object('departments',(SELECT count(*) FROM public.departments),"
            "'users',(SELECT count(*) FROM public.users),'auth',(SELECT count(*) FROM auth.users),"
            "'students',(SELECT count(*) FROM public.students),'audit',(SELECT count(*) FROM public.admin_audit_log));")
        rehearsal = builder.render(target["id"],target["code"])
        report = json.loads(sql(rehearsal))
        assert report["deleted_rows"] > 50 and report["preservation_verified"]
        assert before == sql("SELECT jsonb_build_object('departments',(SELECT count(*) FROM public.departments),"
            "'users',(SELECT count(*) FROM public.users),'auth',(SELECT count(*) FROM auth.users),"
            "'students',(SELECT count(*) FROM public.students),'audit',(SELECT count(*) FROM public.admin_audit_log));")
        print("PASS: rollback preserves structure, identities, credentials and audit history",flush=True)
        commit = builder.render(target["id"],target["code"],commit=True,expected=report)
        # A new academic row invalidates the reviewed rehearsal, even at the same institution.
        sql("INSERT INTO public.departments(institution_id,name,code) VALUES ('" + target["id"] + "','Late department','LATE');")
        sql(commit,success=False)
        assert sql("SELECT count(*) FROM public.departments WHERE code='LATE'") == "1"
        sql("DELETE FROM public.departments WHERE code='LATE'")
        print("PASS: changed plan refuses permanent reset without partial deletion",flush=True)
        # Unknown external consumer must stop even an ON DELETE CASCADE relationship.
        sql("CREATE TABLE public.reset_external_consumer(id uuid REFERENCES public.programs(program_id) ON DELETE CASCADE);"
            "INSERT INTO public.reset_external_consumer SELECT value FROM academic_package_fixture.ids WHERE name='program';")
        sql(rehearsal,success=False)
        assert sql("SELECT count(*) FROM public.reset_external_consumer") == "1"
        sql("DROP TABLE public.reset_external_consumer")
        print("PASS: unknown preserved dependencies block reset without cascading",flush=True)
        sql(builder.render(str(uuid4()),target["code"]),success=False)
        result = json.loads(sql(commit))
        assert result["plan_digest"] == report["plan_digest"] and result["trigger_restoration_verified"]
        assert sql("SELECT count(*) FROM public.users") == "4"
        assert sql("SELECT count(*) FROM auth.users") == "4"
        assert sql("SELECT count(*) FROM public.students") == "1"
        assert sql("SELECT count(*) FROM public.students WHERE program_id IS NULL AND academic_year_id IS NULL") == "1"
        assert sql("SELECT count(*) FROM public.departments") == "1"
        assert sql("SELECT count(*) FROM public.faculty_responsibilities WHERE scope_type='institution'") == "1"
        assert sql("SELECT count(*) FROM public.academic_classes") == "0"
        assert json.loads(sql(rehearsal))["deleted_rows"] == 0
        print("PASS: permanent tenant-only reset preserves accounts, roles, profiles, audits, institution appointments and other tenant",flush=True)
    finally:
        if container and re.fullmatch(r"[a-f0-9]{64}",container):
            owned = validate_with_retry(validate_cleanup_target,container,token,purpose)
            checked(docker_arguments("stop","--timeout","10",owned))


if __name__ == "__main__":
    main()
