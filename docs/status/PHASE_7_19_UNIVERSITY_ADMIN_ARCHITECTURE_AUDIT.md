# Phase 7.19 — University Admin Architecture Audit

## Status

**INCOMPLETE**

The architecture and scope audit is complete, but Phase 7.19 cannot be marked complete because the production University Admin authorization chain does not satisfy institution isolation. The current `get_current_user` projection derives `institution_id` only from `students.institution_id`; University Admin grants are stored in `user_roles` with `scope_type='institution'` and `scope_id=<institution>`. An ordinary University Admin therefore resolves as tenantless in the legacy `/admin` dependency chain, where tenantless `admin` accounts are deliberately treated as unrestricted. Organization-scoped accounts with the ordinary `admin` role can reach the same shell and endpoints because `/admin` checks role membership but not scope type.

No product functionality, migration, remote data, role, or email change was made in this audit. The only change is this document.

## Scope Lock

- `public.institutions` remains the canonical institution/tenant entity.
- Super Admin remains the separate `super_admin` role with a fresh platform grant check.
- University Admin remains the ordinary `admin` role with an active `institution` scope.
- No competing tenant, RBAC, or authentication model should be introduced.
- The next implementation must first connect the existing scoped `user_roles` authorization context to every University Admin operation.
- Institution lifecycle and University Admin invitation/roster lifecycle stay in the Super Admin workspace.

## Existing Admin Architecture

### Frontend

The frontend is a React/Vite single-page application without React Router. `App.tsx` parses a small set of real URL paths and, after `/auth/me` bootstrap, selects a shell from the server-resolved primary role. `admin` selects `AdminShell`; `super_admin` selects the isolated `SuperAdminShell`. University Admin views are in-shell state tabs, not addressable browser routes.

`AdminShell` has one tested navigation model (`adminNavigation.ts`) and renders eleven views: dashboard, approvals, students, attendance, results, test results, notices, documents, FAQs, authenticated AI assistant, and profile. Requests use the shared bearer-token API clients and emit the common session-expired event on HTTP 401. Components generally have loading, empty, and error states, although direct component tests are uneven.

### Backend

`backend/app/api/admin.py` exposes 46 operations below `/api/v1/admin`. The endpoint layer applies `require_roles('admin')` to most operations and `require_roles('admin', 'staff')` to the approval queue. Services use the service-role Supabase client, so application-layer authorization is the security boundary. Mutations write `admin_audit_log` entries.

Knowledge uses `admin_knowledge` plus the existing upload/extract/chunk/embed pipeline. Academic CRUD uses `admin_academics`; attendance routes use the newer standalone `attendance` service. Dashboard aggregation uses `admin_dashboard`.

### Authorization chains found

Two authorization chains coexist:

1. Legacy tenant chain used by `/admin` and `/documents`: verified JWT → `get_current_user` → `get_user_by_auth_id` → role names plus `students.institution_id` → `require_roles` → `scope_tenant` / `assert_tenant_object`.
2. Scoped tenancy chain used by organization/institution approval workflows: verified JWT → `get_current_user` → `services.authorization.resolve_authorization_context` → `user_roles.scope_type/scope_id` → active-scope and resource checks.

The second chain correctly resolves institution-scoped admin grants. The first does not use it. This split is the central security defect and the most important duplication to consolidate.

Super Admin does not use either tenant shortcut. `/platform/*` uses `require_super_admin`, which verifies the primary `super_admin` role and freshly reads the active platform grant on every request.

## Existing Admin Routes

University Admin views are internal shell states reached after an authenticated `admin` enters `/`, `/login`, or `/login/admin`.

