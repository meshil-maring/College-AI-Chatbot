# Academic Setup database integration

For visual rules, follow the shared [design system](DESIGN_SYSTEM.md). This guide
defines Academic Setup's storage, behavior and integration boundaries.

All eleven Academic Setup entities use authenticated institution-scoped backend
APIs. The black-and-yellow layouts retain responsive tables/cards, filters,
pagination, accessible modal drawers and pinned actions. No sample records are
inserted or substituted when the database is empty or unavailable.

## Storage and API ownership

| Screen               | Storage               | Backend API                 |
| -------------------- | --------------------- | --------------------------- |
| Departments          | `departments`         | `/admin/academic-setup`     |
| Programs             | `programs`            | `/admin/academic-setup`     |
| Academic Years       | `academic_years`      | `/admin/academic-setup`     |
| Academic Terms       | dated `semesters`     | `/admin/academic-setup`     |
| Subjects             | reusable `courses`    | `/admin/academic-setup`     |
| Program Semesters    | `program_semesters`   | `/admin/academic-structure` |
| Curriculum Versions  | `curriculum_versions` | `/admin/academic-structure` |
| Subjects by semester | `curriculum_subjects` | `/admin/academic-structure` |
| Batches              | `admission_cohorts`   | `/admin/academic-structure` |
| Academic Sections    | `academic_sections`   | `/admin/academic-structure` |
| Academic Offerings   | `academic_offerings`  | `/admin/academic-structure` |

Each API exposes a readable catalogue plus server-advertised manageable entities,
and POST/PATCH record operations. Public URLs include the existing `/api/v1`
prefix. Actor and institution come from verified server authorization.

The existing eight-entity API and offering-owned `sections` retain their
contracts and data. Legacy program-course mappings remain available through
Curriculum's Legacy program mappings tab and the existing catalogue workflow.
They do not populate versioned curricula; use versioned curricula for new batch
study plans and retain legacy mappings only for workflows that still require them.
They are not silently converted into curriculum versions or class sections.

## Building the academic structure

The setup guide follows Foundations → Curriculum → Batches → Classes & subjects
→ Student enrollment. Its next-step actions open the existing authorized screens;
they do not publish curricula or create records automatically. Semester subjects,
Version History and Student Enrollment are direct navigation destinations.
Curriculum tabs, the sidebar, search results and browser history stay synchronized.
The Subjects by semester view presents a curriculum as a study plan. Select one
curriculum and add subjects within its numbered semester cards; the subject form
retains that curriculum and semester automatically. Compulsory subjects apply to
every student; Student choice subjects and their complete option groups are
managed inside the same semester card. There is no separate Subject Options tab.
Publication reviews saved subjects and groups and waits for open choice drafts
to be saved or cancelled. Existing server validation still applies.
Before publishing, administrators see active-subject coverage and warnings for
empty or unconfigured semesters. These are review prompts, not new publication
requirements. Published versions of the same program can be compared in Version
History to review added, removed and changed subject mappings. A published or
archived plan can also be cloned into an independent draft, including its subject
mappings and saved choice groups; a failed clone keeps any partial draft for
manual review instead of creating duplicates on retry. Bulk semester setup shows
progress and can be retried safely after a partial failure.
After publishing, the plan is read-only and links to batch assignment. The existing
catalogue subscriptions, identity guards, permissions and single-record writes are
reused; this interface change needs no additional database migration.
The guide shows a short description for each step and explains the key distinctions
in context: calendar terms are dated teaching periods, program semesters are
numbered curriculum stages, batches group an intake with its curriculum, and
sections represent class groups within a batch. Sections remain optional and
are created manually from the post-batch shortcut when needed.
The Academic Setup overview derives a recommended next action and four readiness
states from tenant-scoped saved records for the selected active program. Programs
can be switched to inspect their own department subjects, curricula, batches,
sections and offerings; shared academic years remain institution-wide. Missing
prerequisites are shown before later steps, and unavailable data is never
presented as an empty setup. Class delivery is labeled optional until sections
are needed.

Semester cards use a raised header with a 20px title, 16px section headings,
14px medium-weight subject names and 12px regular metadata, all expressed through
the shared rem-based type tokens. Subject lists and student choices sit in inset
panels with consistent spacing. Empty-state copy remains normal body text, and
choice-group names and option labels follow the same heading hierarchy.

1. Create a department, degree program, academic year and dated teaching terms.
2. Create reusable subjects and the program's progression semesters.
3. Create a draft curriculum version for the program and academic year.
4. Map subjects to that version's program semesters, retaining type and required
   status. Program semesters must belong to the same program and fit the version.
   In the same semester card, group optional mappings into complete alternatives; keep
   subjects shared by every student marked Required.
