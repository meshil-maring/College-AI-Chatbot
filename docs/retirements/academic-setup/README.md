# Academic Setup removal

Date: 2026-10-23. The owner requested removal of the existing Academic Setup
workflow, design, schema and dependent academic modules before a future redesign.
The owner explicitly included Attendance, Exams, Faculty Assignments, Student
Records and their shared academic tables.

## Preserved backup

The previous implementation is saved in GitHub branch
[`backup/academic-setup-2026-10-23`](https://github.com/meshil-maring/College-AI-Chatbot/tree/backup/academic-setup-2026-10-23),
commit `77374d0d13fdd2ed61f7a63166a34b8019b91b92`. Removal work is isolated on
`refactor/academic-setup-fresh-start-2026-10-23`. The backup branch is unchanged.
This source backup does not contain private database rows or credentials.

## Removal boundary

Remove academic setup/catalogues, curricula/packages, classes, teaching sections,
batches, offerings, student academic rosters, attendance and examination results,
faculty teaching assignments and academic responsibilities. Remove their UI,
API, services, repositories, contracts, tests and active design proposals.

Keep authentication accounts, roles, institutions/organizations, identity-only
student profiles and account approval, account permissions, knowledge/documents,
notices/resources, ordinary chat and conversation history. Chat no longer reads
academic records. Existing audit history remains.

The forward [migration sources](../../../supabase/migration_sources/academic_decommission/README.md)
list the exact database scope: 39 academic tables and 71 routine names. Only
`students.program_id` and `students.academic_year_id` are removed from the retained
identity profile. Retired academic permission grants are removed; account-role
assignments and nonacademic permissions remain.

Historical applied migrations and dated evidence stay intact. A forward
migration removes installed academic schema; deleting migration history would
prevent clean database replay. No replacement academic schema or design is added.

## Validation and deployment

Disposable database replays cover both the complete local migration history and
the observed live history. Dependency rejection, atomic rollback and exact
preservation of retained data are required before live execution.

The removal was committed to Quest (`QUEST123`, project
`rjnfmjcvkfotneswpygr`) on 2026-10-23 as migration `20261023000000`. A live
ROLLBACK rehearsal first proved exact restoration of the prior schema, data
fingerprints, routines and 43-version ledger. The permanent transaction then
removed 39 tables, 71 routine names and 31 academic permission codes.

Post-release inspection confirms 38 retained tables, unchanged independent
fingerprints for 35 tables, six Auth accounts, two application users, two role
assignments and the existing institution. The three permission/grant tables have
only the authorized academic permission removals; the transaction separately
verified exact preservation of their remaining rows. The ledger now contains
44 versions. Student academic columns are absent; identity/approval columns
remain. The retained approval RPC permits service-role execution and denies
authenticated direct execution.

The frozen migration SHA-256 is
`7c3a06e4773093d7f1a358bd996c3a860137fa306a6817759cca1ea0f59d809c`.
No unrelated missing B05 invitation migrations were installed. The minimal
identity-only approval adapter was added because its backend RPC was previously
absent; approval, role provisioning and audit now commit atomically.

Validation passed: 2,460 backend tests (21 skipped), 552 frontend tests, the strict
production build, structure validators and generated RBAC check. Final landing
copy checks passed another 16 tests. Both disposable database baselines passed
dependency rejection, rollback, account preservation and actual approval RPC
contracts. Code changes remain on the local removal branch; no application
deployment or new Git push was performed.

Evidence is kept locally under `logs/backend/academic-decommission-*` and
`logs/frontend/academic-retirement-*`. The offline post-release verification is
`logs/backend/academic-decommission-offline-verification.json`. Operational
inspection, preparation and verification tools are documented in
[the release guide](../../../scripts/maintenance/academic_decommission/README.md).

The owner requested that the [listed legacy UI files](pending-removals.md) stay
for now. Their inactive source remains available alongside the GitHub backup.
Fifteen inactive source paths and thirteen historical workflow test files are
explicitly excluded from the production build/test run. The structure validator
still checks their maintenance limits and rejects active imports into them.
The account approval wrapper and its current tests remain active.