| Browser route / view | Component | Purpose | Primary API | Intended role/scope | Implementation status | Direct frontend tests | Known limitations |
|---|---|---|---|---|---|---|---|
| `/`, `/login`, `/login/admin` → `dashboard` | `AdminDashboard` | Counts and recent activity | `GET /admin/dashboard` | University Admin / own institution | BLOCKED | `AdminDashboard.test.tsx` | Four counts and audit feed are global; identity scope is not projected. |
| shell view `approvals` | `AdminApprovals` | Approve/reject pending students | pending/approve/reject endpoints | Admin or staff / own institution | BLOCKED | `AdminApprovals.test.tsx` | Backend logic is scoped only when `current_user.institution_id` is populated. |
| shell view `students` | `StudentManager` | List institution students | `GET /admin/students` | University Admin / own institution | BLOCKED | Shell/API/backend coverage only | UI is list-only; missing projected institution produces a neutral empty state. |
| shell view `attendance` | `AttendanceManager` | View attendance by typed student UUID | `GET /admin/students/{id}/attendance` | University Admin / own institution | BLOCKED | Shell/API/backend coverage only | UI exposes no create/edit/delete and requires raw UUID entry. |
| shell view `results` | `ResultsManager` | View results and upload CSV | result list and CSV upload | University Admin / own institution | BLOCKED | `ResultsManager.test.tsx` | UI exposes no row create/edit/delete; CSV is disabled when the broken identity projection returns no institution. |
| shell view `test-results` | `TestResultsManager` | View test results by typed student UUID | test-result list | University Admin / own institution | BLOCKED | Shell/API/backend coverage only | Read-only UI; raw UUID entry; mutation APIs not integrated. |
| shell view `notices` | `NoticeManager` | Notice CRUD and active toggle | notice CRUD | University Admin / own institution | BLOCKED | Shell/API/backend coverage only | Null-institution rows are mutable by any tenant admin; no dedicated component test. |
| shell view `documents` | `DocumentManager` | Sources, upload, version, processing, delete | knowledge/document APIs | University Admin / own institution | BLOCKED | Shell/API/backend coverage only | Source update exists only in client/backend; source lifecycle UI is incomplete. |
| shell view `faqs` | `FaqManager` | FAQ CRUD and active toggle | FAQ CRUD | University Admin / own institution | BLOCKED | `FaqManager.test.tsx` | Dedicated publish API is unused; null-institution rows are mutable by any tenant admin. |
| shell view `assistant` | shared `ChatShell` | Authenticated personal AI conversation | conversations and generation APIs | Any authenticated user / own conversation | COMPLETE | Shared chat tests | This is not institution support/conversation management. |
| shell view `profile` | `AdminProfile` | Safe identity display | AuthProvider `/auth/me` state | Admin / current identity | PARTIAL | `AdminShell.test.tsx` | Email/role only; no admin profile, institution, department, or contact record. |
| `/admin-invite/{token}` | `AdminInvitationPage` | Inspect and accept invitation | `/admin-invitations/*` | Public token flow | COMPLETE | `AdminInvitationPage.test.tsx` | Lifecycle ownership belongs to Super Admin, not University Admin. |
| `/super-admin` | `SuperAdminShell` | Platform workspace | `/platform/*` | active platform `super_admin` | COMPLETE | Super Admin component/client tests | Separate boundary; must not be merged into `AdminShell`. |

Route guards are UX gates only. `App.tsx` fails closed for unknown roles, keys shells by role and authenticated identity to clear cross-session state, and gives `super_admin` its own gate. Backend dependencies remain authoritative.

## Existing Admin APIs

All paths below have the `/api/v1` prefix. `A` means `require_roles('admin')`; `AS` means `require_roles('admin', 'staff')`. “Tenant guard” describes current code, not a claim that the production identity is correctly populated. Payload schemas are Pydantic models; UUID path/query parsing and service validation apply. Several list limits are plain integers without bounded query constraints.

