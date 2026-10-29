# Audience and revision database model

Implemented on 28 October 2026 as migration source and a generated SQL artifact.
Validated only in disposable PostgreSQL; no configured project was modified.
The [audience upload plan](AUDIENCE_UPLOAD.md) remains the product contract.

## Stored model

| Record                                    | Stored responsibility                                                                                                                         |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `knowledge_source_revisions`              | Tenant/source identity, ordered revision, metadata, visibility, effective dates, review provenance, lifecycle and revision concurrency token. |
| `knowledge_source_revision_audiences`     | Canonical student/staff/faculty/admin targets attached to one revision.                                                                       |
| `knowledge_source_revision_documents`     | Exact document/version manifest, with one version per document per revision.                                                                  |
| `knowledge_sources.published_revision_id` | Pointer to that source's one published revision; source metadata/visibility must match it.                                                    |
| `knowledge_sources.policy_version`        | Server-maintained counter for publication/audience/lifecycle/effective-date changes.                                                          |

The source/institution FK prevents cross-tenant revisions. Composite manifest FKs
prevent a revision from pinning another source's document or another document's
version. New drafts default to restricted visibility, no audience targets and no
live pointer. Unknown role names and duplicate targets are rejected.

Public/authenticated revisions cannot also carry selected-role targets. Restricted
drafts can be incomplete; submission requires nonempty targets and an indexed file manifest.
An existing role name in the target list does not grant any permission to a user.

## Review and version invariants

Revisions progress through draft, under review, approved and published, followed
by archive or supersession. Review freezes metadata and members; returning to
draft clears review/approval provenance. Approval requires recorded reviewers
and timestamps. Published history and reviewed file content are immutable.

Member edits lock the parent revision and advance its concurrency token. File
content edits also lock referencing revisions, so review cannot race past a
concurrent content edit. Writers must still compare the expected token when
accepting a review; the validation suite exercises this across two real sessions.
Processing-run edits lock referencing revisions too; removing the last successful
index for a live manifest is rejected at transaction completion.
Reviewed runs, chunks and embeddings are immutable, including writes through
legacy chunking/indexing routes; draft index writes advance the review token.

Deferred checks require the live source to match the published revision and its
indexed/published file manifest at transaction completion. A replacement may
stage alongside the live version; the publication writer supersedes the prior
revision, publish the new revision and switch source policy in one transaction.
Clearing the pointer or archiving the live revision alone is rejected.

## Conservative backfill

Only currently published, effective noncanonical Public/authenticated sources with eligible
published versions and ready/embedded/completed processing receive snapshots.
The newest eligible version per document enters the manifest. Legacy snapshots
are explicitly labeled and do not fabricate missing administrator approval.

The migration preserves existing source metadata, file rows, visibility and role
grants. Restricted, draft, expired, future, unindexed and metadata-only sources
receive no live pointer or inferred audience. Canonical FAQ/notice sources keep
their existing explicitly public workflow and are excluded from this backfill.

## Application and deployment boundary

New tables enable RLS and deny browser access. The trusted service role receives
SELECT only. Service-only RPCs now implement drafts, exact staged versions,
review, approval, atomic publication, unpublication and retry after failed
indexing. Each writer rechecks active scoped grants and ownership and commits
its audit event atomically. Expected revision and live-policy tokens prevent
stale edits and publication. See the [API contract](API.md).

Shared predicates now filter library metadata, student resources and vector
candidates before ranking/limits. Authenticated answers store source-policy and
version provenance synchronously; delivery and history restoration revalidate it.
An invalid assistant turn redacts that turn and its dependent tail; continuing
that conversation requires a new chat. Legacy unverified answers are redacted.
Public chat remains stateless and rechecks a conservative corpus fingerprint.

Legacy file uploads now stage private revisions and preserve the live version.
Direct file-source publication edits and revision-managed deletion are blocked.
Raw ingestion stays unpublished and outside approved manifests. Deploy the
migration and backend together; the shared upload/review UI now consumes this contract.
This work has only used disposable PostgreSQL, with no configured project modified.

## Source and verification

- [Maintained SQL and generator instructions](../../../supabase/migration_sources/knowledge_revisions/README.md).
- [Generated migration](../../../supabase/migrations/20261028010000_knowledge_audience_revisions.sql).
- [PostgreSQL validation runner](../../../scripts/validation/knowledge_revisions/README.md).
- [Offline generator tests](../../../backend/tests/knowledge/test_revision_migration.py).

Validation covers migration rollback, data-preserving backfill, audience/manifest
constraints, tenant boundaries, lifecycle/provenance, frozen content, atomic
replacement, indexing failure, real database-role privileges and concurrent
review-token invalidation. The owner-only fixture helpers are never deployed.
Workflow evidence belongs in `logs/backend/knowledge-workflows/`; foundation
evidence is retained in `logs/backend/knowledge-revisions/`. The runner also
checks failed-index submission/retry, audit rollback, legacy resource ownership,
public snapshots and in-flight access changes. Backend and frontend regression
logs record the accompanying application checks.
