# Retained academic offering test data

This loader writes fictional academic data directly to the **configured
development database**, under an explicitly selected institution and existing
administrator. Created data remains available in the application. It is separate
from the parent directory's disposable PostgreSQL validator.

Run from `backend/`, so the application's existing `.env` is discovered:

```powershell
$env:DEBUG='false'
./.venv/Scripts/python.exe ../scripts/validation/academic_workspace/offerings/run.py --institution-id INSTITUTION_UUID --actor-id ADMIN_USER_UUID --prefix QA26
```

The default is a dry run. Add `--apply` to insert and verify the records. The
configured environment must be development/local/test. The account must already
have institution administrator grants and Academic Setup permissions. The loader
does not create accounts, grant permissions, apply migrations or change settings.

The dataset includes three fictional degree programs: Computer Science,
Electronics and Communication, and Mathematics. Each has a complete sequence of
eight/eight/six study semesters, two published curricula, two admission cohorts,
two class sections per semester, and three subjects per section. That produces
264 academic offerings, 132 legacy course offerings, 88 cohort-owned sections,
264 legacy offering-owned sections, 66 reusable subjects and 132 versioned subject
mappings. Both core and optional subject types appear. Program credit totals
match the included subjects; intake is expected capacity, never enrollment.

The August-to-July calendar covers 2025-2030. Existing matching academic years
and numbered dated terms are reused. Other existing application records are
preserved. New department/program/course/cohort/section codes use the selected
prefix. Rerunning with the same prefix reuses matching records and refuses to
overwrite incompatible or inactive records. Each mutation uses the application's
permission-checked database RPCs and generates its normal audit record.

Before inserting, the loader records a catalogue baseline under `logs/backend/`.
Its manifest retains created IDs and payloads for repeatable inspection/resumption
if an interrupted run leaves a partial dataset. The overall seed spans multiple
atomic RPCs; it is not a single transaction. Independent programs are populated
concurrently, while the database retains its per-institution write lock.
The loader uses a process-scoped HTTP/1.1 transport to avoid bulk HTTP/2 stream
termination. It does not blindly retry writes with uncertain commit outcomes;
resumption discovers matching records through their natural keys.

One initial offering is created through the real FastAPI endpoint. Verification
reads both real catalogues, checks every offering's complete ancestry and dates,
checks duplicates/credits/capacities and preservation of unrelated records, and
exercises API update, deactivate/reactivate, validation and rejection paths.
Temporary capacity changes are restored, leaving the offerings active. The API
checks inject the existing database-resolved administrator into the authentication
dependency; they do not log in with or test the administrator's password/JWT.

Keep the manifest, baseline, execution report and logs in `logs/backend/`.
Frontend interaction regressions belong in `logs/frontend/`.
