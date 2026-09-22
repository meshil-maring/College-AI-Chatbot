# Phase 6.20 - Cross-Role Integration and Authorization Boundary Validation

Status: verified. Scope: only the files under Git scope. No commit created.

## Phase identity

Phase 6.20 follows Phase 6.19 (Admin Experience and Administrative Workspace
Foundation). This is an implementation and integration validation phase.
## Objective

Validate student, faculty, staff, and admin separation after Phases
6.16-6.19: server-authoritative role resolution, shell selection, backend
authorization, tenant isolation, session lifecycle, navigation, data
exposure, client-controlled identity parameters, cross-role API access,
and multi-tab behavior. No new capability is invented here.

## Scope

In scope: role-to-shell mapping, navigation isolation, authorization
matrix, staff approval exception, tenant isolation, mutation safety,
client-controlled parameters, session lifecycle, transitions, stale
view state, leakage, storage, API client, boundaries, chat, a11y,
integration tests, regression, docs, git scope. Out of scope: new roles,
models, RAG, ChatShell, Phase 6.21.
## Architecture baseline

Unchanged chain: JWT to get_current_user to public.users to user_roles to
roles to resolve_primary_role() to /auth/me to AuthProvider to shell.
Precedence admin over staff over faculty over student is unchanged
(backend/app/core/security.py). auth_user_id is the JWT sub; user_id is
the users-table key (backend/app/api/auth.py). ChatShell is reused
verbatim in each authorized shell; chat auth is the existing
get_current_user plus scope_tenant contract. Session flow is the single
existing requestJson to 401 to notifySessionExpired to AuthProvider flow.
## Role-to-shell matrix

Verified: admin to AdminShell, staff to StaffShell, faculty to
FacultyShell, student to StudentShell, null and unknown to the neutral
unsupported state (frontend/src/App.tsx). All transitions covered by
frontend/src/CrossRoleIntegration.test.tsx. Fixed: shells are keyed on
role plus server-issued auth_user_id so React remounts on session
replacement instead of reconciling stale state in place.

## Role navigation isolation

Verified. Student exposes only verified student surfaces; faculty only
dashboard, assistant, and profile; staff only dashboard, approvals,
assistant, and profile including the Phase 6.4 approval exception;
admin only its 11 verified items. Every navigation builder returns an
empty list for foreign, null, and unknown roles (fail closed), covered
by the existing unit suites plus the new integration mapping tests.

## API authorization matrix

