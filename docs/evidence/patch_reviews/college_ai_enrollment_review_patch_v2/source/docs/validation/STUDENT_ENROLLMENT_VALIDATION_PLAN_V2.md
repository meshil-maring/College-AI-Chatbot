# Student Enrollment Validation Plan v2

- **Status:** Proposed harness changes; static checks only
- **Safety boundary:** Local Docker Desktop only. No SQL was executed while preparing this package.

## Safety properties in the harness patch

- Each runner creates a unique run token and unique container name.
- Container is created from the expected Supabase PostgreSQL 17.6.1.166 image.
- Container uses `--network none`, a bounded 512 MiB tmpfs for `/var/lib/postgresql/data`, `--rm`, and no published host ports, bind mounts, or persistent database volumes.
- Runner passes the exact 64-character container ID, run token, and purpose to every Python concurrency helper.
- `disposable_container.py` validates local Docker context/engine, container identity, run token/purpose labels, image, running state, the single allowed tmpfs mount, absence of host ports/bind mounts, auto-removal, and network isolation before SQL helpers run.
- Helpers refuse to issue SQL until a target is configured and validated.
- Cleanup targets only the exact container ID created by the runner and requires its run token label to match.
- Faculty assignment concurrency no longer hard-codes `supabase_db_CollegeAIChatbot` or requires host port 54322.

## Files in this patch

- `scripts/validation/disposable_container.py` — shared fail-closed target validator.
- `scripts/validation/faculty_attendance_concurrency.py` — accepts container ID, run token, and purpose.
- `scripts/validation/faculty_tests_concurrency.py` — shares the validated attendance SQL target.
- `scripts/validation/faculty_assignment_concurrency.py` — requires a validated disposable target instead of the persistent project DB.
- `scripts/validation/academic_setup_concurrency.py` — uses the shared validator.
- `scripts/validation/verify_faculty_attendance_database.ps1` — unique, isolated runner.
- `scripts/validation/verify_faculty_tests_database.ps1` — unique, isolated runner.
- `scripts/validation/verify_academic_setup_database.ps1` — unique, isolated runner.
- `scripts/validation/verify_faculty_assignment_database.ps1` — new isolated runner for the assignment concurrency contract.

## Static validation performed

- Python `py_compile` passed for all six Python files in the patch. Six isolated unit tests for the shared target validator passed; these tests mock Docker inspection and do not contact Docker or PostgreSQL.
- No PowerShell runtime/parser was available in this environment, so the `.ps1` scripts have not been executed or runtime-parsed.
- No Docker command, database connection, migration, SQL query, test fixture, or remote Supabase operation was executed.

## Required local checks before use

1. Review the patch and confirm that the repository paths and Python interpreter invocation match the Windows checkout.
2. Inspect the final runner source to verify PowerShell parsing and the exact Docker labels/arguments.
3. Confirm Docker Desktop's `desktop-linux` context and `docker-desktop` engine.
4. Run a non-database harness self-test if available; do not point any helper at `supabase_db_CollegeAIChatbot`.
5. Run one disposable validation suite at a time initially and verify cleanup of the run-owned container.
6. Rehearse the existing migration chain in the disposable container. A failure is evidence to investigate; do not repair by skipping migrations.
7. Only after the general harness is trusted, add the final enrollment DDL and synthetic enrollment fixtures to a separate enrollment-specific runner.

## Enrollment-specific validation still required

Once final DDL exists and is approved for disposable execution, test:

- fresh full migration replay;
- all foreign keys, checks, indexes, trigger bindings, grants, and RLS assertions;
- same-student readmission with retained identifier ownership;
- rejection of identifier reuse by a different student;
- transfer and program change as new episodes;
- promotion/repeated semester with non-overlapping placements;
- forged cross-tenant IDs and mismatched identifier kind/student/institution;
- event append-only behavior, operation retry idempotency, and actor retention;
- state transition concurrency, stale versions, and atomic rollback when event/audit/reconciliation fails;
- historical published-result visibility after promotion, withdrawal, or transfer;
- existing registration, attendance, results, tests, roster, notifications, authentication, and frontend contract suites.

## Go/no-go rules

**Go to disposable enrollment validation only when:** ADR policy decisions are approved, exact candidate DDL is recovered/reviewed, security preflight is reconciled, and the harness passes local safety checks.

**No-go for remote deployment** until populated synthetic backfill tests, current catalog ACL/RLS verification, rollback rehearsal, and explicit separate deployment approval are complete.
