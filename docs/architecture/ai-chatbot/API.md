# Learning resource API

Implemented backend contract, 28 October 2026. All paths below start with
`/api/v1/knowledge`. The prepared migration and backend must ship together.
The shared frontend library/uploader/review workspace is now connected to this
contract. A live environment still requires migration/backend deployment together.

## Requests and scope

Bearer authentication supplies the actor and institution. Clients cannot set
institution, uploader, approval, visibility columns or publication state directly.
Active institution grants and operation permissions are rechecked in PostgreSQL.
Faculty/staff access their own drafts; institution admins can review all revisions.

```json
{
  "title": "Library guide",
  "source_type": "handbook",
  "audience": { "mode": "roles", "roles": ["student", "faculty"] }
}
```

Audience modes are `public`, `institution` and `roles`. Only `roles` accepts
targets: `student`, `staff`, `faculty` and `admin`. The UI label Teacher maps to
`faculty`. Selected targets combine with OR. An incomplete restricted draft may
have no targets; submission requires a valid audience and indexed files.
Omitting audience on creation saves an incomplete private draft. `faq` and
`notice` are reserved for their existing canonical editors.

## Endpoints

| Method and path                                  | Behavior                                                                                  |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `GET /resources?limit=20&offset=0`               | Audience-filtered published library; `documents.read`.                                    |
| `GET /resources/{source}`                        | Safe resource metadata/files; inaccessible and missing both return 404.                   |
| `POST /resources`                                | Create an owned draft; `ai.knowledge.create`.                                             |
| `POST /resources/{source}/revisions`             | Clone live metadata/audience/manifest into a new draft; owner or admin with update grant. |
| `PATCH /resources/{source}/revisions/{revision}` | Edit a draft using `expected_version`; never change live policy.                          |
| `GET /revisions?view=own`                        | Paginated owned revisions, including review feedback.                                     |
| `GET /revisions?view=review`                     | Admin review list; exact admin scope and `ai.knowledge.read`.                             |
| `GET /revisions/{revision}`                      | Own revision or explicit admin review access.                                             |
| `POST /revisions/{revision}/documents`           | Multipart file plus `expected_version`; optional `document_id` stages a replacement.      |
| `POST /revisions/{revision}/retry-index`         | JSON `expected_version` and `document_version_id`; retry failed draft indexing.           |
| `POST /revisions/{revision}/{action}`            | `submit`, `request_changes`, `approve`, `publish` or `unpublish`.                         |

Library/revision list responses contain `items` and `total`. Limits are 1–100;
offsets are 0–100000. Safe file summaries include IDs, name, type, size, version
and indexing state. New responses expose no storage keys, buckets or signed URLs.
This contract does not implement file delivery or document removal.

## Editing, upload and review

After every successful write, use the returned `revision_version` for the next
request. Audience, manifest and indexing changes advance it. Review actions
accept `{ "expected_version": 4, "notes": "Reviewed" }`; publish/unpublish also
require the latest returned `policy_version` as `expected_policy`.

```text
draft -> under_review -> approved -> published -> archived / superseded
             |              |
             +---- request_changes -> draft
```

Submission freezes the indexed manifest and audience. Request-changes requires
feedback and clears approval. Admin approval, publication, audience changes and
unpublication require `ai.knowledge.update`; staff/faculty cannot publish.
Published revisions are immutable; edits require a new draft and review.

Uploads require knowledge-create plus document-create, or document-update for a
replacement. They use the existing synchronous extraction/chunk/embedding
pipeline while leaving the file unpublished. A failed index returns 422 and
retains the draft/file for retry. Queued, running, successful or reviewed versions
cannot be indexed again through retry. Until publication commits, the old live
manifest remains available. Publication switches the exact approved manifest and
source policy atomically, without purging old content before approval.

Conflict responses return 409; reload the revision/policy before retrying.
Invalid audience, review state or indexing readiness returns 422. Revoked grants
return 403 and a missing schema returns 503. Unknown registration outcomes retain
uploaded objects because the transaction may have committed.

## Chat and compatibility

The chat request now accepts optional `resource_id` for immutable resource-scoped
conversations. The eligibility endpoint, response/history context, rejection and
revocation contracts are documented in [Resource-specific Ask AI](RESOURCE_CHAT.md).

Signed-in requests also accept `turn_id` with a stable session/conversation ID.
`GET /generation/turns/{turn_id}` checks status without resending work. The
[durable turn contract](CHAT_RECOVERY.md) defines replay, explicit retry,
unfinished history and atomic answer/retrieval/citation persistence.

`GET /conversations/{conversation_id}/messages` returns `sources` on each message,
using the same structured cards as live replies. User/uncited messages return an
empty list. Restored cards require current access and citation-to-answer retrieval
provenance; they expose no storage locations or provider diagnostics. Changed
policy redacts the affected answer and dependent tail. Apply the history-citation
migration before the matching API. Missing/failed source reads return a safe 503.

Authenticated chat uses the actor's institution and checks audience, manifest,
dates and ready/embedded provenance before vector ranking. It rechecks source
policy and scope before delivery. Restored history redacts an invalid assistant
answer and stops its dependent tail; follow-up chat returns 409 and asks for a
new conversation. Old answers without verified provenance are also redacted.
Public chat uses public sources only and rechecks the public corpus before delivery.

Existing admin upload URLs now stage drafts. Direct file-source PATCH and
revision-managed file deletion cannot bypass review. Raw ingestion creates
unpublished versions outside the live manifest. Canonical FAQ/notice editors
retain their existing workflow, while student resource responses retain their
metadata-only shape and canonical-type exclusions with audience filtering.