| Method | Route | Service / repository | Role | Current scope/action | Frontend use | Tests / status |
|---|---|---|---|---|---|---|
| GET | `/admin/me` | endpoint projection | A | Identity only; no scope in response | Unused (AuthProvider uses `/auth/me`) | API tests; BLOCKED by scope projection |
| GET | `/admin/dashboard` | `admin_dashboard` / `admin_audit` | A | Requested institution passed through `scope_tenant`; mixed scoped/global aggregation | Dashboard | Service/UI/API tests; BLOCKED |
| POST | `/admin/knowledge-sources` | `admin_knowledge.create_knowledge_source` | A | Object tenant assertion; create | Documents | Repo/service/API tests; BLOCKED |
| GET | `/admin/knowledge-sources` | `admin_knowledge.list_knowledge_sources` | A | Institution query required and scoped | Documents | Repo/service/API tests; BLOCKED |
| GET | `/admin/knowledge-sources/{source_id}` | `admin_knowledge.get_knowledge_source_detail` | A | Fetch then object tenant assertion | Client has no function | API tests; BLOCKED |
| PATCH | `/admin/knowledge-sources/{source_id}` | `admin_knowledge.update_knowledge_source` | A | Fetch/assert then update | Client exists; UI unused | Repo/service/API tests; BLOCKED |
| GET | `/admin/knowledge-sources/{source_id}/documents` | `admin_knowledge.list_documents_for_source` | A | Source tenant assertion then list | Documents | Repo/service/API tests; BLOCKED |
| GET | `/admin/documents/{document_id}` | `admin_knowledge.get_document_with_versions` | A | Resolve source then assert tenant | Client/UI unused | API tests; BLOCKED |
| POST | `/admin/documents` | `admin_documents.upload_document` → ingestion pipeline | A | Source assertion; upload/process | Documents | Service/API tests; BLOCKED |
| POST | `/admin/documents/{document_id}/versions` | `admin_documents.update_document` | A | Resolve source, assert, version/process | Documents | Service/API tests; BLOCKED |
| DELETE | `/admin/documents/{document_id}` | `admin_documents.delete_document` | A | Resolve source, assert, purge/delete | Documents | Service/API tests; BLOCKED |
| GET | `/admin/faqs` | `admin_faq.list_faqs` / `admin_knowledge` | A | Institution derived by `scope_tenant`; filtered list | FAQs | Service/UI/API tests; BLOCKED |
| POST | `/admin/faqs` | `admin_faq.create_faq` | A | Payload institution replaced with effective tenant | FAQs | Service/UI/API tests; BLOCKED |
| GET | `/admin/faqs/{faq_id}` | `admin_faq.get_faq` | A | Fetch then object tenant assertion | Client/UI unused | API tests; BLOCKED |
| PATCH | `/admin/faqs/{faq_id}` | `admin_faq.update_faq` | A | Fetch/assert; update and RAG sync | FAQs | Service/UI/API tests; BLOCKED |
| POST | `/admin/faqs/{faq_id}/publish` | `admin_faq.publish_faq` | A | Fetch/assert; publish and RAG sync | Unused; UI patches `is_active` | Service/API tests; PARTIAL |
| DELETE | `/admin/faqs/{faq_id}` | `admin_faq.delete_faq` | A | Fetch/assert; delete and RAG cleanup | FAQs | Service/UI/API tests; BLOCKED |
| GET | `/admin/notices` | `admin_notices.list_notices` / `admin_knowledge` | A | Institution derived by `scope_tenant`; filtered list | Notices | Service/API tests; BLOCKED |
| POST | `/admin/notices` | `admin_notices.create_notice` | A | Payload institution replaced with effective tenant | Notices | Service/API tests; BLOCKED |
| GET | `/admin/notices/{notice_id}` | `admin_notices.get_notice` | A | Fetch then object tenant assertion | Client/UI unused | API tests; BLOCKED |
| PATCH | `/admin/notices/{notice_id}` | `admin_notices.update_notice` | A | Fetch/assert; update and RAG sync | Notices | Service/API tests; BLOCKED |
| DELETE | `/admin/notices/{notice_id}` | `admin_notices.delete_notice` | A | Fetch/assert; delete and RAG cleanup | Notices | Service/API tests; BLOCKED |
| GET | `/admin/students` | `admin_academics.list_students` / repo | A | Required institution scoped by `scope_tenant` | Students | Repo/service/API tests; BLOCKED |
| POST | `/admin/students` | `admin_academics.create_student` | A | Payload institution object assertion | Client exists; UI unused | Repo/service/API tests; BLOCKED |
| GET | `/admin/students/pending` | `admin_academics.list_pending_approvals` | AS | Tenant if present; tenantless admin is global | Approvals | Workflow/UI/API tests; BLOCKED |
| POST | `/admin/students/{student_id}/approve` | `admin_academics.approve_student` | AS | Conditional pending transition; tenant supplied if present | Approvals | Workflow/UI/API tests; BLOCKED |
| POST | `/admin/students/{student_id}/reject` | `admin_academics.reject_student` | AS | Conditional pending transition; tenant supplied if present | Approvals | Workflow/UI/API tests; BLOCKED |
| GET | `/admin/students/{student_id}` | `admin_academics.get_student` | A | Fetch then student institution assertion | Client/UI unused | API tests; BLOCKED |
| PATCH | `/admin/students/{student_id}` | `admin_academics.update_student` | A | Fetch/assert; update | Client exists; UI unused | Service/API tests; BLOCKED |
| DELETE | `/admin/students/{student_id}` | `admin_academics.archive_student` | A | Fetch/assert; soft archive | Client exists; UI unused | Service/API tests; BLOCKED |
| GET | `/admin/students/{student_id}/results` | `admin_academics.list_results_for_student` | A | Resolve student then tenant assertion | Results | Service/API/UI tests; BLOCKED |
| POST | `/admin/results` | `admin_academics.create_result` | A | Resolve payload student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| GET | `/admin/results/{result_id}` | `admin_academics.get_result` | A | Resolve result/student then assert | Client/UI unused | Service/API tests; BLOCKED |
| PATCH | `/admin/results/{result_id}` | `admin_academics.update_result` | A | Resolve result/student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| DELETE | `/admin/results/{result_id}` | `admin_academics.delete_result` | A | Resolve result/student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| POST | `/admin/results/csv-upload` | `admin_academics.upload_results_csv` | A | Multipart institution scoped by `scope_tenant`; per-row validation | Results | Service/API/UI tests; BLOCKED |
| GET | `/admin/students/{student_id}/test-results` | `admin_academics.list_test_results_for_student` | A | Resolve student then assert | Test Results | Service/API tests; BLOCKED |
| POST | `/admin/test-results` | `admin_academics.create_test_result` | A | Resolve payload student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| PATCH | `/admin/test-results/{test_result_id}` | `admin_academics.update_test_result` | A | Resolve result/student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| DELETE | `/admin/test-results/{test_result_id}` | `admin_academics.delete_test_result` | A | Resolve result/student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| GET | `/admin/students/{student_id}/attendance` | `attendance.list_attendance_for_student` / repo | A | Resolve student then assert | Attendance | Service/API tests; BLOCKED |
| POST | `/admin/attendance` | `attendance.create_attendance` | A | Resolve payload student then assert; academic validation | Client exists; UI unused | Service/API tests; BLOCKED |
| PATCH | `/admin/attendance/{attendance_id}` | `attendance.update_attendance` | A | Resolve attendance/student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| DELETE | `/admin/attendance/{attendance_id}` | `attendance.delete_attendance` | A | Resolve attendance/student then assert | Client exists; UI unused | Service/API tests; BLOCKED |
| GET | `/admin/audit-logs` | `admin_audit.list_audit_entries` | A | No institution filter or resource-scope guard | Client exists; no screen | Repo/API tests; BLOCKED |
| GET | `/admin/audit-logs/{audit_id}` | `admin_audit.get_audit_entry` | A | No institution/resource-scope guard | Unused | Repo/API tests; BLOCKED |

