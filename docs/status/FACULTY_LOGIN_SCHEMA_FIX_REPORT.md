# Faculty login with pending database migrations

Date: 7 October 2026.

Status: Login crash fixed in the backend and regression-tested. Hosted database
migration application is awaiting explicit user approval.

## Cause

Admin approval succeeded, but `/api/v1/auth/me` failed while adding the Faculty
context. PostgREST returned `PGRST205` because
`public.responsibility_definitions` was absent from the linked database's schema
cache. The current backend expects the Faculty responsibility migration and its
teaching-validity columns.

The read-only linked migration history and database-push dry run confirmed these
five pending migrations, in execution order:

1. `20261004235959_permission_primary_key_convergence.sql`
2. `20261010000000_phase_10_faculty_attendance_management.sql`
3. `20261011000000_faculty_responsibilities_and_validity.sql`
4. `20261012000000_faculty_attendance_workflow.sql`
5. `20261013000000_faculty_tests_examination.sql`

## Backend behavior

`faculty_context` translates recognized missing Faculty tables, columns and
relationships into a controlled `503 FACULTY_SCHEMA_UNAVAILABLE`. Its warning
identifies the required responsibility migration without exposing database
details to the user. Other database failures continue to propagate.

`/auth/me` handles only that specific unavailable-schema error after the normal
identity and institution authorization checks. It returns the authenticated
Faculty identity, its existing effective permissions, and empty assignment and
responsibility lists. Missing schema grants no responsibility permissions.

The Faculty context endpoint returns the controlled 503 until the migrations
are installed. Its existing frontend refresh behavior displays the unavailable
context and retries; authentication no longer fails because of this feature.
Account and institution authorization denials remain 403.

## Validation

- Focused backend regression suites: **188 passed**. These cover the supplied
  PostgREST failure through the actual responsibility query path, missing
  teaching columns and relationships, unchanged identity/permissions, and
  authorization denials. Command, from `backend`:
  `python -m pytest tests/test_faculty_responsibilities.py tests/test_auth.py tests/test_phase_8_1_authorization.py tests/test_faculty_experience_phase_6_17.py -q -p no:cacheprovider`
- Disposable local Docker verification: **all 35 migrations replayed**;
  responsibility, attendance, assessment and concurrency contracts passed.
  Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/validation/verify_faculty_tests_database.ps1`.
  Local log: `faculty-login-database-verification.log`.
- Python compilation, focused fatal Ruff checks (`E9,F63,F7,F82`), and
  `git diff --check` passed. The full configured Ruff scan still reports existing
  import/style findings in the touched files.
- Read-only `supabase migration list --linked` and
  `supabase db push --linked --include-all --dry-run` both succeeded and identified
  the exact five-migration set above.

## Hosted update awaiting approval

Automatic approval review rejected
`supabase db push --linked --include-all --yes` because the user's login-fix
request did not explicitly authorize hosted schema/data mutations. That command
did not execute; no hosted database changes were made.

After explicit approval, apply the reviewed five-migration set, verify migration
history parity, and check Faculty context reads against the hosted database.
The migrations extend teaching validity and responsibility management,
attendance workflow and examination tables/constraints, and include existing-row
backfills and reconciliation. Restart the backend if its development reloader
has not picked up the login fix.
