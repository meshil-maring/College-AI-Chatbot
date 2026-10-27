# Academic Setup database integration

All eleven Academic Setup entities use authenticated institution-scoped backend
APIs. The black-and-yellow layouts retain responsive tables/cards, filters,
pagination, accessible modal drawers and pinned actions. No sample records are
inserted or substituted when the database is empty or unavailable.

## Storage and API ownership

| Screen              | Storage               | Backend API                 |
| ------------------- | --------------------- | --------------------------- |
| Departments         | `departments`         | `/admin/academic-setup`     |
| Programs            | `programs`            | `/admin/academic-setup`     |
| Academic Years      | `academic_years`      | `/admin/academic-setup`     |
| Academic Terms      | dated `semesters`     | `/admin/academic-setup`     |
| Subjects            | reusable `courses`    | `/admin/academic-setup`     |
| Program Semesters   | `program_semesters`   | `/admin/academic-structure` |
| Curriculum Versions | `curriculum_versions` | `/admin/academic-structure` |
| Curriculum Subjects | `curriculum_subjects` | `/admin/academic-structure` |
| Batches             | `admission_cohorts`   | `/admin/academic-structure` |
| Academic Sections   | `academic_sections`   | `/admin/academic-structure` |
| Academic Offerings  | `academic_offerings`  | `/admin/academic-structure` |

Each API exposes a readable catalogue plus server-advertised manageable entities,
and POST/PATCH record operations. Public URLs include the existing `/api/v1`
prefix. Actor and institution come from verified server authorization.

The existing eight-entity API and offering-owned `sections` retain their
contracts and data. Existing program-course mappings remain available through
Curriculum's Existing Program Mappings tab and the existing catalogue workflow.
They are not silently converted into curriculum versions or class sections.

## Building the academic structure

1. Create a department, degree program, academic year and dated teaching terms.
2. Create reusable subjects and the program's progression semesters.
3. Create a draft curriculum version for the program and academic year.
4. Map subjects to that version's program semesters, retaining type and required
   status. Program semesters must belong to the same program and fit the version.
5. Publish the curriculum after adding at least one active mapping. Publication
   records its timestamp and freezes metadata and subject mappings.
6. Create a batch with a published curriculum for its program. Program,
   curriculum, intake academic year and year boundaries remain immutable.
7. Create a section for the batch, a program semester and a dated teaching term.
   These relationships and its code remain immutable after creation.
8. Create academic offerings by selecting subjects from the section's assigned
   curriculum and progression semester.

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
