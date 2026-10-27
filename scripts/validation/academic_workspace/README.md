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

For data that remains visible in the application, use the separate
[retained offerings loader](offerings/README.md). It targets an explicitly chosen
institution in the configured development database and requires `--apply` to
write records; the disposable runner above remains isolated.
