# Scoped academic decommission release

`inspect.sql` is read-only and returns table counts and fingerprints, migration
versions, institution identifiers and routine fingerprints. It exports no private
row data. The same query works before removal and after the academic tables are
absent; use it again for post-release evidence.

`prepare_release.py` runs offline. It accepts the captured Supabase CLI JSON
including a UTF-8 BOM, requires the pinned Quest institution and exact observed
43-migration ledger, and verifies the frozen reviewed migration SHA-256.

```powershell
python scripts/maintenance/academic_decommission/prepare_release.py logs/backend/academic-decommission-inspection.json
```

It writes `rehearsal.sql` and `commit.sql` only to a dedicated ignored folder
under `logs/backend/`. Both payloads check the exact ledger, institution, table
inventory, table row fingerprints and routine definitions after taking locks.
The existing migration then verifies preservation of retained identities and
nonacademic data. Its migration-ledger entry commits atomically with the removal.
The rehearsal rolls back all changes. The commit payload differs only in its
reported transaction ending and final `COMMIT`.

The preparation script never calls Supabase, Docker or any network service.
Review and run the rehearsal against the pinned project first. If any guarded
data changed, obtain a new read-only inspection and prepare fresh artifacts.
No unrelated B05 migration or global account-reset script belongs in this release.

After a committed release, run `inspect.sql` again and also capture
`postchecks.sql`. The latter checks the removed student academic columns and the
retained account approval RPC's execution permissions. Verify all four captured
results offline:

```powershell
python scripts/maintenance/academic_decommission/verify_release.py BEFORE.json AFTER.json COMMIT.json POSTCHECKS.json
```

The verifier requires exactly 39 retired tables, 71 retired routine names, 31
retired permissions and the original ledger plus this release. It compares all
unchanged retained table fingerprints and routine definitions; only the approved
permission removal, staff delegation adapter and conditional approval RPC differ.
For populated student identities, the migration's atomic projection comparison
proves retention after dropping the two academic keys.
