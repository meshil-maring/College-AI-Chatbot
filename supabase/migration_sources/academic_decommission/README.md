# Academic domain decommission

The forward migration `20261023000000` removes the explicitly approved Academic
Setup domain and its dependent attendance, assessment, faculty assignment and
student academic record modules. Historical applied migrations remain intact.

`scope.sql` lists 39 tables and 71 routine names. Only `program_id` and
`academic_year_id` are removed from the retained `students` account profile.
Academic permission families are removed; student account approval permissions,
account-role assignments, tenancy, invitations and nonacademic data remain.

If the retained backend's atomic `b05_approve_student` routine is missing, the
release creates an identity-only adapter with verified actor, tenant and approval
permission checks, including an active parent organization. Profile approval, institution-scoped student role and audit
commit together. Existing installed approval routines remain unchanged. No B05
invitation changes or decision-key column are introduced.

Preflight rejects unknown incoming table and permission dependencies. Removal
uses `RESTRICT`; unexpected views, typed routine dependencies or other consumers
abort the transaction. Exact snapshots verify retained public rows, `auth.users`
and nonacademic routine definitions. Staff delegation keeps its existing narrow
nonacademic permissions and authority checks.

Build with `python scripts/maintenance/migrations/build_academic_decommission.py`.
The generated file owns its outer transaction. A rejected run rolls back every
change. Committed academic data removal requires the saved database backup for
restoration; historical migrations alone cannot recover deleted rows.

Run disposable verification with
`python scripts/validation/academic_decommission/verify_database.py`, and repeat
with `--remote-baseline` to exclude the two unrelated B05 migrations absent from
the observed deployment. The checker uses only an owned local Docker container
with networking disabled and never connects to a hosted database.
