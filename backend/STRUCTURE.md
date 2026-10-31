# Backend structure and file rules

This is the shared convention for backend changes. Layer READMEs describe the
modules within that layer; keep them consistent with this guide.

## Before adding files or growing modules

Follow the [shared project rules](../AGENTS.md) before creating any file. Inspect
the existing feature and layer, search for reusable implementations, and place
new code within the established ownership structure.

Keep each folder at or below 15 directly contained, project-maintained files,
including tests, docs, configuration, and `__init__.py` markers. Before adding a
sixteenth file, or adding anything to an already oversized folder, group related
modules into descriptive subpackages by feature, workflow, or responsibility.
Apply the same limit to every resulting folder. Do not create numbered buckets
or empty packages merely to distribute file counts.

Keep source, test, and script files at or below 250 physical lines, including
imports, comments, and blank lines. Split responsibilities before exceeding the
limit. Preserve readable formatting, package markers, imports, public contracts,
and mock targets when extracting modules. Generated dependencies, build output,
caches, lockfiles, and archived evidence are excluded as defined in the shared
rules.

## Where files belong

```text
backend/
  app/
    main.py                     # App creation, middleware and router registration
    config.py                   # Application settings
    api/<feature>/              # HTTP endpoints and router composition
    services/<feature>/         # Business rules and use-case orchestration
    repositories/<feature>/     # Database reads, writes and RPC calls
    schemas/<feature>/          # Pydantic request, response and domain contracts
    core/                       # Shared errors, permissions, security, startup checks
    db/                         # Database client construction
    middleware/                 # HTTP middleware
    models/                     # Reserved package; currently has no model definitions
  tests/                        # Automated tests
  evaluation/                   # Retrieval evaluation harness and datasets
  scripts/
    diagnostics/                # Manual investigation tools
    manual_tests/               # Manual API and integration flows
    validation/                 # Offline checks and live-stack validation tools
    generate_frontend_rbac.py    # Offline policy generation
```

Local logs and test output belong in `../logs/backend/` at the repository root.
Database migrations belong in `../supabase/migrations/`. Phase reports, evidence
and locks belong in `../docs/`; retain historical paths and evidence as records.
Dependencies belong in `pyproject.toml` and `uv.lock`.

## Feature ownership

Use the same feature name across `api`, `services`, `repositories` and `schemas`
when that layer needs a module. Do not create empty feature folders just to make
all four layers identical.

| Feature | Owns |
| --- | --- |
| `academics` | Academic Setup foundations, dated terms, subjects, legacy mappings, versioned curricula, program progression, admission cohorts, sections and offerings |
| `admin` | Administrative workflows, dashboard and knowledge management |
| `ai` | Chat, conversations, generation and privacy safeguards |
| `auth` | Authentication, account registration, sessions and access policy services |
| `email` | Delivery, outbox and delivery webhooks |
| `invitations` | Invitations, acceptance and invitation recovery |
| `knowledge` | Documents, ingestion, embeddings, retrieval and storage |
| `platform` | Institutions, organizations, tenancy and platform operations |
| `students` | Account identity profiles, notices, resources and notifications |
| `shared` | Reusable repository paging helpers; currently only in `repositories` |

Choose the owner of the operation rather than its audience alone. Student account
creation belongs in `auth`, profile reads in `students`, and signup
invitations in `invitations`. Cross-feature imports may reuse the owning module;
do not duplicate implementations. Add a feature when a real domain requires it,
and update this table, the checker and the affected layer guides together.

Academic Setup follows the owner-selected [schema export](../academic_state_check_latest.sql).
Departments own degree programs and teaching courses. Academic years contain dated
semesters. Program-course links define curricula; course offerings connect a
linked course, program, year and semester. Sections belong to one offering.
The additive [department deletion migration](../supabase/migration_sources/department_deletion/README.md)
allows permanent deletion only without foreign-key consumers, including inactive
records. Exact institution-admin grants, ownership, serialized checks and atomic
auditing protect the narrow DELETE endpoint; account records are preserved.
The [program deletion migration](../supabase/migration_sources/program_deletion/README.md)
adds the same guarded operation for unused degree programs, deriving institution
ownership through their department and preserving all linked academic history.
The [calendar/section deletion migration](../supabase/migration_sources/calendar_section_deletion/README.md)
adds unused academic-year, dated-semester and cohort-owned class-section deletion.
Current periods and every FK dependency prevent removal, including student
assignments/registrations. Existing offering-owned legacy sections stay separate.
Descendant tenants derive from parent relationships, with server-owned institution
context added to API records. Attendance, results, teaching workflows and the
retired academic packages remain outside this implementation. Earlier setup tables
are preserved privately by the [forward migration](../supabase/migration_sources/academic_export/README.md).

