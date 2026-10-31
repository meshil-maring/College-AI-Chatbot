# Academic workspace integration

Additive migration after the export alignment. The eight existing tables and
their APIs retain their contracts and records. This adds program progression,
versioned curriculum mappings, admission cohorts, batch-owned class sections and
subject offerings. It never converts an offering-owned legacy section into a class.

Draft curricula accept mappings from the same program's progression semesters.
Publication requires an active mapping and freezes metadata and mappings.
Published versions may be archived, retaining cohort assignments. A batch must
select a published version of its own program, and cannot later change that
assignment. Sections select that batch, a program semester and a dated term.
Offerings must select a mapped subject from that section's assigned curriculum
and progression stage. Dated terms and program semesters remain separate.

All writes go through `manage_academic_structure_record`, reuse exact institution
admin permission checks and the existing tenant advisory lock, and audit atomically.
Program semesters and batches use `departments`; curriculum and class delivery
use `courses` grants. Browser table access and direct service writes are denied.
Composite foreign keys, active ancestry checks and deactivation guards enforce
tenant boundaries and relationships independently of API validation.

Student enrollment is not restored by this migration. Student totals remain
unavailable until an enrollment source is connected; expected capacity is never
presented as enrolled students. No sample records are inserted.

Generate: `python scripts/maintenance/migrations/build_academic_workspace.py`.
Check parity with `--check`. Review the generated migration against the target's
migration history before applying it; generation does not execute SQL.

The same generator produces the forward-only `academic_curriculum_subject_snapshots`
migration. Apply it after the integration migration when updating an existing
database: it adds and backfills the curriculum snapshot columns, then updates the
publication trigger. The original integration migration may already be recorded
as applied, so editing that historical migration alone will not update a live DB.
