# Fictional college database validation

Run from the repository root:

```powershell
backend/.venv/Scripts/python.exe scripts/validation/academic_workspace/verify.py
```

Requires the local Docker Desktop Linux engine and the cached Supabase PostgreSQL
image selected by `../disposable_container.py`. The runner validates container
ownership, uses memory-backed storage, publishes no ports and disables networking.
It never reads `backend/.env` or contacts a configured Supabase project.

Every ordered repository migration is replayed, including the current Academic
Setup workspace migration. Two fictional colleges and six fictional accounts are
created. The fixture inserts departments, programs, academic years, dated terms,
subjects, legacy mappings/offerings/sections, progression semesters, curriculum
versions and mappings, admission cohorts, class sections and subject offerings.
Academic records use the actual permission-checked, audited database writers.

Checks cover relationship consistency, normalized duplicate rejection, tenant
boundaries, dates, roles, publication immutability, audit atomicity and dependent
deactivation/reactivation. Expected intake remains capacity, never enrollment.
Two concurrent duplicate writes must produce exactly one commit and one audit.
The run-owned database is removed after success or failure; fixtures remain here
for repeatable validation. This is database integration validation; frontend and
HTTP authentication regression suites must also run independently.

Keep execution logs in `logs/backend/` and frontend logs in `logs/frontend/`.

`backend/.venv/Scripts/python.exe scripts/validation/academic_workspace/verify_academic_deletion.py`
replays migrations and the same fictional seed in an isolated owned database,
then runs department, program, calendar and class-section SQL contracts in
`backend/tests/academics/deletion/`. It checks deletion of unused active/inactive
records, linked-record conflicts, exact grants, tenant isolation, current periods,
student assignments/registrations, audit rollback and future cascade/set-null consumers.
The probe rolls back its records and schema changes before container cleanup.

Without Docker, `verify_academic_deletion.mjs` runs the same SQL contracts in
PGlite's in-memory PostgreSQL with minimal identity fixtures and the actual
Academic Setup and semester-registration schema, guards, grants and writers.
Pass the installed PGlite
package directory as its first argument. A temporary runtime may be installed
under ignored logs without changing application dependencies:

```powershell
npm.cmd install --prefix logs/backend/department-deletion-postgres --no-save --package-lock=false --ignore-scripts @electric-sql/pglite@0.5.13
node scripts/validation/academic_workspace/verify_academic_deletion.mjs logs/backend/department-deletion-postgres/node_modules/@electric-sql/pglite
```

This fallback never reads `.env` or connects to a database URL. It verifies the
relevant schema and SQL behavior, not full historical migration replay or
concurrent sessions. The Docker runner remains the full replay check.

For data that remains visible in the application, use the separate
[retained offerings loader](offerings/README.md). It targets an explicitly chosen
institution in the configured development database and requires `--apply` to
write records; the disposable runner above remains isolated.
