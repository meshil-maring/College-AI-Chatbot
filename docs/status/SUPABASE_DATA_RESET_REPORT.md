# Supabase data reset

Completed and independently verified on 7 October 2026 for **College AI Chatbot**,
project `rjnfmjcvkfotneswpygr`.

The user explicitly confirmed this project and requested deletion of application
records, all login accounts and Supabase Storage files, while preserving the
database structure and required role/permission configuration.

| Data | Before | After |
| --- | ---: | ---: |
| Application records across 47 tables | 4,250 | 0 |
| Auth accounts | 26 | 0 |
| Supabase Storage objects | 0 | 0 |
| Roles, preserved | 5 | 5 |
| Permissions, preserved | 78 | 78 |
| Role-permission mappings, preserved | 133 | 133 |
| Public tables, preserved | 50 | 50 |
| Supabase Storage buckets, preserved | 1 | 1 |

Post-reset checks also confirmed zero Auth identities, sessions and refresh
tokens. Supabase Storage was already empty, so no Storage deletion was needed.

The reset first ran successfully inside a transaction ending in `ROLLBACK`.
An independent inspection confirmed that all original rows and accounts were
still present after that rehearsal. The reviewed execution copy changed only
the final transaction statement to `COMMIT`, then executed against the explicit
confirmed project through `supabase db query --linked --project-ref`.

Application tables were truncated together with `RESTART IDENTITY RESTRICT`.
Auth accounts were deleted through `auth.users`, allowing managed foreign keys
to clear dependent user data. The transaction refused nonempty Storage, public
materialized views and public TRUNCATE triggers; verified that configuration
contents remained identical; and checked all target tables and accounts for
remaining rows before commit. A separate post-commit query independently
verified the empty data and unchanged configuration counts.

Schema objects, constraints, indexes, RLS, functions, migration history, Auth
service configuration and Storage bucket definitions were retained. No migration
was applied or replayed. Cloudflare R2 files and provider-managed service logs,
metadata and backups were outside the authorized reset. Existing workspace
changes were retained; no application source was changed or committed, and the
user's running server was not stopped.

**No local data backup was created.** Automatic approval review rejected the
proposed export because the user had authorized deletion but had not authorized
copying sensitive application/Auth records to the proposed local destination.
A backup choice was presented and remained unanswered. The authorized deletion
proceeded without making that data copy.

Maintenance SQL and instructions are in [scripts/maintenance](../../scripts/maintenance/README.md).
The reusable reset SQL defaults to `ROLLBACK`. The exact committed execution
copy is local and Git-ignored at
`supabase/.temp/data-reset-20261007/reset-authorized.sql`; it contains SQL only,
not an exported copy of any records. All three maintenance SQL files passed
`pglast` parsing. Validation used the real remote transaction rehearsal and
independent post-commit counts; no application test-suite run was needed for
these operational SQL/documentation additions.

No replacement administrator was created during this reset. A platform-scoped
Super Admin account is required for platform management. Public university
registration instead creates its own initial University Admin and needs no
Super Admin approval.

## University registration repair, 7 October 2026

The initial reset also removed the reserved `COLLEGE-AI-PLATFORM` organization
seeded by the existing Phase 7.13 migration. That row is system configuration:
the public university form sends its code automatically, and the backend must
resolve an active existing parent before creating a university. Its absence
caused `ORGANIZATION_NOT_FOUND` and the displayed organization-code error. This
dependency was missed in the initial reset.

`scripts/maintenance/restore_platform_organization.sql` restored that one system
row in the same remote project, without restoring deleted tenant records or
creating an account. The backend's actual `get_organization_by_code` lookup
confirmed that it resolves an active organization with no required join code.

The reusable reset SQL now recreates this canonical seed after clearing the
application tables and verifies that it remains usable. The inspector separates
preserved configuration rows from application rows, so this one required
organization is not counted as user data. The original reset execution copy
and before/after counts above describe the historical initial operation.

Verification for the repair passed: **49 backend registration tests** (one
existing Starlette/httpx deprecation warning), **2 frontend university
registration tests**, all four maintenance SQL files parsed with `pglast`, and
the new verifier passed Ruff and Python compilation. An independent live
inspection confirmed zero application records/accounts and one active system
organization with no join code.

`scripts/validation/verify_supabase_data_reset.py` replayed all **35 migrations**
in a new disposable local Docker database and passed seven database checks:
idempotent restoration without changing existing records; refusal to override
restricted onboarding; default rollback without data loss; nonempty Storage
refusal; cross-schema foreign-key refusal; committed reset with configuration
and onboarding retained; and restoration of a missing seed. Public migrations,
Auth/application fixture records and reset transactions ran on real PostgreSQL.
Storage checks used minimal synthetic metadata because the standalone database
image does not run the separate Storage service migrator. No live registration
account was created for testing. The verifier stopped only its own container.
