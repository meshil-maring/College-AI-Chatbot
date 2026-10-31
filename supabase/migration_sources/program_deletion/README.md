# Unused program deletion

Additive migration after department deletion. The service-only
`delete_unused_academic_program` RPC uses the existing exact institution-admin
`departments.manage` grant that owns program management. It verifies active
account/tenant/organization state and resolves institution ownership through
the program's department. Foreign and missing IDs return the same not-found error.

All foreign-key consumers block deletion, without filtering by status. This
includes subject mappings, legacy offerings, program semesters, curriculum
versions and admission cohorts, preserving their indirect enrollment history.
Future cascade/set-null references also block. The program row and existing
tenant advisory locks serialize writes; deletion and its before-image audit
commit together. The owning department, subjects and account identities remain.

Generate: `python scripts/maintenance/migrations/build_program_deletion.py`.
Add `--check` for parity. Generation never applies SQL; deploy this forward
migration before using the program DELETE endpoint. Previous migrations retain
their original bytes. Programs with history use the existing Inactive workflow.
