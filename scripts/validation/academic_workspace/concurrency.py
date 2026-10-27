"""Competing committed writes must create one progression stage and one audit."""

from concurrent.futures import ThreadPoolExecutor
import subprocess

from runtime import execute, sql_arguments


def verify_concurrent_duplicate(container):
    command = """
        BEGIN;
        SET LOCAL request.jwt.claim.role='service_role';
        SELECT public.manage_academic_structure_record(
            workspace_fixture.id('admin'), workspace_fixture.id('tenant'),
            'program_semesters', NULL, jsonb_build_object(
                'program_id',workspace_fixture.id('program'),
                'name','Semester 3','code','S3','semester_number',3));
        SELECT pg_sleep(0.2);
        COMMIT;
    """
    audit_before = int(execute(container, "SELECT count(*) FROM public.admin_audit_log"))

    def write():
        return subprocess.run(
            sql_arguments(container), input=command, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=60,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: write(), range(2)))
    successes = [result for result in results if result.returncode == 0]
    failures = [result for result in results if result.returncode != 0]
    if len(successes) != 1 or len(failures) != 1 or "23505" not in failures[0].stderr:
        raise RuntimeError("Concurrent duplicate writes did not produce exactly one commit and one unique violation")
    execute(container, f"""
        SELECT workspace_fixture.assert_true(
            'Concurrent duplicate requests create exactly one record and one audit',
            (SELECT count(*)=1 FROM public.program_semesters
             WHERE program_id=workspace_fixture.id('program') AND semester_number=3)
            AND (SELECT count(*)={audit_before + 1} FROM public.admin_audit_log));
    """)
    print("PASS: concurrent duplicate writes produce one committed record and one audit", flush=True)
