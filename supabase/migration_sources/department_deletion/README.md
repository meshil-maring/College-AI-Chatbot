# Unused department deletion

Additive migration after semester registration. The service-only
`delete_unused_academic_department` RPC rechecks exact institution-admin grants,
active tenant/organization state, ownership and every foreign-key consumer.
Active and inactive dependencies both block deletion, including consumers whose
foreign keys would otherwise cascade or clear a reference. Programs and courses
preserve indirect student, curriculum, cohort, section and offering relationships.
Account identities are never deleted by this command. Retired faculty teaching
workflows remain retired; any future department references must use foreign keys.

The existing tenant advisory lock serializes academic writers; a department row
lock serializes concurrent foreign-key inserts. Deletion and its before-image
audit commit together. Missing or foreign departments return the same not-found
error. Linked records return a conflict; no dependencies are modified.

Generate with `python scripts/maintenance/migrations/build_department_deletion.py`;
add `--check` to verify parity. Generation does not apply SQL. Deploy this forward
migration before enabling the new HTTP DELETE action. Historical migrations stay
unchanged. Department retirement remains the existing guarded Inactive workflow.