### Other role-accessible operational APIs

| Surface | Roles/dependency | Scope mechanism | Audit conclusion |
|---|---|---|---|
| `/documents/ingest`, `/{run}/extract`, `/{run}/chunk`, `/{run}/embed` | admin, staff, faculty | Knowledge-source tenant resolved through legacy `current_user.institution_id` | Same identity/scope split affects non-student staff/faculty grants; BLOCKED for production isolation. |
| `/admin/students/pending` and approve/reject | admin, staff | Legacy tenant plus special tenantless-admin global behavior | Functional and tested with injected contexts; production projection BLOCKED. |
| `/generation/chat`, `/conversations*` | any authenticated user | Conversation ownership and personalized context services | Existing personal assistant; not support administration. |
| `/students/me/*`, `/students/me/notifications*` | `get_current_user`, then student-profile/resource lookup | User/student/resource scoped in services | Student self-service; non-student closure is covered by integration tests. |
| `/organizations/{id}/decision`, `/institutions/join-requests/{id}/decision` | authenticated, then scoped authorization service | `user_roles.scope_type/scope_id`, organization/institution resource checks | Uses the stronger scoped chain; not University Admin operations. |
| `/platform/*` | `require_super_admin` | Fresh active platform grant | Correctly isolated from ordinary University Admin. |
| `/auth/login`, `/auth/student-login`, `/auth/me` | public login or authenticated identity | Supabase Auth plus application-user lookup | Canonical credential system, but ordinary non-student tenant lifecycle/scope is not enforced by general login/me. |

## Existing Admin Features

### A. Identity & Access

- Admin login: existing shared email/password login and `/login/admin`; PARTIAL because non-student admin tenant lifecycle is not checked.
- Admin invitation, token inspection/acceptance, email verification, resend/cancel/expiry: implemented and tested under the Super Admin lifecycle.
- Admin roster, assignment, revocation: implemented and tested in `SuperAdminShell`/`AdminRosterPanel`; intentionally not University Admin functionality.
- Admin role assignment: server-fixed institution `admin` role; no client-selected role and no `super_admin` assignment field.
- Admin profile: email and role only; no institutional profile entity.

### B. Student Management

- Student registration and pending approval workflow exist.
- Student list exists in the University Admin UI.
- Student create/update/archive APIs and client functions exist but have no UI integration.
- Student detail API exists but has no University Admin detail screen.
- Student status fields, authentication, own profile, results, attendance, notices, resources, and notifications exist.
- All University Admin access remains BLOCKED by the authorization-context defect.

### C. Academic Operations