5. Publish the curriculum after adding at least one active mapping. Publication
   records its timestamp and freezes metadata and subject mappings.
6. Create a batch with a published curriculum for its program. Program,
   curriculum, intake academic year and year boundaries remain immutable. After
   saving, use Set up sections to continue to class grouping; this shortcut does
   not create a section automatically.
7. Create a section for the batch, a program semester and a dated teaching term.
   These relationships and its code remain immutable after creation.
8. Create academic offerings by selecting subjects from the section's assigned
   curriculum and progression semester.
9. In Sections, use Manage Student Enrollment to assign approved active students
   to a section. Students then complete Semester Registration by choosing exactly
   one option per group. Every required and selected subject must be offered.

Publication preserves option groups with the curriculum. The separate
[registration guide](../../supabase/migration_sources/semester_registration/README.md)
documents permissions, atomic enrollment, capacity, snapshots and lifecycle limits.

Use Add subject or Edit within a semester while preparing its choice groups.
The group name and option selections are preserved while subject drawers are open.
New subjects default to compulsory; uncheck Every student must take this subject
for subjects available to choices. Every option must have a name and at least one selected
optional subject. Save explains missing entries instead of silently disabling
the action. An empty curriculum needs subject mappings before an option can be
saved; creating a curriculum version does not copy mappings from other versions.

A cohort retains its curriculum even after that version is archived. Published
versions cannot revert to draft, and archived versions cannot be republished.
Archival does not reassign any historical cohort. Subject catalogue metadata is
reusable; publication freezes mapping structure rather than copying subjects.

Academic Terms describe dates within an academic year. Program Semesters describe
progression within a degree. They remain separate selectors and relationships.
Subjects display assignments from both existing dated-term mappings and versioned
program-semester mappings, with labels that distinguish their meanings.

## Access, errors and lifecycle

Every operation requires exact institution-scoped administrator authority and
active institution/organization ancestry. Existing grants are reused:
`departments.read/manage` covers programs, progression semesters and batches;
`courses.read/manage` covers subjects, curricula and class delivery. Years and
dated terms retain their own grants. Browser table access and direct service
writes are denied; database writes use audited security-definer RPCs.

Catalogue records and parent choices are tenant-verified. Missing catalogues show
Unavailable, confirmed empty catalogues show zero, and denied reads expose no
records. Failed refreshes mark retained data stale and block changes until Retry
succeeds. Identity replacement remounts screens, clears drafts and prevents late
save callbacks from changing or refetching replacement-identity state.

Forms keep drafts after conflicts, validation failures and network errors.
Repeated submission is blocked while saving. Changed drafts require discard
confirmation; existing status changes and publication require explicit
confirmation. Database uniqueness, active-parent checks, composite tenant foreign
keys, immutable assignments and deactivation guards remain authoritative.
All academic writes share the same tenant advisory lock and audit atomically.

Maximum capacity and expected intake remain separate from enrollment. No student
enrollment source is connected in this task, so enrolled-student totals display
Unavailable rather than invented zeros or old sample counts. Attendance,
results, teaching assignments and program-outcome authoring remain separate work.

## Overview and implementation

The overview's management cards read available catalogue counts. Quick links
navigate to manageable structure areas; foundation creation shortcuts open their
existing drawers. Recent activities come from tenant-filtered successful academic
audit entries and expose no actor or unrelated administrative audit details.

Transport lives in `services/admin/academics.ts` and `academicStructure.ts`;
contracts live in `types/academicSetup.ts` and `academicStructure.ts`.
`academic-setup/structure/` owns the shared identity-scoped structure query,
mutation guard, declarative controls and record drawers used by real consumers.
Batches and Sections retain their focused feature hooks, adapters, components,
editors, styles and adjacent regression tests. Curriculum's versioned workflow
lives in `curriculum/versioning/`; existing mapping UI remains separate.

Database sources live in `supabase/migration_sources/academic_workspace/`.
Generate the forward migration with
`python scripts/maintenance/migrations/build_academic_workspace.py`; add
`--check` to verify parity. Historical migrations and archived data are retained.

The confirmed project received prerequisites 20261023010000, 20261024000000,
20261024010000 and 20261026000000, followed by the additive 20261027000000
integration on 2026-10-27. Live catalogue reads, table security and migration
history were verified. Review each target's actual history before deployment.
Unrelated unapplied historical approval migrations must not be included merely
to make a broad migration push succeed. Local deployment evidence and rollback
rehearsal results belong in `logs/backend/`; frontend checks and browser evidence
belong in `logs/frontend/`.

From `backend/`, `python scripts/validation/verify_academic_workspace.py` runs a
read-only catalogue check using a database-resolved administrator scope. It
prints counts and capabilities without exposing identities or record contents.
