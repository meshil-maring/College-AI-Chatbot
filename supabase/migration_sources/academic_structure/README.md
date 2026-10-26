# Academic Setup study semesters and reusable subjects (Stage 2)

Maintained sources for the unapplied new forward migration `20261024000000`.
Stage 1 `20261023010000_academic_foundations.sql` is required first. These sources
do not replace or rewrite any Stage 1 or historical function, source or migration.
No SQL has been executed to verify database or production compatibility.

`study_semesters` represents degree progress in one program and academic year,
for example B.Tech CSE / 2026–2027 / Fifth Semester (`study_semester_number=5`).
It has no calendar-term dates or current-term flag. Institutional academic years
keep their existing calendar dates. The API entity is `semesters`, explicitly
mapped to `study_semesters`; degree programs and reusable subjects stay distinct.

`subjects` belongs to a department, with a reusable code, name and required finite
positive credits at most 100. Subjects have no program, semester or section
assignment. Sections and subject assignments remain a future stage. Composite
foreign keys enforce the tenant of every parent. Codes are trimmed and unique
case-insensitively in the owning department or program/year context. Study
semester numbers are also unique per program/year. Inactive records continue to
reserve their codes and study numbers; ownership and study number are immutable.

Create and reactivate require active tenant/organization and active academic
parents. Metadata edits and deactivation of existing inactive children remain
possible. New parent triggers prevent deactivating departments with active
subjects, or programs/academic years with active study semesters. Existing Stage
1 department protection for active programs remains intact. Both stages share
the `academic-foundations:` advisory tenant lock to serialize hierarchy changes.

Only institution-scoped active administrators receive the four exact read/manage
permissions. The new audited `manage_academic_structure` RPC reuses unchanged
Stage 1 actor authorization. Table RLS denies browser access; service reads are
tenant-filtered by repositories and service mutation requires the RPC. Each
write atomically audits before/after data and actual activation transitions.

Prepare source only:
`python scripts/maintenance/migrations/build_academic_structure.py`.
Check generated parity:
`python scripts/maintenance/migrations/build_academic_structure.py --check`.

The generator writes one outer transaction; source files stay bounded. Source
tests check release contracts and parity without executing PostgreSQL. They do
not prove trigger, constraint, locking or privilege behavior in a live database.
