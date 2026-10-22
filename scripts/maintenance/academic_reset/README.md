# Institution academic-only reset

This workflow removes one explicitly identified institution's academic records.
It preserves accounts, roles, direct permission grants, unrelated modules,
institution-wide appointments, other tenants, and administration/security audits.
It is separate from the historical global reset, which deletes accounts.

The authorized 2026-10-22 target is Quest (`QUEST123`), institution
`93d79749-0164-4cbf-b378-5fdff295d7af`, in project `rjnfmjcvkfotneswpygr`.
See the [fresh-start record](../../../docs/proposals/academic_curriculum_packages/fresh-start.md).

## Preconditions and safeguards

- Review `catalog.sql` against the explicitly verified project. It exports only
  schema metadata and contains no account rows, credentials, or academic data.
- Install and validate the reviewed academic foundation first. All 36 expected
  academic tables must exist. An unexpected or missing table stops the reset.
- `build.py` pins the institution ID and code and requires database-owner access.
  The default output ends with ROLLBACK; the builder never connects to a database.
- Planning takes table locks, captures the exact target rows, and rejects
  references from preserved rows or unknown consumers, including cascading FKs.
- Only nullable student program/year references can clear through their existing
  foreign keys. Profiles and canonical identity fields remain.
- Only the result-deletion and package-roster deletion guards are temporarily
  paused, inside the locked transaction. Foreign keys and other guards remain
  enabled. Trigger definitions and enabled states must match before commit.
- All accessible public/Auth/migration records outside the deletion plan are
  fingerprinted inside the database before and after. No private rows are
  exported. A mismatch aborts the entire reset.
- A permanent copy requires the successful rehearsal report. Exact table counts
  and a row-content digest must still match; intervening academic changes abort.
- No global trigger bypass, TRUNCATE, auth-account deletion, backup export,
  organization recreation, storage cleanup, or schema migration is performed.

## Reviewed execution sequence

Run from the repository root, keeping output under `logs/backend/`:

```powershell
supabase db query --linked --project-ref rjnfmjcvkfotneswpygr --file scripts/maintenance/academic_reset/catalog.sql --output-format json
backend/.venv/Scripts/python.exe scripts/maintenance/academic_reset/build.py --institution-id 93d79749-0164-4cbf-b378-5fdff295d7af --code QUEST123 --output logs/backend/academic-reset-rehearsal.sql
supabase db query --linked --project-ref rjnfmjcvkfotneswpygr --file logs/backend/academic-reset-rehearsal.sql --output-format json | Out-File logs/backend/academic-reset-rehearsal.json -Encoding utf8
```

Inspect the successful report and verify the intended scope. For the authorized
permanent operation, render a separate copy bound to that report:

```powershell
backend/.venv/Scripts/python.exe scripts/maintenance/academic_reset/build.py --institution-id 93d79749-0164-4cbf-b378-5fdff295d7af --code QUEST123 --expected-report logs/backend/academic-reset-rehearsal.json --output logs/backend/academic-reset-commit.sql --commit
supabase db query --linked --project-ref rjnfmjcvkfotneswpygr --file logs/backend/academic-reset-commit.sql --output-format json
```

Rerun the rollback copy independently afterward. Its deleted-row count must be
zero, with successful preservation and trigger checks. Retain the reports as
local verification evidence. Historical audit snapshots may still name the
deleted academic records; they are retained audit history, not current setup.

## Disposable regression checks

```powershell
backend/.venv/Scripts/python.exe scripts/validation/academic_reset/verify_database.py
```

The verifier creates an owned PostgreSQL container using the existing validated
local Docker helper, with no network, host ports, bind mounts, or persistent
volumes. It replays the remote-like migration baseline and seeds fixtures only
inside that container. It checks rollback, permanent reset, wrong-target refusal,
changed-plan refusal, unknown dependency refusal, account/profile/role/audit
preservation, institution appointments, other-tenant preservation, and idempotent
empty state. Cleanup checks the container's ownership before stopping it.