- Attendance CRUD backend/client exists; University Admin UI is read-only by typed student UUID.
- Result CRUD and CSV import backend/client exist; UI is read-only plus CSV import.
- Test-result CRUD backend/client exists; UI is read-only.
- Academic years, semesters, programs, courses, and sections exist as schema/context data, but no University Admin management UI or dedicated CRUD API was found.

### D. Knowledge Management

- Knowledge-source create/list/get/update exists; UI lists/creates sources but does not expose source update/lifecycle management.
- Document upload, R2 storage, extraction, chunking, embedding, versioning, retrieval synchronization, and deletion exist.
- FAQ and notice canonical-text synchronization into knowledge exists.
- Public knowledge visibility is controlled by the existing public knowledge policy/lifecycle fields, not a dedicated University Admin configuration screen.

### E. Communication

- FAQ and notice CRUD UIs exist.
- Authenticated AI assistant and public institution AI routes exist.
- Conversation history is personal-user scoped.
- No University Admin support inbox, cross-user conversation viewer, ticket workflow, or support assignment surface exists.

### F. Institution Configuration

- Canonical name, code, branding, contact, status, and lifecycle data exist on `public.institutions`.
- Super Admin institution create/update/suspend/activate and branding/contact baseline UI/API exist.
- Public portal is represented by `/u/{code}` and `/u/{code}/ai`; no University Admin portal-settings UI exists.
- No University Admin AI-settings UI or institution configuration API was found.
- No production WhatsApp configuration was found.

### G. Monitoring / Dashboard

- Current dashboard renders eight raw counts and ten recent audit events.
- Staff and faculty counts are not implemented.
- Attendance rate, test/result summaries, knowledge processing health, AI usage, and support metrics are not implemented.
- The current dashboard cannot be approved for production University Admin use until every metric and audit row is institution-scoped.

## API ↔ Frontend Coverage

| Feature | Backend API | Frontend UI | Tests | Admin scope | Status |
|---|---|---|---|---|---|
| Login/session/role shell | `/auth/login`, `/auth/me` | Login + `AdminShell` | Backend auth; App/AuthProvider/Shell/navigation | Role resolved; institution scope not projected for admins | BLOCKED |
| Dashboard | `/admin/dashboard` | Eight cards + recent activity | Backend service/API + UI | Mixed institution/global | BLOCKED |
| Student approvals | pending/approve/reject | Full queue actions | Backend workflow/API + UI | Intended institution; production identity is tenantless | BLOCKED |
| Student roster | student CRUD | List only | Backend/client; no direct component test | Intended institution | PARTIAL |
| Attendance | attendance CRUD | Read only by UUID | Backend/client; no direct component test | Student-resource intended | PARTIAL |
| Results | result CRUD + CSV | Read + CSV only | Backend/client/UI | Student-resource intended | PARTIAL |
| Test results | test-result CRUD | Read only by UUID | Backend/client; no direct component test | Student-resource intended | PARTIAL |
| Knowledge sources | create/list/get/update | List/create/select | Backend/client; manager not directly tested | Intended institution | PARTIAL |
| Documents | list/get/upload/version/delete + pipeline | List/upload/version/delete | Backend/client; manager not directly tested | Source institution intended | PARTIAL |
| FAQs | full CRUD + publish | CRUD + active toggle | Backend/client/UI | Intended institution; global-row mutation hole | BLOCKED |
| Notices | CRUD | CRUD + active toggle | Backend/client; no direct component test | Intended institution; global-row mutation hole | BLOCKED |
| Authenticated AI | generation + conversations | Shared `ChatShell` | Existing chat suites | Current user/conversation | COMPLETE |
| Public AI / portal | institution lookup/public chat | `/u/{code}`, `/u/{code}/ai` | Public chat/landing suites | Public institution policy | COMPLETE |
| Support administration | None | None | None | Not defined | MISSING |
| Institution branding/settings | Super Admin `/platform/institutions*` only | Super Admin only | Backend/frontend Super Admin tests | Platform | MISSING for University Admin |
| University Admin roster/lifecycle | Super Admin `/platform/.../admins*` | Super Admin only | Backend/frontend lifecycle tests | Platform | COMPLETE at Super Admin boundary |
| Staff/faculty management | No dedicated CRUD | None | Role-shell tests only | Not defined | MISSING |
| Admin audit screen | `/admin/audit-logs*` | None; dashboard shows recent events | Repository/API only | Currently global | BLOCKED |

No legacy `/admin` endpoint should be called production-ready for a University Admin until the common scope defect is fixed. Functionality tests passing against mocked, pre-populated `current_user.institution_id` do not verify the real JWT-to-`user_roles.scope_id` chain.

## RBAC / Tenant Isolation

### Intended chain

