# Academic Setup aligned with the supplied export

The owner selected `academic_state_check_latest.sql` on 2026-10-26 as the model,
starting with Academic Setup. This forward migration follows the three existing
setup migrations. Historical migrations keep their original bytes.

The conversion targets the repository's seven-table setup baseline. A database
already using the supplied eight-table layout can use the matching application
contracts and existing `manage_academic_master_record` RPC. Check its migration
history before deployment: this conversion expects the old tables and refuses
an already converted database. The full export is a reference, not a migration.

The eight public setup tables, columns, keys, indexes and hierarchy validation
come from that export. Semesters are dated terms within academic years. Courses
are department-owned subjects; programs are degrees. A program-course link is
unique per program/course and optionally specifies a semester. An offering
selects a linked course, program, year and semester. Sections belong to offerings.
Attendance, examinations, student enrollment and teaching assignments are later
work; this migration does not restore their tables or endpoints.

Programs and other descendants derive their institution through parents. The API
adds a derived `institution_id` to responses; it is not a new physical column.
Permissions follow the exported writer: `departments` covers programs, `courses`
covers program links, offerings and sections, with separate academic-year and
semester grants. Existing exact institution-admin and active-organization checks
remain stricter than the exported writer. Browser table access and direct service
writes stay denied. Writes audit atomically; active children block deactivation.

The superseded seven-table setup is moved intact to the private
`academic_setup_previous` schema, with browser/service privileges revoked and old
writers disabled. Common department, program and year rows are copied with the
same IDs. Reusable subjects are copied to courses with the same IDs and credits.
Study-semester and class data remain in that private schema;
their conversion needs an explicit mapping because study progress has no dates
and a multi-subject class is not a single-course offering section. No rows are
deleted and no term dates or class assignments are invented. Existing archive
schemas or unexpected dependencies make the transaction fail, preserving state.

Build: `python scripts/maintenance/migrations/build_academic_export.py`.
Parity: add `--check`. These commands only assemble SQL; they do not apply it.
Apply the reviewed migration through the normal database deployment process.
Verification covers the table definitions, all academic keys and indexes,
generated SQL parity, API validation, permissions and frontend workflows.
This update does not establish a connection to or apply SQL to a live database.
