# Shared learning resources and AI chatbot

Design draft, 28 October 2026. Based on the current working tree; this is a
proposed implementation plan, not a record of completed screens or deployed APIs.

## Product requirement

Admin, faculty and staff use **one Learning Resources component** and the same
interaction patterns. The title, search, filters, resource rows, details, status
labels and feedback are consistent. Server-authorized capabilities determine
which records and actions each person can use.

The AI Assistant uses the existing shared chat components. Learning Resources
supplies its authorized knowledge; the assistant returns answers with traceable
sources. Processing, publication and audience access are separate decisions.

## Review the design

| Document                                                | Responsibility                                                            |
| ------------------------------------------------------- | ------------------------------------------------------------------------- |
| [UI and UX](UI_UX.md)                                   | Shared screen, component ownership, interactions and states               |
| [Application architecture](APPLICATION_ARCHITECTURE.md) | Existing foundations, proposed contracts, permissions and data boundaries |
| [Workflows and delivery](WORKFLOWS.md)                  | Resource ingestion, chat decisions, rollout and acceptance checks         |

## Current implementation and gaps

| Area                | What exists today                                                                                           | Design implication                                                                     |
| ------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Admin resources     | Documents/knowledge-source manager and separate FAQ editor                                                  | Reuse their domain logic behind the shared resource workspace.                         |
| Faculty resources   | Learning Resources navigation opens a placeholder                                                           | Replace it only when the shared authorized API is available.                           |
| Staff resources     | No Learning Resources navigation                                                                            | Add the same workspace behind resolved read capabilities.                              |
| Student resources   | Published source metadata; no file-open/download contract                                                   | Preserve this API and its FAQ/notice exclusions during the first rollout.              |
| Authenticated chat  | Admin, faculty, staff and student mount `ChatShell`                                                         | Extend the shared implementation; avoid role-specific chat copies.                     |
| Institution context | Backend checks the requested institution against active scope; `useChat` sends `DEMO_INSTITUTION_ID`        | Use the authenticated institution and preserve the server check.                       |
| Resource management | Admin CRUD routes are admin-only; ingestion routes permit admin/staff/faculty with a knowledge-create grant | Shared UI needs a supported shared read/write facade, not broader admin-router access. |
| Pipeline feedback   | Document UI uses a delayed refresh; backend has processing and embedding state                              | Render server state; elapsed time never establishes readiness.                         |

## First implementation slice

1. Establish a tenant-scoped resource read contract for the three roles.
2. Build one Learning Resources page and detail view with real loading, empty,
   error and access states. Mount it in each permitted role workspace.
3. Move supported resource actions into shared hooks and focused controls,
   preserving existing grants and canonical FAQ/document data.
4. Correct chat institution context and define source eligibility consistently.
5. Add resource-scoped questions after the server accepts and authorizes that
   context. Keep ordinary institution-wide chat working throughout migration.

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
