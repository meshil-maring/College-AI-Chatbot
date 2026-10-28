# Academic Setup security and lifecycle

[Reading guide](README.md) · [Application architecture](APPLICATION_ARCHITECTURE.md)

## Authorization model

Every academic endpoint uses `require_institution_roles("admin")`. Business
services resolve permissions from the administrator's exact institution scope.
They require active institution and organization ancestry and exclude grants
whose organization does not match the institution's organization.

| Permission resource          | Foundation/export entities                                               | Additive workspace entities                                                     |
| ---------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `departments.read/manage`    | Departments, programs                                                    | Program semesters, admission cohorts                                            |
| `academic_years.read/manage` | Academic years                                                           | None directly                                                                   |
| `semesters.read/manage`      | Dated semesters                                                          | None directly                                                                   |
| `courses.read/manage`        | Courses, program-course links, course offerings, offering-owned sections | Curriculum versions, curriculum subjects, academic sections, academic offerings |

Read and manage are separate checks. Catalogue output includes only readable
entities, and its manageable list is restricted to those readable entities that
also have management permission. Valid wildcard grants are handled by the existing
permission machinery. The resource names above are the current grouping, not
independent grants for every academic entity.

Student, faculty and staff authority does not authorize these endpoints. A
platform/organization administrator or super administrator role alone does not
substitute for an institution-scoped admin assignment. A user with multiple roles
must still satisfy the applicable institution admin assignment.

## Database authority

Both writer RPCs call `assert_academic_foundation_actor`. It requires a trusted
`service_role` call and checks the active user, admin role, institution assignment,
organization ancestry and active management permission in PostgreSQL.

Authority and permission must come from the same institution admin role
assignment. Delegated user permissions cannot supply a missing academic role
permission. Matching rows are locked `FOR SHARE` during this validation, preventing
those authorization records from changing underneath the transaction.

Browser roles `anon` and `authenticated`, along with `PUBLIC`, receive no direct
academic-table access. `service_role` can select the tables and execute the writer
RPCs, but has no direct insert/update/delete grants on those tables. RLS is enabled;
security relies on these restricted privileges plus backend tenant filtering and
the security-definer functions. A trusted database owner remains privileged.

Security-definer helpers set an empty search path and use explicit schema names.
The backend owns the service credential. The browser sends a user bearer token
to FastAPI and never supplies a service credential for academic database access.

## Tenant isolation

Foundation departments and academic years physically store the institution ID.
Programs and subjects derive it from their department; dated terms derive it from
their academic year. Mapping and delivery records derive it through their parents.
Repository inner joins filter all relevant ancestry by the selected institution.
The API adds a derived institution field to descendant records for a uniform UI.

The additive workspace physically stores institution IDs on all six tables.
Composite foreign keys pair workspace parent IDs with the tenant ID. Where a
parent is an export-aligned table without that tenant column, recursive parent
validation establishes its institution and active ancestry. Relationships also
check matching program, stage bounds and the assigned curriculum.

API request models forbid caller-supplied actor and institution fields. The
service passes both from verified user context. Foreign-tenant update lookups
return not found before reaching the writer. Frontend tenant checks add display
protection, while server/database checks remain authoritative.

## Transactions, concurrency and audit

| Writer                             | Owns                                    |
| ---------------------------------- | --------------------------------------- |
| `manage_academic_master_record`    | Eight export-aligned catalogue entities |
| `manage_academic_structure_record` | Six additive workspace entities         |

For a normal record save, the writer:

1. Selects the allowlisted entity, fields and permission resource.
2. Checks trusted database role and exact actor authority.
3. Rejects unsupported or immutable input fields.
4. Acquires a transaction advisory lock for `academic-setup:<institution UUID>`.
5. Reads an existing record `FOR UPDATE` when editing and validates its tenant.
6. Inserts/updates the record; triggers enforce relationships and lifecycle.
7. Inserts before/after data in `admin_audit_log` within the same transaction.
8. Returns the saved record; any error rolls the complete transaction back.

Both API families share the same tenant lock, so a child creation and parent
deactivation within an institution cannot bypass each other through separate
writers. Unique indexes additionally reject duplicate races. This serializes
academic writes per institution and is a throughput tradeoff for future bulk work.

