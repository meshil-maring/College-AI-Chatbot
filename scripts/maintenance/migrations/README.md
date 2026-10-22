# Generated academic package migration

Maintain the normalized academic package SQL in
`supabase/migration_sources/academic_packages/`. Its manifest specifies dependency
order; each maintained fragment stays within the project file/folder limits.

From the repository root:

```powershell
python scripts/maintenance/migrations/build_academic_packages.py
python scripts/maintenance/migrations/build_academic_packages.py --check
```

The generator adds one outer transaction and source fingerprints. It rejects
path escapes, duplicate fragments, oversized maintained source files, and
overwriting a handwritten migration. The generated flat migration is consumed
by the existing Supabase CLI and disposable replay helpers.

Generation changes a local file only. It never connects to a database or applies
migrations. Existing historical migration files are preserved byte-for-byte.

## Pinned academic release

`prepare_academic_release.py` renders an operational SQL copy for the reviewed
Quest fresh start. It consumes the read-only preflight evidence, checks the
generated migration, pins the institution and exact installed ledger, and adds
the migration-ledger entry to the same transaction as the academic schema.
It refuses an already-installed foundation or an unexpected baseline.

```powershell
backend/.venv/Scripts/python.exe scripts/maintenance/migrations/prepare_academic_release.py --preflight logs/backend/academic-cleanstart-preflight.json --output logs/backend/academic-schema-rehearsal.sql
```

The default copy ends with ROLLBACK. `--commit` renders a permanent copy for the
already-authorized operation. This builder performs no network calls. Execute
only a reviewed copy against the explicitly verified project. It deliberately
does not apply the two unrelated absent invitation/approval migrations, run
`db push`, reset records, or deploy application processes.

Validate the academic migration both with the normal disposable replay and its
`--remote-baseline` mode before executing the live rehearsal. The scoped record
reset is a separate [maintenance workflow](../academic_reset/README.md).
