# Shared learning resources and AI chatbot

Design and staged implementation, 28 October 2026. The
[database model](DATABASE_MODEL.md), authorized draft/review writers and
reader/chat enforcement are implemented with a prepared migration. Shared
library/upload/review screens now mount in all three workspaces. No project
database was modified; live use requires migration/backend deployment together.
Resource-specific [Ask AI](RESOURCE_CHAT.md), follow-ups and restored history are
implemented with a second prepared additive migration dated 29 October 2026.

## Product requirement

Admin, faculty and staff use **one Learning Resources component** and the same
interaction patterns. The title, search, filters, resource rows, details, status
labels and feedback are consistent. Server-authorized capabilities determine
which records and actions each person can use.

The AI Assistant uses the existing shared chat components. Learning Resources
supplies its authorized knowledge; the assistant returns answers with traceable
sources. Processing, publication and audience access are separate decisions.

Uploads support **Public**, **All signed-in institution members** and **Selected
roles** (students, staff, faculty/teachers, admins or combinations). Admins publish
and change the live audience; faculty/staff submit drafts for review. See the
[audience-based upload plan](AUDIENCE_UPLOAD.md) for the confirmed workflow.

## Review the design

| Document                                                | Responsibility                                                                               |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [UI and UX](UI_UX.md)                                   | Shared screen, component ownership, interactions and states                                  |
| [Application architecture](APPLICATION_ARCHITECTURE.md) | Existing foundations, proposed contracts, permissions and data boundaries                    |
| [Workflows and delivery](WORKFLOWS.md)                  | Resource ingestion, chat decisions, rollout and acceptance checks                            |
| [Audience-based uploads](AUDIENCE_UPLOAD.md)            | Audience matrix, shared form, admin review, revision model and rollout                       |
| [Database model](DATABASE_MODEL.md)                     | Implemented schema, constraints, conservative backfill, verification and deployment boundary |
| [Implemented API](API.md)                               | Draft/upload/review endpoints, permission and concurrency contracts, chat compatibility      |

## Current implementation and gaps

| Area                | What exists today                                                                                           | Design implication                                                                     |
| ------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Admin resources     | Shared Learning Resources page, own submissions and explicit admin review; separate canonical FAQ editor    | Use the shared API and preserve existing canonical editing.                            |
| Faculty resources   | `/faculty/resources` mounts the shared library/upload/submission workspace                                  | Faculty submit drafts for admin review.                                                |
| Staff resources     | Learning Resources navigation mounts the same workspace behind resolved grants                              | Same components and actions for equal capabilities.                                    |
| Student resources   | Published metadata with audience filtering and existing exclusions                                          | Retain the student metadata-only page; file delivery needs a separate contract.        |
| Authenticated chat  | Admin, faculty, staff and student mount `ChatShell`                                                         | Extend the shared implementation; avoid role-specific chat copies.                     |
| Institution context | `useChat` sends the authenticated institution; backend rechecks active scope                                | Preserve identity boundaries when adding resource context.                             |
| Resource management | Admin CRUD routes are admin-only; ingestion routes permit admin/staff/faculty with a knowledge-create grant | Shared UI needs a supported shared read/write facade, not broader admin-router access. |
| Pipeline feedback   | Document UI uses a delayed refresh; backend has processing and embedding state                              | Render server state; elapsed time never establishes readiness.                         |
| Audience/review     | Guarded manifests, connected shared UI/APIs, admin-only publication and reader/chat policy are implemented  | Deploy the migration/backend together and verify the target environment.               |

## First implementation slice

1. Establish audience/revision storage, admin-only publication and a tenant-scoped
   resource read contract. Close publication bypasses and enforce audiences in
   existing reader/retrieval paths before enabling restricted publication.
2. Build one Learning Resources page and detail view with real loading, empty,
   error and access states. Mount it in each permitted role workspace.
3. Build shared upload/draft controls and admin review using exact permissions,
   preserving canonical FAQ/document data and independent indexing state.
4. Correct chat institution context and define source eligibility consistently.
5. Resource-scoped questions now persist authorized context on the conversation.
   Ordinary institution-wide chat remains available; see [Ask AI](RESOURCE_CHAT.md).
6. Signed-in chat uses [durable turns and explicit recovery](CHAT_RECOVERY.md)
   for lost responses, failed work and atomic citation persistence.

The first slice uses institution resources. Course assignments, subject packages,
attendance, results and personal student records stay outside this design's data
model; the existing retirement boundaries still apply.

## Source references

- [Design system](../../../frontend/docs/DESIGN_SYSTEM.md) and
  [server-state guide](../../../frontend/docs/SERVER_STATE.md).
- [Admin document UI](../../../frontend/src/features/admin/documents/DocumentManager.tsx)
  and [document state](../../../frontend/src/features/admin/documents/useDocumentManager.ts).
- [Faculty workspace](../../../frontend/src/features/faculty/workspace/FacultyShell.tsx)
  and [staff workspace](../../../frontend/src/features/staff/StaffShell.tsx).
- [Shared chat](../../../frontend/src/features/chat/ChatShell.tsx),
  [chat state](../../../frontend/src/hooks/useChat.ts) and
  [authenticated/public boundary](../../../backend/app/main.py).
- [Admin route authorization](../../../backend/app/api/admin/dependencies.py),
  [ingestion API](../../../backend/app/api/knowledge/ingestion.py) and
  [student resource contract](../../../backend/app/schemas/students/student_resources.py).

Role defaults in source are reference policy. Effective permissions and active
institution scope remain server-authoritative; this draft changes no grants.
