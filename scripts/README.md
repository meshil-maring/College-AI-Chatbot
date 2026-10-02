# Repository maintenance scripts

One-off scripts used to prepare repository assets. Both are **historical**: their outputs are already
committed, so they are kept for provenance rather than routine use.

| Script | Purpose | Notes |
| --- | --- | --- |
| `write_migration.py` | Regenerates `supabase/migrations/20260909000001_phase_admin_2_extracted_text_column.sql` (adds `document_versions.extracted_text`) | The migration is already applied — running this overwrites the file, so only use it to reproduce it |
| `fix_indent.py` | Corrects the mis-indented `'low'` entry of the `notices_priority_check` array in `supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql` | Already applied; re-running is a no-op unless that migration is regenerated |

Both resolve the repository root from their own file location
(`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`), so they can be executed from any
working directory:

```powershell
python scripts/write_migration.py
python scripts/fix_indent.py
```

## Validation and local provisioning

Scripts under `scripts/validation` are active, narrowly scoped operational
helpers. `manage_local_super_admin.ps1` assigns or revokes the Phase 7.12 role
only against the verified loopback Supabase stack. It requires an explicit
`local`/`test` environment and actor identifier, uses the transient local
service-role credential without printing it, and records every idempotent
result in `platform_role_audit_log`. It does not create or delete Auth users.

`provision_local_demo_users.ps1` creates local-only demo accounts through the
verified loopback stack. It refuses to run without an explicit ephemeral
password, never contacts a remote Auth instance, and never prints the
service-role credential.