JWT → `get_current_user` → `public.users` → active `user_roles`/`roles` → institution scope → role dependency → resource-level guard.

### Verified actual chain for `/admin`

JWT → `get_current_user` → `get_user_by_auth_id` → `public.users` + role names + optional `students.institution_id` → `require_roles` → legacy tenant helpers.

`get_user_by_auth_id` does not select `user_roles.scope_type`, `scope_id`, or `scope_organization_id`. University Admins created or invited by the platform are non-student users, so their `institution_id` becomes `None`. The legacy tenant helpers explicitly treat `None` as platform/unrestricted. This breaks cross-tenant isolation for students, documents, FAQs, notices, attendance, results, test results, approval operations, and ingestion when a caller supplies or discovers a foreign resource identifier.

The separate `services.authorization.resolve_authorization_context` correctly reads scoped role rows and is tested, but `/admin` does not use it. Active tenant checks in that service are likewise absent from the ordinary `/admin` dependency.

### Super Admin isolation

`super_admin` is a separate canonical role and is not included in `require_roles('admin')`. `/platform/*` performs a fresh database authorization read, requires an active account and active platform grant, and accepts no role/scope value from the client. University Admin tests confirm 403 responses at the platform boundary. Assignment/invitation payloads cannot select `super_admin`.

### Resource-level notes

- Result/test/attendance endpoints resolve the owning student before applying the legacy tenant assertion; the resource pattern is sound only if caller scope is sound.
- Document endpoints resolve the knowledge source before the same assertion.
- `assert_tenant_object` deliberately treats `institution_id=None` rows as global and visible. On FAQ/notice get/update/delete routes this also makes global rows mutable by institution admins, which is too broad for a write path.
- Admin audit list/detail and dashboard recent audit have no institution/resource filter.

## Super Admin Boundary

### Super Admin / platform scope

- Create, list, update, suspend, and activate institutions.
- Set platform baseline name/code/branding/contact fields.
- Assign existing University Admins.
- Invite, resend, cancel, expire, list, and revoke University Admin grants.
- Read platform audit events.
- Enforce platform authorization and account lifecycle.

### University Admin / one active institution

- Operate only its assigned institution.
- Manage its students and approval queue.
- Manage attendance, results, and test results.
- Manage knowledge sources, documents, FAQs, and notices.
- Use institution-level authenticated AI and, in future, configure institution-level public portal/AI settings.
- In future, manage staff/faculty and institution support workflows only where a specific authorization policy permits it.

University Admin must not create/suspend/activate institutions, assign or revoke University Admins, grant `super_admin`, edit platform audit data, or change platform-wide settings. `InstitutionManagement`, `AdminRosterPanel`, invitation lifecycle, and platform audit remain canonical Super Admin implementations and must not be copied into `AdminShell`.

## Proposed University Admin Navigation

This is a consolidation target, not an instruction to build missing pages in Phase 7.19.

- Dashboard — existing, blocked pending secure contract.
- Students
  - Student Approvals — existing.
  - Student Directory — existing list; integrate existing detail/CRUD later.
- Academic
  - Attendance — existing read UI; integrate existing mutations later.
  - Results — existing read/CSV UI; integrate existing mutations later.
  - Test Results — existing read UI; integrate existing mutations later.
- Knowledge
  - Documents — existing.
  - FAQs — existing.
- Communication
  - Notices — existing.
  - AI Assistant — existing personal authenticated AI.
  - Support — future; do not label the personal conversation UI as support management.
- Institution
  - Public Portal — future University Admin settings, bounded so platform baseline/lifecycle remains Super Admin.
  - AI Settings — future.
  - Profile / Institution Settings — future; current profile is identity-only.
- Administration
  - Staff — future.
  - Faculty — future.

“University Admins” is intentionally absent: the existing canonical roster/invitation/revocation surface belongs to Super Admin. Institution create/suspend/activate is also absent.

## Dashboard Data Contract

### Currently rendered

| Metric | Existing data source | Current query | Contract decision |
|---|---|---|---|
| Knowledge source count | `knowledge_sources` | `institution_id` when supplied | AVAILABLE AT DATA LAYER; blocked by identity projection. |
| Document count | `documents` | Global count | PARTIALLY AVAILABLE; must derive tenant through knowledge source/document version relationship. |
| FAQ count | `faqs` | `institution_id`, `is_active=true` when supplied | AVAILABLE AT DATA LAYER; label should clarify active FAQs. |
| Notice count | `notices` | `institution_id`, `is_active=true` when supplied | AVAILABLE AT DATA LAYER; label should clarify active notices. |
| Student count | `students` | `institution_id` when supplied | AVAILABLE AT DATA LAYER. |
| Student result count | `student_results` | Global count | PARTIALLY AVAILABLE; must join/resolve through student. |
| Test result count | `test_results` | Global count | PARTIALLY AVAILABLE; must join/resolve through student. |
| Attendance record count | `student_attendance` | Global count | PARTIALLY AVAILABLE; must join/resolve through student. |
| Recent activity | `admin_audit_log` | Latest ten globally | BLOCKED; audit rows lack a reliable direct institution filter. |