The lock does not provide a multi-screen transaction, a consistent snapshot for
catalogue reads or optimistic edit protection. Two valid sequential updates can
still overwrite the same field because PATCH does not require an expected version.
Repeated create attempts have no application-level idempotency key.

Foundation audit actions distinguish create/update/activate/deactivate. Workspace
actions use create/update; lifecycle meaning remains in the before/after data.
Recent activity selects successful academic entries for the current tenant and
readable entities, ordered newest first and limited to 20. The response omits actor
details and raw before/after payloads.

## Active ancestry and immutable assignments

New records and activation require valid active ancestry. Publication rechecks
active mappings and their ancestry. The database allows many metadata edits and
deactivation operations without revalidating all active ancestry, so preserved
records can still be maintained after permitted parent changes.

The update contracts and writer allowlists prevent reparenting. Foundation
triggers additionally reject changed ID columns and offering-section codes.
Workspace constraints and lifecycle triggers enforce tenant relationships,
published mapping immutability and supported status transitions. Normal direct
service writes are unavailable, so RPC allowlists are part of the security boundary.

## Deactivation dependencies

The guards reject an active-to-inactive transition when active dependents remain.
They do not silently cascade deactivation or delete historical rows.

| Parent                       | Active dependents that block deactivation                                                       |
| ---------------------------- | ----------------------------------------------------------------------------------------------- |
| Department                   | Programs, reusable subjects                                                                     |
| Program                      | Existing program-course links and offerings; program semesters, curriculum versions and batches |
| Reusable subject             | Existing links/offerings; curriculum subject mappings                                           |
| Academic year                | Dated terms and existing offerings; curriculum versions and batches                             |
| Dated term                   | Existing links/offerings; academic sections                                                     |
| Existing program-course link | Existing offerings for that program/subject                                                     |
| Existing course offering     | Offering-owned sections                                                                         |
| Program semester             | Curriculum subject mappings and academic sections                                               |
| Curriculum version           | Curriculum subject mappings and active batches                                                  |
| Curriculum subject           | Academic offerings; publication also freezes mapping edits                                      |
| Batch                        | Academic sections                                                                               |
| Academic section             | Academic offerings                                                                              |

For ordinary delivery closure, deactivate academic offerings, then sections, then
complete/inactivate the batch as appropriate. Reactivation rechecks active
ancestry. A batch's status controls its generated active flag; status is not a
student promotion or graduation operation.

## Archival is a separate lifecycle dimension

Curriculum publication status and `is_active` are separate columns. Archiving
preserves the publication timestamp and batch references and prevents selection
by new batches. It does not automatically clear `is_active` on the version or
its mappings, and existing active assignments can continue delivery.

Published mapping rows cannot be edited, including turning their active flag
off. Consequently, a published/archived version with an active mapping cannot
simply be boolean-deactivated, and that mapping can continue to block retirement
of its reusable subject or program semester. The dedicated version editor also
freezes non-status fields after publication.

This is an important closure-policy issue for review, not a procedure to bypass
the guards. A future retirement design should distinguish preserved historical
dependencies from present teaching activity while retaining tenant isolation and
audit history. Archival alone is not full retirement of the academic graph.

## Preserved migration history

The export-alignment migration preserves the superseded seven-table setup in the
private `academic_setup_previous` schema, revokes browser/service privileges and
disables old writers. Common foundations and reusable subjects retain IDs when
copied into the export-aligned model. Old progression/class records are not
invented as dated terms or single-course sections.

The workspace migration adds its six tables and guards without replacing the
eight export tables or their writer. Prior archived data does not become active
workspace data automatically. Historical retention does not imply enrollment,
teaching or attendance endpoints have been restored.

Sources: [API authority](../../../backend/app/services/academics/authorization.py),
[database actor assertion](../../../supabase/migration_sources/academic_foundations/authorization.sql),
[foundation writer](../../../supabase/migration_sources/academic_export/write.sql),
[workspace writer](../../../supabase/migration_sources/academic_workspace/write.sql),
[foundation table security](../../../supabase/migration_sources/academic_export/security.sql),
[workspace table security](../../../supabase/migration_sources/academic_workspace/security.sql),
[recursive ancestry](../../../supabase/migration_sources/academic_workspace/parent_access.sql),
[workspace parent guards](../../../supabase/migration_sources/academic_workspace/parent_guards.sql) and
[export transition record](../../../supabase/migration_sources/academic_export/README.md).
