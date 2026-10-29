# Knowledge audience and revision workflow

Schema implementation for the [audience-based upload design](../../../docs/architecture/ai-chatbot/AUDIENCE_UPLOAD.md).
Generated migration: `20261028010000_knowledge_audience_revisions.sql`.

Generate or check the artifact without contacting a database:

```powershell
python scripts/maintenance/migrations/build_knowledge_revisions.py
python scripts/maintenance/migrations/build_knowledge_revisions.py --check
```

## Model and invariants

- `knowledge_source_revisions` snapshots metadata, requested visibility, review
  provenance, lifecycle and a monotonic revision concurrency token.
- `knowledge_source_revision_audiences` lists explicit student/staff/faculty/admin
  targets. Targets combine with OR; Public/authenticated revisions have no targets.
- `knowledge_source_revision_documents` pins one exact version per document.
  Composite FKs prevent source/document/version or institution mismatches.
- `knowledge_sources.published_revision_id` pins the single live revision;
  `policy_version` advances when live policy changes. Metadata and visibility
  must match that revision at transaction completion.
- New revisions start in draft. Submission requires a valid audience and an indexed
  file manifest. Review freezes content and members; returning to draft clears approval.
- Published history cannot be edited/deleted. Reviewed file content cannot be
  rewritten. Replacement versions and audience changes stage a new revision;
  live pointer/manifest changes must commit atomically after indexing.

Deferred constraint triggers allow an atomic publication/supersession transaction
while rejecting inconsistent final state. Parent row locks serialize audience,
manifest and file edits against review and advance the same revision token.
Processing runs, chunks and embeddings also freeze when their manifest enters
review, including writes through legacy processing endpoints.

## Backfill and rollout boundary

Only already-published, effective noncanonical Public/authenticated sources with published,
effective versions and ready/embedded/completed processing receive legacy
snapshots. The newest eligible version per document is retained. Existing source
metadata, file rows, visibility and permissions are unchanged. Empty/expired/
future/unindexed/restricted sources receive no revision pointer or inferred roles.
Legacy snapshots are labeled; no historical admin approval is fabricated.

New tables enable RLS, deny browser access, and grant the service role SELECT
only. `workflow/` exposes service-only draft/upload/review RPCs that recheck active
identity, exact institution grants, ownership, concurrency tokens and atomic audit
events. Admins alone approve/publish/unpublish; faculty/staff submit their drafts.
`readers/` filters library metadata and vector candidates before ranking/limits,
and snapshots/revalidates provenance for generated answers and restored history.

Canonical FAQ/notice sources retain their existing explicitly public workflow
and are excluded from backfill and file-upload types. Legacy admin file uploads
stage revisions; live file source PATCH and revision-managed deletion are blocked.
Raw ingestion creates unpublished versions outside the live manifest.

Deploy the migration and integrated backend together. The shared uploader and
review UI now consume these APIs. Preparation and disposable verification
do not apply this migration to a configured or hosted project. See the
[implemented API contract](../../../docs/architecture/ai-chatbot/API.md).

See [database validation](../../../scripts/validation/knowledge_revisions/README.md).