The additive [workspace migration](../supabase/migration_sources/academic_workspace/README.md)
connects program semesters, curriculum versions/subjects, admission cohorts,
academic sections and academic offerings through `academic_structure.py` modules
in the four academic layers. It preserves all export-aligned tables and APIs.
Cohorts retain their published curriculum; sections reference a cohort, program
semester and dated term. Subject offerings must match that assignment. All
writes use exact institution-admin grants, the existing tenant advisory lock and
atomic auditing. Existing setup summary enrollment counts and teaching workflows
remain separate integrations.

The additive [semester-registration migration](../supabase/migration_sources/semester_registration/README.md)
adds curriculum choice groups, administrator section assignments and a student's
whole-option course enrollment. `semester_registration.py` in the four academic
layers owns this workflow. Separate own-registration grants protect student reads
and writes; SQL rechecks identity, ownership, tenant, required subjects, offerings
and capacity atomically. Recorded subject snapshots preserve names and credits.
Retained academic-package code remains disconnected.

## Naming and module boundaries

- Use lowercase `snake_case` for Python files and package directories. Include
  `__init__.py` in each application package.
- Keep the four feature-layer roots limited to `__init__.py`, `README.md` and
  feature packages. Put implementation files inside their feature.
- Keep feature-layer package markers empty or docstring-only. Import from the
  owning module explicitly; update mock targets and source references when moving
  it. Do not add aliases that hide obsolete flat paths.
- The explicit public exports in `core/security/__init__.py` and
  `core/startup_validation/__init__.py` preserve existing APIs and dependency
  identity. Retain those exports when reorganizing their implementations.
- Give each module a coherent responsibility. Split a growing module at a
  workflow boundary; keep router assemblers small and use feature-local
  `common.py` or `dependencies.py` only for genuinely shared code. The 250-line
  file limit is mandatory; choose meaningful responsibility boundaries when
  splitting a file.
- Avoid generic dumping grounds such as `misc.py`, `utils2.py`, backup source
  files or numbered copies. Reuse an owning module or name a specific helper.
- Put automated tests in `tests/test_<behavior>.py` or a related feature group
  such as `tests/<feature>/test_<behavior>.py`, respecting the 15-file folder
  limit. Existing phase test names remain valid. Manual tools stay under
  `scripts/` and follow the same folder and file size limits.

## Responsibilities and safe changes

API modules handle HTTP inputs, dependencies and responses. Services coordinate
business operations. Repositories own database queries and RPC calls. Schemas
define data contracts. Shared infrastructure stays in `core`, `db` or
`middleware` rather than in an unrelated feature.

Existing authorization dependencies can resolve database/service state; existing
provider adapters can live beside their owning service. This guide does not
impose a new dependency graph on those established integrations.

When moving code, preserve URL prefixes, permission coverage, tenant filters,
validation, query projections, pagination, return values and error behavior.
Preserve function-local imports that defer circular dependencies. Do not import
the application or load credentials merely to inspect source structure.

Keep generated caches, virtual environments and local output out of Git. Delete
obsolete helpers only after checking callers; keep useful diagnostics in the
appropriate scripts folder. Do not rename migrations or historical evidence as
part of a layout cleanup.

## Verification

From `backend/`, run the offline structure check:

```powershell
python scripts/validation/check_structure.py
```

It checks feature placement, Python naming, package markers, passive feature
initializers, stray runtime output and absolute `app` import module paths in
application code, tests and backend scripts. It reads source only and requires
no credentials or third-party packages. It does not prove business-layer
separation, resolve imported symbols, or inspect dynamic import/mock strings.
It currently does not check numeric folder or file size limits; review affected
folders and files against the mandatory 15-file and 250-line rules as well.

The automated suite also runs this check through `tests/test_backend_structure.py`.
Default pytest discovery is limited to `tests/` in `pyproject.toml`; live-stack
validation scripts under `scripts/` are explicit manual entry points.
Authentication fixtures shared by legacy account tests live in `tests/auth_fixtures/`.
JWT/identity and hardening tests live in `tests/authentication/`, document pipeline
tests in `tests/knowledge/`, history tests in `tests/ai/history/`, and organization
foundation tests in `tests/platform_tenancy/`. These groups preserve the original
test cases while keeping support and behavior-specific modules within size limits.
AI generation API, persistence, citations, response projection and public contract/
policy/retrieval tests live in focused `tests/ai/` subpackages. Resource API, upload
and history-policy tests live in `tests/knowledge/resources/`; SQL integration
checks live in `../scripts/validation/knowledge_revisions/`.
For a code move, additionally check affected mock targets and imports, run the
relevant regression tests, and compare API contracts when routers or schemas
are affected. Check the frontend RBAC snapshot when permission/role sources
change (`python scripts/generate_frontend_rbac.py --check`).