Verified from backend contracts as source of truth
(backend/tests/test_cross_role_integration_phase_6_20.py).
/students/me/* serves students and returns 404 for faculty, staff,
admin, and unsupported. Pending and approve/reject allow admin and
staff only. All other /admin/* surfaces are admin-only. Chat remains
per existing contract for every authenticated role. Student, faculty,
and staff denial is asserted per surface; admin read paths asserted
open. Approval queue is the single explicit exception.

## Staff approval exception

Verified intact and not expanded. Student and faculty are denied 403 on
pending, approve, and reject. Staff and admin work inside their own
tenant with tenant-scoped handlers. Tenantless staff and faculty are
denied. Stale decisions return the documented 409
STUDENT_NOT_PENDING with no write and no audit. Staff reaches no other
/admin/* surface.
## Tenant isolation

Verified for Institution A versus Institution B across all four roles.
Admin A reads for B student, attendance, result, test-result, notice,
FAQ, knowledge-source, and document data return 403 TENANT_MISMATCH.
Staff A cannot list or approve B students. Student and faculty A reads
for B records receive the correct denial. Tenantless privileged users
fail safely with 403. Same-role cross-tenant sessions are also covered
by the frontend transition tests.

## Cross-tenant mutation safety

Verified with write-nothing proofs: each foreign-tenant mutation returns
403 TENANT_MISMATCH while the write service, audit, and database client
are asserted never called. Covers student create, update, and archive;
attendance; results; test results; notices; FAQs; knowledge sources;
document reads, uploads, and deletes; and the approval handlers used
from their authorized tenants.

## Client-controlled tenant parameters

Verified server-derived authorization only. Supplied role,
institution_id, tenant_id, and user_id values cannot change the
resolved role or tenant. A create carrying a foreign institution_id is
denied before any write. Student identity comes from the server-side
student context, never from a client student_id. Dangerous overrides
are denied; ordinary allowed filters remain filters.

## Session lifecycle

Verified with one shared mechanism for all roles. Login enters the
role shell. Refresh revalidates the saved token through /auth/me into
the same shell exactly once. A 401 uses the existing requestJson to
notifySessionExpired to AuthProvider flow; a 401 naming a replaced
token cannot clear the current session. Logout removes auth state and
the stored token. Multi-tab storage events clear this tab on sign-out
and adopt the new role after /auth/me validation. No role-specific
session system was introduced.
## Role transition safety

Verified across admin, staff, faculty, and student permutations,
including same-role different-account and different-tenant changes.
Switching never inherits the previous shell, navigation, cached data,
API responses, or view state. Identity-keyed shell remounts plus the
backend tenant guards make admin A to admin B and admin to student
safe in both directions. No previous role UI state survives.

## Stale view state

Verified fixed. In-shell useState view names could persist when React
reused an element across an authentication replacement, for example an
open Documents manager. Keying each shell on the canonical identity
forces a fresh mount per identity; tests assert admin Documents falls
back to the student dashboard and staff approvals never appear inside
a student shell. Ordinary navigation behavior is unchanged.

## Cross-role data leakage

Verified absent. After transitions the DOM contains no previous role
headings, counts, queues, or management state for any role pair.
Backend tests confirm denial payloads carry only the denial, never
admin data. Tenant-B principal adoption is covered as well.

## Browser storage audit

Verified safe. localStorage holds exactly one key, the documented
access-token key, during every role session. sessionStorage stays
empty. Logout empties localStorage. The token never renders in the DOM.
No passwords, secrets, authorization decisions, or datasets are stored.
No extra token copies were introduced.
## API client isolation

Verified. The shared client attaches the current token, raises the one
401 expiry broadcast, does not retain role-filtered responses between
sessions, and never retries mutations. Backend tests prove denied
mutations never reach a handler body. No per-role clients were created
and none were required.

## Admin-to-Staff boundary

Verified. A staff session on the same browser, institution, device,
build, and client receives only staff navigation and staff-authorized
endpoints. Every other /admin/* surface answers 403 FORBIDDEN without
touching service or database layers. Role identity comes from the
authenticated backend context only.

## Staff-to-Faculty boundary

Verified. Staff never receives faculty navigation, panels, or state,
and faculty never receives the staff approval queue. Backend denies
staff on /students/me/* and all admin-only faculty-denied surfaces,
while faculty is denied on the approval queue. Both minimal workspaces
remain separate despite similar shapes.

## Faculty-to-Student boundary

Verified. Faculty cannot use /students/me/* and receives the same 404
as every non-student account. No faculty-to-student academic data
contract was created in this phase; the absence is intentional and is
pinned by test.
## Student privileged boundary

Verified server-side rather than from UI absence. A student is denied
403 on every admin surface in the full matrix sweep before any database
interaction and remains confined to its own /students/me/* identity
chain.

## Chat boundary

Verified as isolation only. ChatShell is reused verbatim inside every
authorized role shell. Chat authorization remains the existing
get_current_user contract. No per-role bypass was found and no chat,
session, or tenant state leaks across transitions. No generation or
retrieval redesign and no contract change were made.

## Accessibility and responsive integration

Verified with one parity fix. All four shells keep native-button
navigation with landmark labels, aria-current page marking, one h1 per
view, status and alert regions, visible focus rings, keyboard
reachability, wrapping and shrinking headers, collapsing grids, and
locally scrolling tables. AdminShell gained the overflow-x-clip root
and min-w-0 header row already present in the other shells. No visual
system was redesigned.

## Frontend integration tests

New dedicated suites: frontend/src/CrossRoleIntegration.test.tsx with
13 tests for shell mapping including null and unknown, navigation
mapping including forbidden entries, transitions including same-role
and different-tenant changes, logout to login, leakage, and token
exposure; and frontend/src/CrossRoleSessionLifecycle.test.tsx with 11
tests for restore, expiry including stale-token safety, logout,
multi-tab, and storage audit. Result: 24 of 24 pass; full suite is 47
files and 402 tests passing.
## Backend integration tests

New backend/tests/test_cross_role_integration_phase_6_20.py with 26
tests over 910 lines: role resolution and precedence; /auth/me per role
plus client-parameter resistance and unsupported role; full admin-only
matrix denial for student, faculty, and staff; staff approval exception
including 409 and stability; student-chain closure; tenant isolation
reads; cross-tenant write-nothing proofs; tenantless safety; chat auth
check; and a no-token-material check. Existing tests were not weakened.
Result: 26 of 26 pass; full backend is 1929 passed and 15 skipped.

## Full regression

Backend: python -m pytest tests -q gives 1929 passed and 15 skipped,
including the 26 new tests. Frontend: npx vitest run gives 47 files and
402 tests passing, including the 24 new tests. TypeScript with
npx tsc --noEmit exits 0. Production build with npm run build succeeds.
Authentication, registration, student, faculty, staff, admin, RAG, and
chat suites remain green.

## Deferred capabilities

Documented, not built: faculty profiles and assignments; staff
departments and employee IDs; student-owned profile editing; new
academic models; new role types; new chatbot or RAG architecture;
mobile application; billing and subscriptions. The faculty-to-student
academic absence is intentionally unavailable. Nothing missing required
invention and nothing was invented.

## Security findings

Found and fixed two items. First, same-element-type shell reuse could
preserve stale view and data across authentication replacement; fixed
by identity-keyed remount and covered by transition tests. Second,
AdminShell lacked overflow-clip parity; fixed with a visual-only class
change. Audited and clear: no cross-tenant access or mutation, no
privilege escalation for staff, faculty, or student, no stale admin
data after switching, no token, password, or secret in DOM, storage, or
responses, and no client-derived authorization. Security gate: PASS.
## Performance findings

Initial authenticated requests per shell: student loads profile,
attendance, results, test results, notices, and resources through its
existing parallel dashboard path; faculty loads no extra role probe;
staff loads the approval queue plus dashboard summary paths already
present; admin loads dashboard summary plus the selected manager path.
No duplicate /auth/me calls were introduced: restore validates once and
shells reuse AuthProvider state, asserted once per restore test. No
mutation retries exist: denied mutations stop at the role dependency.
Cross-role cleanup is a synchronous unmount through the shell key. No
caching framework was added; none was required.

## Documentation verification

This file is PHASE_6_20_CROSS_ROLE_INTEGRATION_VALIDATION.md. Its
headings are exactly the 34 required section names from the phase
specification. Verified, fixed, intentionally unavailable, deferred,
and known limitation outcomes are stated separately in each section.

## Git scope

Modified: frontend/src/App.tsx for identity-keyed shell remounts and
frontend/src/features/admin/AdminShell.tsx for responsive parity.
Added: backend/tests/test_cross_role_integration_phase_6_20.py,
frontend/src/CrossRoleIntegration.test.tsx, and
frontend/src/CrossRoleSessionLifecycle.test.tsx. No unrelated files
were modified. No commit was created.

## Known limitations

Coverage uses mocked service and database boundaries for tenant and
write-nothing assertions, so it proves authorization ordering and
non-invocation rather than live-database behavior. Frontend transitions
drive the App boundary from AuthProvider state rather than live JWTs.
Multi-tenant fixtures use two institutions. These match the documented
testing patterns and do not weaken the security gate.

## Final verification

Role resolution, shell isolation, navigation isolation, API
authorization, staff approval exception, tenant isolation, mutation
safety, transition safety, stale view-state protection, leakage,
storage, session lifecycle, chat isolation, accessibility,
responsiveness, frontend tests, backend tests, regression, TypeScript,
build, documentation section count, and git scope all pass. Security
and performance gates pass.

## Final status

Phase 6.20 - COMPLETE. Stopping here. No Phase 6.21 work started, no new
capability added, no RAG or ChatShell redesign, no unrelated behavior
modified, and no commit created.
