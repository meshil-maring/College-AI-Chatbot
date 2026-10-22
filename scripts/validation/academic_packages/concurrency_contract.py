"""Concurrent SQL contracts against the runner's owned disposable container."""

from __future__ import annotations

import subprocess
import time


CLAIMS = "SET request.jwt.claim.role = 'service_role';\n"


def verify_concurrency(container: str, token: str, purpose: str, docker_arguments, checked) -> None:
    from disposable_container import validate_disposable_target

    validate_disposable_target(container, token, purpose)

    def arguments():
        return docker_arguments("exec", "-i", container, "psql", "-U", "postgres", "-d", "postgres",
                                "-qAt", "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose")

    def sql(statement: str) -> str:
        result = subprocess.run(arguments(), input=CLAIMS + statement, text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stderr[-8000:])
        return result.stdout.strip()

    def competing(statements: list[str], expected_state: str) -> None:
        processes = [subprocess.Popen(arguments(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True) for _ in statements]
        try:
            for process, statement in zip(processes, statements):
                process.stdin.write(CLAIMS + "SELECT pg_sleep(0.2);\n" + statement)
                process.stdin.close()
                process.stdin = None
            results = [process.communicate(timeout=30) for process in processes]
            successes = sum(process.returncode == 0 for process in processes)
            if successes != 1:
                raise RuntimeError(f"Expected one concurrent winner, got {successes}: {results}")
            failures = [stderr for process, (_, stderr) in zip(processes, results) if process.returncode]
            if len(failures) != 1 or expected_state not in failures[0]:
                raise RuntimeError(f"Unexpected concurrency failure: {failures}")
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def assignment(placement: str, package: str) -> str:
        return ("SELECT academic_package_fixture.command('assign_package', jsonb_build_object("
                f"'placement_id', academic_package_fixture.id('{placement}'), "
                f"'package_id', academic_package_fixture.id('{package}')));")

    competing([assignment("RACE_INITIAL", "package_abc"), assignment("RACE_INITIAL", "package_efg")], "42501")
    sql("""
        SELECT academic_package_fixture.check((SELECT count(*) = 1 FROM public.academic_package_assignments
            WHERE placement_id = academic_package_fixture.id('RACE_INITIAL')), 'one competing initial assignment');
        SELECT academic_package_fixture.check((SELECT count(*) = 5 FROM public.academic_subject_participation
            WHERE placement_id = academic_package_fixture.id('RACE_INITIAL') AND ended_at IS NULL), 'one complete winning bundle');
        UPDATE public.sections SET capacity = (SELECT count(*) + 1 FROM public.faculty_attendance_rosters
            WHERE section_id = academic_package_fixture.id('section_E') AND participation_active)
        WHERE section_id = academic_package_fixture.id('section_E');
    """)
    competing([assignment("RACE_CAP_A", "package_efg"), assignment("RACE_CAP_B", "package_efg")], "23514")
    sql("""
        SELECT academic_package_fixture.check((SELECT count(*) = 1 FROM public.academic_package_assignments
            WHERE placement_id IN (academic_package_fixture.id('RACE_CAP_A'), academic_package_fixture.id('RACE_CAP_B'))), 'one last-seat winner');
        SELECT academic_package_fixture.check((SELECT count(*) = 5 FROM public.academic_subject_participation
            WHERE placement_id IN (academic_package_fixture.id('RACE_CAP_A'), academic_package_fixture.id('RACE_CAP_B'))
              AND ended_at IS NULL), 'capacity loser has no partial bundle');
        UPDATE public.faculty_responsibilities SET end_at = clock_timestamp() + interval '3 seconds'
        WHERE institution_id = academic_package_fixture.id('tenant') AND responsibility_code = 'hod'
          AND faculty_user_id = academic_package_fixture.id('faculty');
    """)
    blocker = subprocess.Popen(arguments(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        blocker.stdin.write(CLAIMS + """
            BEGIN;
            SELECT 1 FROM public.faculty_responsibilities WHERE institution_id = academic_package_fixture.id('tenant')
              AND responsibility_code = 'hod' AND faculty_user_id = academic_package_fixture.id('faculty') FOR UPDATE;
            SELECT pg_sleep(4);
            COMMIT;
        """)
        blocker.stdin.close()
        blocker.stdin = None
        if blocker.stdout.readline().strip() != "1":
            raise RuntimeError("Responsibility lock holder did not acquire its row")
        started = time.monotonic()
        allowed = sql("""
            SELECT public.academic_package_allowed(academic_package_fixture.id('faculty'), academic_package_fixture.id('tenant'),
                'academic.package.assign', academic_package_fixture.id('race_class'));
        """)
        waited = time.monotonic() - started
        if allowed != "f" or waited < 1:
            raise RuntimeError(f"Expired responsibility authorized after lock wait: allowed={allowed}, waited={waited:.2f}")
        blocker.communicate(timeout=10)
        if blocker.returncode:
            raise RuntimeError("Responsibility lock holder failed")
    finally:
        if blocker.poll() is None:
            blocker.kill()
            blocker.communicate(timeout=5)
    print("PASS: competing selections, last-seat capacity and responsibility expiry after row-lock wait", flush=True)
