# Academic Setup source map and verification

[Reading guide](README.md) · [Design review](DESIGN_REVIEW.md)

## Evidence boundary

This record was assembled on 28 October 2026 by inspecting the active workspace,
contracts, services, repositories, migration sources and adjacent tests. Source
baseline: commit `93fafa4`, with pre-existing local frontend documentation changes.
It does not infer current production state from filenames or historical reports.

The existing frontend integration guide records deployment verification on
27 October 2026. That is historical evidence. This documentation task does not
apply migrations, create accounts, insert fixtures or certify the live schema.

## Frontend source map

All paths below are repository-relative; linked files identify the owning entry.

| Responsibility                       | Source                                                                                                                                                                                                                       |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Admin view/navigation state          | [AdminShell.tsx](../../../frontend/src/features/admin/AdminShell.tsx), [adminNavigation.ts](../../../frontend/src/features/admin/adminNavigation.ts)                                                                         |
| Academic identity and page dispatch  | [AcademicWorkspace.tsx](../../../frontend/src/features/admin/academic-setup/overview/AcademicWorkspace.tsx)                                                                                                                  |
| Overview sections, labels and search | [academicOverviewModel.ts](../../../frontend/src/features/admin/academic-setup/overview/academicOverviewModel.ts), [AcademicOverview.tsx](../../../frontend/src/features/admin/academic-setup/overview/AcademicOverview.tsx) |
| Shared foundation reads              | [useAcademicOverview.ts](../../../frontend/src/features/admin/academic-setup/overview/useAcademicOverview.ts)                                                                                                                |
| Composed workspace catalogue         | [useAcademicStructure.ts](../../../frontend/src/features/admin/academic-setup/structure/useAcademicStructure.ts)                                                                                                             |
| Guarded saves and generic editor     | [useStructureWrite.ts](../../../frontend/src/features/admin/academic-setup/structure/useStructureWrite.ts), [useStructureEditor.ts](../../../frontend/src/features/admin/academic-setup/structure/useStructureEditor.ts)     |
| Relationship-driven form definitions | [structureFields.ts](../../../frontend/src/features/admin/academic-setup/structure/structureFields.ts)                                                                                                                       |
| Calendar recovery                    | [saveCalendar.ts](../../../frontend/src/features/admin/academic-setup/calendar/editor/saveCalendar.ts), [useCalendarEditor.ts](../../../frontend/src/features/admin/academic-setup/calendar/useCalendarEditor.ts)            |
| Curriculum views and history         | [VersionedCurriculumPage.tsx](../../../frontend/src/features/admin/academic-setup/curriculum/versioning/VersionedCurriculumPage.tsx)                                                                                         |
| Persisted batch/section adapters     | [batchStorage.ts](../../../frontend/src/features/admin/academic-setup/batches/batchStorage.ts), [sectionStorage.ts](../../../frontend/src/features/admin/academic-setup/sections/sectionStorage.ts)                          |
| Subject assignment display           | [subjectModel.ts](../../../frontend/src/features/admin/academic-setup/subjects/subjectModel.ts)                                                                                                                              |
| Existing generic catalogue           | [AcademicSetup.tsx](../../../frontend/src/features/admin/academic-setup/AcademicSetup.tsx), [useAcademicSetup.ts](../../../frontend/src/features/admin/academic-setup/useAcademicSetup.ts)                                   |
| Typed contracts                      | [academicSetup.ts](../../../frontend/src/types/academicSetup.ts), [academicStructure.ts](../../../frontend/src/types/academicStructure.ts)                                                                                   |
| Transport                            | [academics.ts](../../../frontend/src/services/admin/academics.ts), [academicStructure.ts](../../../frontend/src/services/admin/academicStructure.ts), [http.ts](../../../frontend/src/services/admin/http.ts)                |
| Query lifetime                       | [useApiQuery.ts](../../../frontend/src/hooks/useApiQuery.ts), [queryClient.ts](../../../frontend/src/lib/queryClient.ts)                                                                                                     |
| Visual/integration rules             | [DESIGN_SYSTEM.md](../../../frontend/docs/DESIGN_SYSTEM.md), [ACADEMIC_SETUP_DESIGN.md](../../../frontend/docs/ACADEMIC_SETUP_DESIGN.md)                                                                                     |

