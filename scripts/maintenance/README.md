# Supabase application data reset

These scripts support the authorized fresh start of College AI Chatbot,
project `rjnfmjcvkfotneswpygr`. They do not replay or apply migrations.

- `inspect_supabase_data_reset.sql` reports exact application/configuration row
  counts, Auth account counts and Supabase Storage metadata. It changes no
  persistent data.
- `reset_supabase_data.sql` clears application records and all Auth accounts in
  one transaction, recreates the reserved university-onboarding parent, checks
  the result, and **rolls back by default**.
- `restore_platform_organization.sql` restores the missing reserved
  `COLLEGE-AI-PLATFORM` organization using the existing migration seed. It is
  idempotent and refuses to override a suspended or join-code-restricted row.
- `backup_supabase_data_reset.sql` exports sensitive application and Auth rows.
  Use it only with explicit authorization to create the local data copy. Keep
  the result private and outside version control. This is a data export, not a
  tested full database restore artifact.

Run the inspection and rehearsal from the repository root:

```powershell
supabase db query --linked --project-ref rjnfmjcvkfotneswpygr --file scripts/maintenance/inspect_supabase_data_reset.sql --output json
supabase db query --linked --project-ref rjnfmjcvkfotneswpygr --file scripts/maintenance/reset_supabase_data.sql --output json
```

If university registration reports that its organization code was not found
after a reset, restore the required system seed:

```powershell
supabase db query --linked --project-ref rjnfmjcvkfotneswpygr --file scripts/maintenance/restore_platform_organization.sql --output json
```

For an authorized permanent reset, use a reviewed copy of the reset SQL with
only its final `ROLLBACK;` changed to `COMMIT;`. Execute that copy against the
explicitly confirmed project, then rerun the inspection. Do not place a reset
in `supabase/migrations`: a reset is an operational action, not a schema change.

The reset preserves tables, constraints, indexes, RLS, functions, migration
history, Storage bucket definitions and these configuration catalogs when
present: `roles`, `permissions`, `role_permissions`, `responsibility_definitions`,
`responsibility_permissions` and `test_types`. Per-user roles and permission
grants are application data and are cleared, along with user profiles, tenants,
academics, documents, chats, audit records, attendance and results.
The reserved `COLLEGE-AI-PLATFORM` parent is recreated as active without a join
code; all other organizations are cleared. Inspection reports
`application_row_count` separately from `preserved_row_count`, and
`application_rows` excludes both configuration catalogs and this system row.

The SQL refuses to run while Supabase Storage contains objects. Remove actual
files through the Storage API or dashboard first; SQL deletion of Storage
metadata leaves orphaned files. See [Supabase's Storage deletion documentation](https://supabase.com/docs/guides/storage/management/delete-objects).

Auth users are deleted through the managed `auth.users` table; its existing
foreign keys remove dependent identities and sessions. The script preserves
the managed Auth schema and configuration. Supabase service logs and other
provider-managed metadata are outside the application-record reset. Existing
JWTs retain their own expiry, as described in [Supabase's user management
documentation](https://supabase.com/docs/guides/auth/managing-user-data).

This app also stores uploaded documents in Cloudflare R2. R2 objects are outside
the authorized Supabase reset and require a separate storage cleanup request.

After resetting, all former accounts and application role grants are gone.
Public university registration can create a new university and its initial
University Admin immediately under the reserved platform parent. A Super Admin
account is required for platform management, not for public university signup.
The existing `manage_local_super_admin.ps1` helper supports local/test stacks
only and must not be used against this remote project.

Validate the reset and repair on a fresh disposable local database with the
cached Supabase PostgreSQL image and Docker Desktop:

```powershell
backend/.venv/Scripts/python.exe scripts/validation/verify_supabase_data_reset.py
```

This verifier replays all local migrations, checks rollback and permanent-reset
behavior, verifies that Storage/dependency errors preserve data, and tests
idempotent restoration and restricted-organization refusal. It publishes no
ports, mounts no volumes and stops only the container it creates.
The standalone PostgreSQL image does not run the separate Storage migrator;
the Storage guard uses minimal fixture metadata, with no actual uploaded files.
Public migrations and reset transactions execute on real PostgreSQL.
