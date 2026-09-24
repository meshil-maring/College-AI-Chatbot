# PHASE 6.13.9 — Security + Final Validation

Phase 6.13.9 is the FINAL validation phase for the **Phase 6.13
Organization & Multi-Tenant Architecture** (Phases 6.13.1–6.13.8).

**No new product features were added.**
**No new roles, endpoints, authentication providers, billing, dashboards,
frontend work, RLS redesign, or unrelated refactoring were added.**
Only genuine security / authorization / tenant-isolation / integration
defects could have been fixed. None were found: the system built in
6.13.1–6.13.8 already fails closed at every manipulated boundary, so
**no source file required a fix** in this phase.

## 1. Inputs Read

Scope reports read:

- `PHASE_6_13_1_SCOPE_REPORT.md`
- `PHASE_6_13_2_SCOPE_REPORT.md`
- `PHASE_6_13_3_SCOPE_REPORT.md`
- `PHASE_6_13_4_SCOPE_REPORT.md`
- `PHASE_6_13_5_SCOPE_REPORT.md`
- `PHASE_6_13_6_SCOPE_REPORT.md`
- `PHASE_6_13_7_SCOPE_REPORT.md`
- `PHASE_6_13_8_SCOPE_REPORT.md` (not present as a file in this checkout;
  validated instead from its implementation
  `backend/app/services/public_chat.py`, its test suite
  `backend/tests/test_public_protected_ai_phase_6_13_8.py`,
  and the Phase 6.13.7 report regression section covering it)

Existing security / RBAC / tenant tests inspected:

- `backend/tests/test_tenant_isolation.py`
- `backend/tests/test_rbac_phase_6_6.py`
- `backend/tests/test_student_auth_phase_6_5.py`
- `backend/tests/test_student_registration_phase_6_3.py`
- `backend/tests/test_role_scope_enforcement_phase_6_13_7.py`
- `backend/tests/test_public_protected_ai_phase_6_13_8.py`

The existing architecture was NOT rewritten to make this phase look
different, per the brief.

## 2. Files Changed

### New Files

- `backend/tests/test_security_final_validation_phase_6_13_9.py` —
  72 targeted final-validation security tests (all mocked; no live
  services). TEST-ONLY addition required by the brief; no product
  behaviour added.
- `PHASE_6_13_9_SCOPE_REPORT.md` — this report.

### Modified Existing Files

**None.** Validation discovered **zero unresolved security /
tenant-isolation / authorization / authentication / data-integrity /
integration-regression defects** within Phase 6.13 scope. Per the fix
policy ("Only fix genuine ... defects" / "Keep fixes minimal"), absent
a genuine defect there was nothing to fix, and no existing test was
modified to hide any failure.

## 3. Migration Created

**None.** No schema change required. Validation reads only existing
columns/constraints/triggers:

- `user_roles` (`role_id`, `is_active`, `scope_type`, `scope_id`,
  `scope_organization_id`)
- `organizations` (`organization_id`, `status`)
- `institutions` (`institution_id`, `organization_id`, `status`,
  `is_active` trigger-derived)
- `students` / `public.users` / request ledgers / knowledge tables —
  read-only tenant + lifecycle checks; existing CHECK / FK / trigger
  constraints relied upon, not redesigned.
## 4. Architecture (built in 6.13.1-6.13.8; re-validated, not redesigned)

### Organization to Institution to User

Organization A holds Institution A1 and Institution A2; Organization B
holds Institution B1. `institutions.organization_id` FK binds each
institution to exactly one organization
(`assert_institution_in_organization` per request).

Trusted chain is always server-side: JWT sub -> public.users ->
user_roles scope columns -> organizations / institutions lifecycle rows
-> resource/data -> AI/RAG context. A pending organization may still be
managed by its own admin while awaiting the platform decision;
rejected/suspended organizations and non-active institutions fail
closed.

### Role + scope model

- scope_type platform: no tenant restriction (previous behaviour;
  tenant-bound accounts may never hold it).
- scope_type organization: admin of ONE organization (all its
  institutions; cross-organization access denied).
- scope_type institution: bound to ONE institution (all
  cross-institution access denied for student / faculty / staff /
  institution admin).