### Available now after authorization/scoping remediation, without new analytics

- Total students from `students`.
- Total knowledge sources from `knowledge_sources`.
- Active FAQ count from `faqs`.
- Active notice count from `notices`.

These four already have direct institution columns. They are not safe in the present request chain but need no new analytics infrastructure.

### Partially available

- Documents, results, test results, and attendance record counts: tables exist, but dashboard queries are global and require relational institution scoping.
- Recent activity: audit data exists, but the current audit schema/query cannot safely produce an institution feed for every event.

### Not implemented

- Staff count, faculty count.
- Attendance percentage/rate.
- Test performance, pass/fail, grade, or trend summaries.
- Knowledge extraction/chunk/embed health summary.
- AI request/token/cost/quality analytics.
- Support/conversation operational metrics.
- Academic year, semester, course, section, or class summaries.

No unsupported metric should appear in the next dashboard.

## Duplications

| Area | Implementations found | Canonical direction |
|---|---|---|
| Tenant/role resolution | `core.security` legacy student-profile tenant helpers vs `services.authorization` scoped `user_roles` context | Consolidate University Admin authorization on the existing scoped context and active-tenant checks; do not create a third model. |
| Attendance domain | Attendance functions in `admin_academics`, standalone `services.attendance`/`repositories.attendance`, plus student-facing attendance service | Admin API already uses standalone `attendance`; retain it as admin mutation path and plan deliberate consolidation with student read models. |
| Results/test results | Legacy admin academic repository/service and newer `results` repository/student result services | Do not delete during audit. Define one shared persistence/validation layer in a later focused phase after authorization repair. |
| Identity endpoint | `/auth/me` is canonical frontend bootstrap; `/admin/me` duplicates a subset | Keep `/auth/me` canonical; consider deprecating `/admin/me` only after usage confirmation. |
| FAQ publication | Dedicated `POST /faqs/{id}/publish` and generic PATCH `is_active`; UI uses PATCH | Choose one lifecycle contract in a later integration cleanup; backend canonical-text synchronization currently supports both. |
| Notice publication | Service has `publish_notice`/`unpublish_notice`; API/UI use PATCH `is_active` | Expose one lifecycle contract or remove dead service helpers only after tests/usage audit. |
| Institution management | Public organization/institution registration workflow and Super Admin platform institution lifecycle | Not duplicates: onboarding approval and platform lifecycle are different boundaries. Super Admin `InstitutionManagement` is canonical for platform lifecycle. |
| Document handling | `/admin/documents` orchestration and `/documents/*` processing pipeline | Not duplicates: the admin workflow composes the processing pipeline. Keep the pipeline shared. |
| Authentication | General email login and student identifier login | Intentional alternate identifiers over the same Supabase Auth authority; do not replace with a new auth system. |

No code was deleted. The duplicated `user_tenant_id` function definition inside `core/security.py` is demonstrably redundant source text but was left untouched because this phase is audit-only and the larger authorization consolidation must be reviewed as one change.

## Missing Capabilities

- Correct University Admin institution-scope projection and enforcement.
- Active institution/account enforcement on ordinary Admin login and every Admin request.
- Institution-scoped audit ledger and safe recent activity feed.
- Secure relational dashboard counts for documents and academic records.
- Integrated student detail/create/edit/archive UI.
- Integrated attendance/result/test-result mutation UI and roster-based selection instead of raw UUID entry.
- Academic year, semester, program/course/section management UI/API.
- University Admin institution/public-portal/AI settings contract.
- Staff and faculty roster/lifecycle management contract and UI.
- Support inbox/ticket/conversation administration.
- Direct component tests for Students, Attendance, Test Results, Notices, and Documents.

## Security Findings

### SEC-7.19-01 — Critical — scoped Admin grants collapse to unrestricted legacy admins

`get_user_by_auth_id` selects role names and `students(institution_id)` only. Platform-created/invited University Admins have their institution in `user_roles.scope_id`, not a student profile. `current_user.institution_id` is therefore `None`, and `scope_tenant`, `assert_tenant_object`, `_approval_scope`, and document guards treat the account as platform-level/unrestricted. Organization-scoped ordinary admins are affected as well because `/admin` checks the role name but not `scope_type`.

