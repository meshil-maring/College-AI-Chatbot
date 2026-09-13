# PHASE 6.6 — RBAC STATUS (UNLOCKED, PENDING REVIEW)

Status date: 2026-09-13. Baseline: Phases 6.1-6.5 LOCKED. No LOCK file.

## 1. Existing RBAC architecture (inspected, reused, not redesigned)

- Single primitive `require_roles(*allowed)` (`core/security.py`):
  401 via `get_current_user`, else 403 `FORBIDDEN`. No second RBAC.
- Chain: GoTrue JWT -> `verify_jwt` -> `public.users`
  (`user_roles(roles(name, is_active))`) -> `students.user_id` ->
  `students.institution_id` -> `institutions`. Tenant key:
  `students.institution_id`. Helpers `user_tenant_id` /
  `scope_tenant` / `assert_tenant_object` (403 `TENANT_MISMATCH`).
- No migration, no duplicate role/tenant columns, no policy tables.
- Platform convention (6.1/6.4 locked): tenant-less accounts pass a
  requested institution through; only platform ADMINS hold global
  approval authority; platform staff -> 403.

## 2. Final role definitions

- admin: admin ops. Bound admin = own institution only. Platform admin
  (`institution_id=None`) = locked global authority.
- staff: approval (own tenant) + ingestion. No admin-only ops.
  Platform staff = 403 on approval (locked 6.4), never global admin.
- faculty: ingestion only (`admin/staff/faculty`). No admin, approval,
  platform, management, or student-approval rights. Tenant-scoped.
- student: own-identity ops only (`/students/me/*` server-side JWT
  resolution; own conversations; chat in own tenant). Nothing
  privileged; no other student's data.

## 3. Authorization matrix (existing policy, verified)

| Operation | Admin | Staff | Faculty | Student |
|-----------|-------|-------|---------|---------|
| Institution administration (`/admin/*`, audit) | yes | no 403 | no 403 | no 403 |
| Student administration (CRUD/results/attendance) | yes | no 403 | no 403 | no 403 |
| Approval queue/decisions | yes | yes, own tenant | no 403 | no 403 |
| Knowledge administration | yes | no 403 | no 403 | no 403 |
| Ingestion (`/documents/*`) | yes | yes | yes | no 403 |
| Student operation (me/conversations/chat) | own identity/tenant | own identity/tenant | own identity/tenant | yes, own only |

No dedicated faculty-only endpoint exists; none was invented.

## 4. Tenant interaction

Order: authenticate -> identify -> role -> tenant -> role check ->
tenant/object check -> operation. `scope_tenant` forces bound users
to their tenant (foreign -> 403); `assert_tenant_object` guards rows

## 5. Platform behavior

- Platform admin (`institution_id=None` + admin): global lists/reads/
  updates; approve/reject any student (write pinned to target tenant);
  optional `?institution_id=` filter on the pending queue.
- Platform staff (tenant-less + staff): 403 `FORBIDDEN` on approval
  queue/decisions (locked 6.4). Never a global administrator.

## 6. Student / faculty boundaries

- Student: `/students/me/*` resolve `users.user_id->students.user_id`
  server-side (client `student_id` inert); conversations
  ownership-scoped (foreign -> 404, no leak); chat tenant-scoped
  (foreign -> 403 before pipeline). 403 on all admin/approval/
  ingestion/management. Phase 6.9 NOT implemented.
- Faculty: ingestion only. 403 on admin-only and approval ops; 403
  `TENANT_MISMATCH` on cross-tenant ingest. No new faculty features.

## 7. Endpoint audit

- `/admin/*`: `_ADMIN = require_roles("admin")` everywhere + tenant
  guards on institution-carrying paths; approval trio `_APPROVAL =
  require_roles("admin", "staff")` + `_approval_scope`.
- `/documents/*`: `_INGEST_ALLOWED =
  require_roles("admin", "staff", "faculty")`; `/ingest` asserts the
  knowledge source tenant.
- `/students/me/*`: `get_current_user` + server identity (+ tenant
  assert on profile). `/conversations*`: auth + ownership.
  `/generation/chat`: auth + `scope_tenant` first.
- `/auth/*`, `/registration`: public by design; locked
  `extra="forbid"` blocks role/tenant escalation. `/dev/auth/*`:
  dev-flag gated; admin reset keeps `require_roles("admin")`.

## 8. Security behavior

Fail closed: 401 unauthenticated; 403 `FORBIDDEN` wrong role; 403
`TENANT_MISMATCH` wrong tenant; 403/404 wrong ownership (conversations
use 404 anti-enumeration). Denied operations never execute
(`assert_not_called`); never 200-with-empty. Login normalizes to 401
`INVALID_CREDENTIALS`; approval checks tenant BEFORE state.

## 9. Tests

NEW `backend/tests/test_rbac_phase_6_6.py` (28 hermetic tests, no
production changes): 401s; admin allow/deny/platform-global; staff
allow/admin-deny/platform-staff-403; faculty ingest-allow/admin- and
approval-deny/cross-tenant-deny; student own-allow + all privileged
deny + cross-user 404 + cross-tenant chat deny; registration/login
role-field 422; approval-body tampering inert; tenant tampering 403;
fail-closed.

## 10. Database / RLS

NONE. No migration; existing roles/user_roles/students/institutions
reused. No `CREATE POLICY`/RLS statements exist in migrations;
service-role + application-layer guards remain the model. No RLS
redesign attempted.

## 11. Known limitations

- Run-scoped ingestion sub-steps (extract/chunk/embed) are role-gated
  but do not yet traverse run->version->document->source->institution
  (locked 6.1 limitation, carried forward; harden before trusting
  multi-tenant run-scoped ingestion in production).
- Root-run full suite shows pre-existing environment-dependent
  failures unrelated to RBAC (missing `backend/.env`: `supabase_url
  is required`; R2 default `documents` vs test `college-ai-knowledge`;
  one vector-search error-code expectation). RBAC + 6.1-6.5 scope is
  green; no existing test was weakened.

## 12. Phase 6.7 boundary

NOT implemented: 6.7 attendance, 6.8 results, 6.9 student-specific
data, 6.10 personalized chatbot, 6.11 broader security, 6.12 demo
validation. Phase 6.6 is RBAC/authorization verification only.

(global NULL rows visible). Approval writes are pinned
(`WHERE student_id AND institution_id AND pending`).