- Legacy rows with scope_type NULL derive tenant-bound to institution,
  otherwise platform (never silently widened).
- Role enforcement reuses locked Phase 6.6 require_roles; scope adds
  assert_scope_consistency + assert_tenant_context_active /
  assert_active_tenant_context (Phase 6.13.7, additive only).

### Tenant isolation

Institution id is the tenant key. Tenant-bound users touch only their
own tenant (scope_tenant / assert_tenant_object, unchanged).
Organization admins reach every institution of their OWN organization
and nothing of any other organization. Pipeline steps (ingest /
extract / chunk / embed) resolve run to knowledge source to tenant
server-side.

### Public / protected AI separation

Public AI (process_public_chat_request, PUBLIC_USER_ID) is
unauthenticated, resolves the institution server-side (exists + ACTIVE
+ belongs to a valid/active organization), scopes retrieval to that
institution, post-filters at the data-access boundary to PUBLIC source
types only (faq, notice, handbook), and rejects personalized queries
with 401 AUTH_REQUIRED. Protected AI requires login and enforces
institution/role scope plus own-data-only student access. The boundary
is data-access filtering, not prompt instructions.

## 5. Security Validation

### 5.1 Organization isolation - VERIFIED

New tests: TestOrganizationIsolation (10 tests). Org-A admin manages
own org but gets ORGANIZATION_MISMATCH (403) for Org B and 403 for
Institution B1. Org-A admin manages both institutions of Org A (A1 +
A2) and decides own join requests; decisions on Org-B join requests
denied. Retrieval-level: Org-A requests return only Org-A chunks;
Org-B chunks never enter the Org-A LLM context; explicit selection of
an Org-B source denied; cross-org academic-data reads denied (403
TENANT_MISMATCH). Normal + manipulated IDs tested; all fail closed.

### 5.2 Institution isolation - VERIFIED

New tests: TestInstitutionIsolation (8 tests). Student / faculty /
staff / institution-admin scoped to Institution A cannot read, ingest
for, approve in, manage, or decide join requests for Institution B
(403 TENANT_MISMATCH / FORBIDDEN). Institution admin cannot manage its
own organization nor decide Org-B join requests. Organization-scoped
admin reaches both institutions of its own org (A1 + A2) per the
existing model - verified as allowed.

### 5.3 Role escalation - ALL DENIED

New tests: TestRoleEscalation (12 tests). Manipulated role,
scope_type, scope_id, organization_id, institution_id, student_id,
user_id all fail: student to admin denied (require_roles 403
FORBIDDEN); institution admin to organization scope denied; Institution
A to Institution B denied (TENANT_MISMATCH); Organization A to
Organization B denied (ORGANIZATION_MISMATCH); widened scope columns
rejected (SCOPE_INCONSISTENT). Login / student-login / registration
schemas use extra=forbid + Literal restrictions, so role / scope_* /
status / admin payloads get 422 before any service call; student_id
path substitution denied (403).

### 5.4 Registration security - VERIFIED

New tests: TestRegistrationSecurity (8 tests). Organization
registration cannot assign arbitrary roles (schema forbids role;
service hard-codes organization-admin assignment). Institution
registration cannot bypass organization ownership (server resolves org
by public code; non-active org rejected). Student/faculty/staff
registration cannot create admin users (requested_role Literal staff /
faculty; admin unrepresentable, 422). Registration into inactive
institutions rejected; cross-tenant registration by manipulated IDs
rejected (server-side code-to-id resolution). Duplicate identities
rejected; passwords go only to the Auth provider and never into
application tables (insert-payload assertions).

### 5.5 Approval security - VERIFIED

New tests: TestApprovalSecurity (9 tests). Only platform authority
approves organizations (pending-org admin gets FORBIDDEN). Only the
owning organization admin decides institution / membership join
requests; institution admin denied. Cross-organization approval fails
(ORGANIZATION_MISMATCH). Pending organizations/institutions remain
protected; rejected organizations/institutions remain protected
(re-decision to NOT_PENDING, no state change). Repeated decisions are
idempotent-safe (second decision to NOT_PENDING, no inconsistent
state).

### 5.6 Authentication security - VERIFIED (no redesign)