Impact: cross-institution read/write access is possible across the legacy Admin API when foreign IDs or institution filters are supplied. The same account may also bypass institution suspension because general sign-in lifecycle checks only follow a student profile.

Disposition: not patched in this audit because a safe fix spans identity projection, dependency policy, lifecycle enforcement, dashboard/audit scoping, staff/faculty ingestion, and regression tests. This is the mandatory next phase and a release blocker.

### SEC-7.19-02 — High — dashboard and Admin audit are globally scoped

Documents, results, test results, attendance counts, recent dashboard audit events, and both `/admin/audit-logs` endpoints are global even when a correct institution id is supplied. They can disclose other institutions' volume and administrative activity.

Disposition: mandatory part of the next remediation. Remove unsafe cards/feed until a reliable scoped query exists; do not manufacture analytics.

### SEC-7.19-03 — High — global FAQ/notice rows are writable by tenant admins

`assert_tenant_object` treats `institution_id=None` as globally visible. The same helper guards update/delete routes, so visibility becomes mutation authority for global FAQ/notice rows.

Disposition: split read visibility from write ownership in the next remediation. Global content mutation, if needed, belongs to an explicitly authorized platform policy.

### Tests and evidence

- Focused Admin/RBAC/tenant/Super Admin backend run: **473 passed**, 4 warnings.
- The focused tests construct `current_user` contexts directly or mock `get_user_by_auth_id`; they do not connect an actual institution-scoped `user_roles` grant through `get_current_user` into `/admin`.
- Complete `backend/tests` production-like run (`DEBUG=false`): **2,424 passed, 2 failed, 27 skipped**, 6 warnings. The two failures assert development diagnostics that are intentionally absent with `DEBUG=false`.
- Required `DEBUG=true` rerun of those exact diagnostics tests: **2 passed**.
- A bare repository-wide `pytest` was also attempted: collection stopped with **6 errors** because scripts under `scripts/manual_tests` and `scripts/validation` made localhost HTTP calls while no manual validation server was running. No remote target was used.
- Frontend first full run: **51 files / 398 tests passed**, with 7 worker-start timeout errors before those files executed.
- Serialized rerun of the 7 affected files: **7 files / 112 tests passed**. Combined coverage: **58 files / 510 tests passed**.
- Focused Admin frontend run: **8 files / 56 tests passed**.
- TypeScript `tsc -b`: passed.
- Production frontend build: passed; 112 modules transformed.

Passing existing tests does not negate the static end-to-end authorization finding; the missing integration case is itself a test gap.

## Follow-up Phases

### Phase 7.20 — University Admin Authorization Context & Tenant Isolation Remediation (next, mandatory)

This is the single next implementation phase.

1. Reuse the existing scoped `user_roles` authorization context for University Admin, staff, and faculty.
2. Add one reviewed dependency requiring active account + active institution scope + allowed role for `/admin` and institution document operations.
3. Exclude organization-scoped ordinary admins and legacy platform admins from University Admin operations unless a separately documented policy explicitly permits them.
4. Make every object/list/mutation institution-scoped, including null/global content write rules.
5. Replace or suppress unsafe dashboard counts and recent audit; add reliable relational tenant filters where possible.
6. Add integration tests that start with realistic `users` + `user_roles.scope_*` projections and prove cross-tenant denial, suspended-tenant denial, Super Admin separation, and no role escalation.
7. Keep `require_super_admin` and the canonical `public.institutions` model unchanged.

### Later, only after Phase 7.20

- Dashboard/UI integration of the four safe direct counts, then relational counts.
- Existing academic/student mutation API integration into the UI.
- Institution-level settings/public portal/AI configuration contract.
- Staff/faculty lifecycle and support workflow phases.
- Deliberate academic repository consolidation.

## Verification and Artifact Hygiene

- Remote Supabase changed: **NO**.
- Production email sent: **NO**.
- Migrations pushed: **NO**.
- Production users/roles/data changed: **NO**.
- No server was started and no manual validation target was contacted successfully.
- Frontend output was generated only by the local production build and is ignored build output.
- No tracked product file was modified.

## Completion Criteria Result

The route/API/UI inventory, coverage matrix, navigation proposal, dashboard contract, duplication audit, Super Admin boundary, missing-capability list, security findings, and test record are complete. Phase status remains **INCOMPLETE** because University Admin tenant isolation, object-level access, and dashboard/audit scope verification failed. Marking the phase complete would incorrectly certify a security property the current production chain does not provide.