## Backend source map

Both API families use the filename shown in each layer, under `academics/`.

| Layer              | Foundation/export                                                                  | Additive workspace                                                                         |
| ------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| API                | [academic_setup.py](../../../backend/app/api/academics/academic_setup.py)          | [academic_structure.py](../../../backend/app/api/academics/academic_structure.py)          |
| Services           | [academic_setup.py](../../../backend/app/services/academics/academic_setup.py)     | [academic_structure.py](../../../backend/app/services/academics/academic_structure.py)     |
| Repositories       | [academic_setup.py](../../../backend/app/repositories/academics/academic_setup.py) | [academic_structure.py](../../../backend/app/repositories/academics/academic_structure.py) |
| Pydantic contracts | [academic_setup.py](../../../backend/app/schemas/academics/academic_setup.py)      | [academic_structure.py](../../../backend/app/schemas/academics/academic_structure.py)      |

Shared service helpers:
[authorization](../../../backend/app/services/academics/authorization.py),
[parent validation](../../../backend/app/services/academics/parent_validation.py) and
[database errors](../../../backend/app/services/academics/database_errors.py).
Complete internal reads use the shared
[query paging helper](../../../backend/app/repositories/shared/query_pages.py).

## Schema and migration lineage

| Migration                                           | Purpose / source of truth                                                                                                                                  |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261023000000_decommission_academic_domain.sql`   | Retires prior academic runtime; [source guide](../../../supabase/migration_sources/academic_decommission/README.md)                                        |
| `20261023010000_academic_foundations.sql`           | Initial replacement foundations and exact admin authorization; [source guide](../../../supabase/migration_sources/academic_foundations/README.md)          |
| `20261024000000_academic_structure.sql`             | Earlier progression/structure baseline; [source guide](../../../supabase/migration_sources/academic_structure/README.md)                                   |
| `20261024010000_academic_sections.sql`              | Earlier sections baseline; [source guide](../../../supabase/migration_sources/academic_sections/README.md)                                                 |
| `20261026000000_academic_export_alignment.sql`      | Preserves earlier setup privately and adopts the owner's eight-table export; [source guide](../../../supabase/migration_sources/academic_export/README.md) |
| `20261027000000_academic_workspace_integration.sql` | Adds current versioned curricula, cohorts, sections and offerings; [source guide](../../../supabase/migration_sources/academic_workspace/README.md)        |

The root [academic SQL export](../../../academic_state_check_latest.sql) is a
reference snapshot, not the instruction to execute an entire database dump.
Older migrations are historical; active API/schema code and the forward export
and workspace sources establish the current academic contract.

Maintained SQL is split into feature-owned source files. Generators assemble
the corresponding migration; `--check` verifies parity without executing SQL.
Do not edit a historical migration to implement a new lifecycle decision.
Review a target database's actual migration history before deployment; the
export conversion expects its particular preceding baseline.

## Existing automated coverage

| Area                                                                            | Tests / evidence                                                                                                   |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Foundation contracts, API, service, repository and export parity                | `backend/tests/academics/test_*.py`                                                                                |
| Earlier structure contracts and service rules                                   | `backend/tests/academics/test_structure_*.py`                                                                      |
| Additive workspace API permissions, payloads, immutability and migration parity | `backend/tests/academics/workspace/`                                                                               |
| Foundation and workspace frontend transport                                     | `frontend/src/services/admin/academics.test.ts`, `academicStructure.test.ts`                                       |
| Existing setup workflow, relationships and session handling                     | `frontend/src/features/admin/academic-setup/AcademicSetup*.test.tsx`                                               |
| Dedicated lists, editors, access and recovery                                   | Adjacent `__tests__/` under departments, programs, calendar, subjects, curriculum, batches, sections and structure |
| Workspace composition                                                           | `frontend/src/features/admin/academic-setup/overview/AcademicWorkspace.test.tsx`                                   |

Unit/API tests often mock database access or override authentication dependencies.
They validate contracts and orchestration, but do not alone prove live JWT login,
PostgreSQL trigger behavior or concurrent database isolation.

## Verification for this documentation change

Checks run on 28 October 2026:

| Check                                                    | Result                                                                                                   |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Frontend `npm.cmd run check:structure`                   | Passed; 569 code files checked                                                                           |
| Frontend `npm.cmd run build`                             | Passed; Vite reported a bundle-size warning                                                              |
| Frontend targeted academic workspace and transport tests | 172 passed in 32 files                                                                                   |
| Backend `scripts/validation/check_structure.py`          | Passed                                                                                                   |
| Backend `pytest tests/academics -q -p no:cacheprovider`  | 208 passed; one dependency deprecation warning                                                           |
| Workspace migration generator `--check`                  | Passed; generated SQL matches maintained sources                                                         |
| Documentation structure and local references             | Seven feature documents, each below 250 lines; affected folders below 15 files; 127 local links resolved |

Frontend test command, from `frontend/`:

```powershell
npm.cmd test -- src/features/admin/academic-setup src/services/admin/academics.test.ts src/services/admin/academicStructure.test.ts
```

Backend tests used process-only `DEBUG=false`, `ENVIRONMENT=test` and
`EMAIL_ALLOW_LIVE_IN_DEVELOPMENT=false`. The first collection attempt encountered
an inherited `DEBUG=release`, which is not a valid boolean. No configuration file
was edited. Disabling pytest's cache provider avoided writing the protected local
pytest cache. These tests use their existing mocked database/authentication fixtures.

Logs use the `academic-architecture-` prefix: frontend `structure.log`, `build.log`,
`tests.log` and `format.log` under `logs/frontend/`; backend `structure.log`,
`tests.log`, `migration-parity.log` and `documentation.log` under `logs/backend/`.
Application source and database records are unchanged by this documentation update.

## Deeper validation tools

| Tool                                                                                                     | Environment and scope                                                                                                                                        |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Disposable database validator](../../../scripts/validation/academic_workspace/README.md)                | Docker-backed isolated PostgreSQL; replays migrations, seeds fictional tenants and checks relationships, roles, publication, audit and duplicate concurrency |
| [Read-only configured catalogue check](../../../backend/scripts/validation/verify_academic_workspace.py) | Uses configured database-resolved admin scope; prints counts and verifies tenants; does not test password/JWT login                                          |
| [Browser journey](../../../scripts/validation/academic_workspace/browser/README.md)                      | Development-only real authentication and browser saves; creates retained academic fixtures and a temporary test admin with documented cleanup                |
| [Retained offering loader](../../../scripts/validation/academic_workspace/offerings/README.md)           | Explicit development target; default dry run, `--apply` writes retained fictional data through audited writers                                               |

These are different evidence levels. The disposable validator does not contact a
configured project. The browser journey and retained loader can leave development
fixtures and are not equivalent to offline unit tests. They were not invoked as
part of writing this record.

## Review checklist for future changes

- Verify contracts across frontend types, transport, route, schema and writer.
- Check exact admin permission provenance and all tenant ancestry paths.
- Exercise publication immutability and assigned-batch preservation.
- Test activation/deactivation across both models' dependent records.
- Rehearse partial saves, uncertain outcomes and same-session token renewal.
- Verify replacement identity/grants discard drafts and ignore late callbacks.
- Distinguish empty, unreadable, unavailable and stale data in every summary.
- Keep archived source disconnected from active routes and imports.
- Validate file/folder limits, links, migration parity and affected regressions.
- Document what was actually run and what requires a separate live rehearsal.