New tests: TestAuthenticationSecurity (15 tests). Valid credentials
succeed; invalid credentials fail (safe 401). Missing public-user row
/ inactive user status denied. Pending/rejected students cannot bypass
sign-in; inactive institution blocks sign-in; approved student of an
active institution can sign in. Email, register-number, and
university-roll-number logins all work; academic-identifier lookup
REQUIRES institution_code (missing code rejected); admin credentials
cannot produce a student session. Role/scope cannot be supplied by the
client (schemas forbid extras).

### 5.7 Public AI security - VERIFIED at retrieval/context boundary

New tests: TestPublicAISecurity (10 tests; 3 more org-isolation AI
tests in TestOrganizationIsolation). Public chat requires no login (no
auth dependency on the route). Institution resolved server-side;
inactive institution / inactive org / unknown institution denied (fail
closed). Public-only retrieval enforced at the data-access boundary:
private-document chunks filtered before LLM context assembly; explicit
private knowledge-source selection denied. Student records /
attendance / results readers never invoked by the public path;
personalized queries rejected with 401 AUTH_REQUIRED; general policy
questions remain public. Client-supplied institution/organization IDs
cannot bypass filtering.

### 5.8 Protected AI security - VERIFIED (inside TestPublicAISecurity + §4)

The 10 TestPublicAISecurity tests cover the public/protected split at
the retrieval/context boundary (private chunks filtered, student
records / attendance / results readers never invoked on the public
path, personalized queries 401, cross-tenant denial). Protected-helper
fail-closed behaviour for cross-student / cross-institution /
out-of-scope access is additionally asserted in
TestOrganizationIsolation (cross-org academic reads) and
TestInstitutionIsolation (cross-institution reads/ingest/queues).
Existing Phase 6.13.8 suite (27 tests) re-run green. Students access
only their own protected academic data.

### 5.9 Lifecycle security - VERIFIED (inside auth/approval/public-AI tests)

PENDING to ACTIVE to REJECTED / INACTIVE. Covered by 15
TestAuthenticationSecurity tests (pending/rejected students denied,
inactive institution blocks sign-in, approved+active allowed) + 9
TestApprovalSecurity tests (pending/rejected organizations and
institutions remain protected; re-decisions are idempotent-safe) + 3
TestPublicAISecurity tests (inactive institution / inactive org /
unknown institution denied public AI). No token revocation implemented
(per brief: only if a defect required it - none did); the JWT-expiry
limitation is documented below.

### 5.10 Data integrity - CHECKS PASS (inside escalation/registration/approval tests)

Orphaned users (no active role rows) fail closed (SCOPE_MISSING);
orphaned memberships / invalid role-scope combos fail closed
(SCOPE_INCONSISTENT); institution-organization mismatch fails closed
(SCOPE_INCONSISTENT) — asserted in TestRoleEscalation
(test_scope_columns_cannot_be_widened_by_client and cross-tenant
denials). Duplicate academic identifiers rejected at registration;
invalid org/institution relationships denied by FK + application
guards — asserted in TestRegistrationSecurity
(test_duplicate_academic_identifier_rejected,
test_institution_registration_rejects_non_active_organization,
test_users_cannot_register_into_non_active_institution) and
TestApprovalSecurity
(test_rejected_organization_cannot_accept_institution_requests).
Existing DB constraints/triggers relied upon; no DB redesign.

## 6. Targeted Security Tests (new, Phase 6.13.9)

`backend/tests/test_security_final_validation_phase_6_13_9.py` — 72
tests, all mocked (stateful fake PostgREST client + dependency
overrides, per project convention). No live Supabase/GoTrue/LLM calls.

| Class | Tests | Result |
| --- | --- | --- |
| TestOrganizationIsolation | 10 | 10 passed |
| TestInstitutionIsolation | 8 | 8 passed |
| TestRoleEscalation | 12 | 12 passed |
| TestRegistrationSecurity | 8 | 8 passed |
| TestApprovalSecurity | 9 | 9 passed |
| TestAuthenticationSecurity | 15 | 15 passed |
| TestPublicAISecurity | 10 | 10 passed |
| **Total collected** | **72** | **72 passed** |

## 7. Regression Testing (exact results)

Phase-ordered re-runs, then the full suite. Nothing modified to hide
any failure.

