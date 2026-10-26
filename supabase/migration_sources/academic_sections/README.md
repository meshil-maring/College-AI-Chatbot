# Academic Setup class sections and subject assignments (Stage 3)

Maintained sources for the unapplied forward migration `20261024010000`.
Stages 1 and 2 must precede it. No earlier source or function is replaced.
The generator only prepares a file; no SQL execution or production verification
is part of this work.

`class_sections` belongs to one `study_semesters` record. Its degree program
and academic year derive from that immutable parent. Names and codes are
trimmed, case-insensitively unique within the institution/study-semester context,
and stay reserved after deactivation. Study-semester ancestry cannot be edited.
A section is shared by multiple subjects rather than duplicated per subject.

`section_subject_assignments` joins a section to a reusable subject. Both parents
must belong to the same institution; subjects from different departments in that
institution are allowed. Create requires active section, study semester, program,
program department, academic year, subject and subject department. Active
institution and organization are also required. Composite foreign keys enforce
tenant ownership independently of the application.

Assignment creation accepts only `section_id` and `subject_id` and starts active.
PATCH accepts only `is_active`. Removal sets it false, preserving the link ID and
the original catalogue subject. Repeated removal is idempotent. Reactivation
uses that same ID and validates every active parent again; another create for
the same pair remains a uniqueness conflict even while inactive. Hard deletes
are unavailable. Metadata edits and cleanup removal tolerate inactive parents.

Deactivate a section or subject only after removing its active assignments;
deactivate a study semester only after deactivating its active sections. New
triggers extend the existing Stage 2 guards without replacing those functions.
All generations use the same `academic-foundations:` tenant advisory lock.

Only exact institution-scoped administrators receive `sections.read/manage`
and `section_subjects.read/manage`. The new `manage_academic_sections` RPC reuses
the unchanged Stage 1 actor check. RLS and table ACLs deny browser access;
service-role tables permit only SELECT, and only the RPC receives EXECUTE.
Actual writes atomically audit before/after records and activation transitions.

Prepare source: `python scripts/maintenance/migrations/build_academic_sections.py`.
Check parity: `python scripts/maintenance/migrations/build_academic_sections.py --check`.
Offline source tests check schema, tenant, lifecycle, permission, audit and
generator contracts. They do not establish live PostgreSQL behavior.
