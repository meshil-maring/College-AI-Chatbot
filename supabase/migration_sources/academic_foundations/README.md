# Academic Setup foundations (Stage 1)

Maintained sources for the new forward migration `20261023010000`. Historical
migrations, including the academic decommission, remain unchanged. No academic
records are seeded. These sources do not implement semesters, subjects, sections,
enrollment, attendance, examinations or teaching assignments.

Departments own degree programs. Each record has an explicit institution tenant;
the composite program foreign key forbids cross-tenant departments. Academic
years are institution-wide calendar records. Future study-semester contexts must
explicitly connect a program and academic year; a degree program is not a subject.

Only the trusted backend can invoke `manage_academic_foundation`. Every mutation
checks active institutional admin authority and permission from the same exact
scope, locks the tenant, enforces immutable ancestry, and writes an atomic audit
snapshot. Browser roles have no table or routine access; the service role has
table SELECT and the single mutation entry point, without direct write/delete.

Normalized codes remain reserved after deactivation. Active year dates cannot
overlap (inclusive endpoints), and at most one active year can be current. A
current year must be cleared before deactivation. An active program blocks its
department's deactivation. Creating or reactivating a program requires its active
department; editing or deactivating existing inactive children remains possible.

Build source only:
`python scripts/maintenance/migrations/build_academic_foundations.py`.
Check generated parity without database access:
`python scripts/maintenance/migrations/build_academic_foundations.py --check`.

The generated migration owns one outer transaction. Source checks verify text
contracts and generated parity; they do not execute PostgreSQL, prove database
runtime compatibility, or imply that any migration was applied.