| # | Suite | Result |
| --- | --- | --- |
| 1 | Phase 6.3 `test_student_registration_phase_6_3.py` | 26 passed |
| 2a | Phase 6.5 `test_student_auth_phase_6_5.py` | 46 passed |
| 2b | Phase 6.6 `test_rbac_phase_6_6.py` | 28 passed |
| 2c | Tenant `test_tenant_isolation.py` | 12 passed |
| 3 | Phase 6.13.1 `test_organization_institution_phase_6_13_1.py` | 44 passed, 4 skipped |
| 4 | Phase 6.13.2 `test_organization_registration_phase_6_13_2.py` | 34 passed |
| 5 | Phase 6.13.3 `test_institution_registration_phase_6_13_3.py` | 48 passed |
| 6 | Phase 6.13.4 `test_approval_workflow_phase_6_13_4.py` | 22 passed |
| 7 | Phase 6.13.5 `test_user_registration_phase_6_13_5.py` | 39 passed |
| 8 | Phase 6.13.6 `test_sign_in_phase_6_13_6.py` | 84 passed |
| 9 | Phase 6.13.7 `test_role_scope_enforcement_phase_6_13_7.py` | 40 passed |
| 10 | Phase 6.13.8 `test_public_protected_ai_phase_6_13_8.py` | 27 passed |
| 11 | Full backend suite (`backend/tests`) | **1401 passed, 15 skipped** |

Included in combined targeted re-run with the new 72 (§6): 522 passed,
4 skipped. Full suite: 1401 passed, 15 skipped (pre-existing skips;
zero failures). No existing test was edited; no test was changed to
hide a failure. No outdated-test documentation was needed because no
security change altered any previously asserted behaviour.

## 8. Known Limitations (explicitly NOT fixed)

Per the brief, these are documented, not claimed fixed:

- JWT remains valid until expiry after tenant deactivation. No token
  revocation was implemented (none required by any defect found);
  lifecycle is enforced at request time via fresh DB reads, so a
  token for a deactivated tenant fails closed on next use, but an
  already-issued token is still cryptographically valid until `exp`.
- No rate limiting / account lockout on auth endpoints.
- No Row-Level Security (RLS); isolation is enforced in the
  application service/authorization layer with admin-client reads.
- No production database integration tests (all validation mocked;
  constraints/triggers relied upon by code inspection against existing
  migration, not live-DB tests).
- Dev-only auth router remains present (`dev_auth_router`,
  DEVELOPMENT / TESTING ONLY); it was not touched in this phase.
- Phase `6.13.8` scope report file is absent from this checkout; its
  implementation + tests were validated directly (see §1).

## 9. Definition of Done — Checklist

- [x] Organization isolation verified (Org A vs Org B / Inst B1 /
  users / knowledge / academic data; normal + manipulated IDs).
- [x] Institution isolation verified (student / faculty / staff /
  institution admin; org-admin behaviour per existing model).
- [x] Role escalation denied (role / scope_type / scope_id /
  organization_id / institution_id / student_id / user_id).
- [x] Scope manipulation denied (extra=forbid + server-side scope).
- [x] Registration security verified (no arbitrary roles, no
  cross-tenant join, no admin creation, inactive rejected,
  duplicates rejected, passwords never in app DB).
- [x] Approval security verified (platform/org authority only,
  cross-org fails, pending/rejected protected, idempotent).
- [x] Authentication security verified (valid/invalid, lifecycle,
  email / register-number / roll-number, institution_code
  required, no client role/scope; no redesign).
- [x] Public AI cannot retrieve private data (boundary-filtered,
  not prompt-only).
- [x] Public AI cannot cross institutions.
- [x] Protected AI respects role + scope; student data is
  student-specific.
- [x] Lifecycle restrictions work
  (PENDING -> ACTIVE -> REJECTED / INACTIVE).
- [x] Data-integrity checks pass (existing constraints/triggers;
  no DB redesign).
- [x] All previous phase tests remain green (table in §7).
- [x] Full backend regression passes (1401 passed, 15 skipped).
- [x] No unresolved security defect remains within Phase 6.13 scope
  (zero fixes required; fix policy observed).
- [x] `PHASE_6_13_9_SCOPE_REPORT.md` complete.

