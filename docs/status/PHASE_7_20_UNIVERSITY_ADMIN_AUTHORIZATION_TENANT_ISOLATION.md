# Phase 7.20 — University Admin Authorization Context & Tenant Isolation

## Status

**COMPLETE**

The University Admin authorization chain is now driven by the existing scoped
`user_roles` authorization context. All 46 `/api/v1/admin` endpoints receive a
fail-closed, institution-scoped authorization context; missing scope, incorrect
scope, inactive account, and inactive institution are all denied; cross-tenant
object and list access is rejected; Super Admin platform isolation is preserved;
and the dashboard/audit reads are tenant-safe.

No schema change, migration, remote change, or email delivery occurred.

## Root Cause

Phase 7.19 found that the `/admin` authorization chain and the newer scoped
tenancy chain had diverged:

1. `get_current_user` projected `institution_id` **only** from
   `students.institution_id`. A University Admin is not a student and has no
   `students` row, so a legitimate institution-scoped University Admin resolved
   as **tenantless**.
2. The legacy guard helpers (`scope_tenant`, `assert_tenant_object`,
   `_approval_scope`) deliberately treated a **tenantless** account as
   *unrestricted*, so tenantless silently became platform-wide.
3. `/admin` only checked role membership (`require_roles("admin")`). Because
   University Admin grants are stored with `user_roles.scope_type='institution'`
   and `scope_id=<institution>`, an **organization-scoped** ordinary admin could
   satisfy `role == "admin"` and reach the same endpoints.

Net effect: institution scope was not enforced at all for University Admin
operations, the effective tenant came from the wrong source, and a correctly
scoped admin was indistinguishable from an unscoped privileged one.

## Previous Authorization Flow

```
request
  -> verify_jwt (Supabase JWKS)
  -> get_current_user
       -> get_user_by_auth_id
            roles[]           from user_roles -> roles
            institution_id     from students.institution_id      <-- WRONG SOURCE
  -> require_roles("admin")            role membership only, no scope
  -> scope_tenant / assert_tenant_object
       tenant is None  ->  passthrough / allow (treated as platform)
  -> service / repository  (often no tenant filter at all)
```

Legacy tenant source -> correct authorization source (remediation basis):

| LEGACY TENANT SOURCE | CLASSIFICATION | CORRECT AUTHORIZATION SOURCE |
| --- | --- | --- |
| `students.institution_id` via `get_current_user` | **A. Authorization tenant resolution** | `user_roles.scope_id` (+ `scope_type='institution'`) |
| `students.institution_id` in `get_sign_in_context` | B. Student-specific / sign-in lifecycle | **Retained** (the sign-in guard is student-scoped) |
| `students.institution_id` in student profile/result/attendance joins | B. Student-specific data relation | **Retained** |
| Tenantless => unrestricted branch in `scope_tenant` / `assert_tenant_object` | A. Authorization | **Defensive only** — now unreachable behind a scoped dependency |
| `_approval_scope` platform passthrough (`is_platform_admin`) | A. Authorization | **Removed** — fails closed with `SCOPE_MISSING` |
| Unfiltered `documents` / `student_results` / `test_results` / `student_attendance` dashboard counts | A. Authorization | **Replaced** with `!inner` tenant joins |

## Corrected Authorization Flow

```
request
  -> verify_jwt (Supabase JWKS)
  -> get_current_user
       -> get_user_by_auth_id  (users + user_roles + roles + students)
            roles[]            from user_roles -> roles (active roles only)
            status             from users.status
            role_assignments[] [{role, scope_type, scope_id, ...}]  <-- authoritative
            institution_id     = primary-role institution grant (scope_type='institution');
                                 else students.institution_id when the primary role
                                 is 'student'; else NULL
  -> require_institution_roles(*allowed)          <-- ONE common dependency
       1. resolve user_id                    else 400 INVALID_USER_CONTEXT
       2. users.status == 'active'           else 403 ACCOUNT_INACTIVE
       3. active role in allowed_roles       else 403 FORBIDDEN
       4. role_assignments is a list         else 403 SCOPE_MISSING
       5. >=1 matching ACTIVE grant for an allowed role with
          scope_type='institution' and non-null scope_id
                                             else 403 FORBIDDEN (wrong scope type)
                                             else 403 SCOPE_MISSING
       6. all matching institution scopes resolve to exactly ONE institution
                                             else 403 SCOPE_INCONSISTENT
       7. institutions.status=='active' AND is_active
                                             else 403 TENANT_INACTIVE
       8. return AuthorizationContext(user_id, role, scope_type,
                                      institution_id, is_active)
  -> scoped current_user copy pinned to the resolved institution
       ("institution_id" + "authorization_context")
  -> endpoint resource guards (_assert_row_tenant / _assert_student_tenant / scope_tenant)
  -> tenant-filtered service / repository query
```

The institution is therefore determined **only** by the server-owned
authorization context. A request body, query parameter, URL value, frontend
value, or an arbitrary student/FAQ/notice/document row can never become the
tenant.

## Authorization Context

The existing `app/services/authorization.py` abstraction was **extended and
reused** (no new tenant model, no new RBAC system):

```python
@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    user_id: UUID
    role: str                 # the selected allowed role
    scope_type: str           # always 'institution' for this context
    institution_id: UUID      # resolved from user_roles.scope_id
    is_active: bool
```

Resolved by `resolve_institution_authorization_context(current_user, *, allowed_roles)`
and exposed to endpoints through `require_institution_roles` in
`app/core/security.py`, which attaches the context to the scoped user copy.

Semantic guarantees:

* **Platform-scoped `super_admin` is a different context.** It is authorized by
  the untouched `require_super_admin` (fresh platform-grant read) and reaches
  `/api/v1/platform/*` only.
* **Missing scope is never "platform".** An absent institution grant yields
  `403 SCOPE_MISSING` / `403 FORBIDDEN`; it is never read as unrestricted.
* **An inactive institution is distinct from an unresolvable one** — the former
  is `403 TENANT_INACTIVE` (resolved but not usable), the latter
  `403 SCOPE_MISSING` (never resolved). Internal DB details are not exposed.
* The five required scopes stay distinct and are never collapsed: platform
  `super_admin`; institution `admin`; institution `staff`; institution
  `faculty`; institution/user `student`.

## University Admin Scope Rules

| Requirement | Rule | Failure |
| --- | --- | --- |
| ROLE | `admin` (approval queue: `admin` **or** `staff`) | `403 FORBIDDEN` |
| SCOPE | `user_roles.scope_type == 'institution'` with non-null `scope_id` | `403 FORBIDDEN` / `403 SCOPE_MISSING` |
| ACTIVE (account) | `users.status == 'active'` | `403 ACCOUNT_INACTIVE` |
| ACTIVE (institution) | `institutions.status == 'active'` and `is_active` | `403 TENANT_INACTIVE` |
| AMBIGUITY | exactly one institution scope | `403 SCOPE_INCONSISTENT` |
| INSTITUTION | required — never optional | fail closed |

`role == "admin"` alone can no longer authorize an institution-admin operation.
Organization-scoped and platform-scoped ordinary admins are explicitly denied.
`super_admin` does **not** implicitly satisfy an institution-admin operation; the
platform/institution boundary is preserved.

## Endpoint Remediation

- Total `/api/v1/admin/*` operations audited: **46** (verified from the
  generated OpenAPI schema; `/api/v1/admin-invitations/*` is a separate,
  token-authenticated router and is not part of the University Admin surface).
- Endpoints now covered by the scoped dependency: **46 of 46**.
- Endpoints changed: **46** (each swapped `require_roles(...)` ->
  `require_institution_roles(...)`), plus resource-level tenant enforcement
  added on document version/delete and on audit list/detail.
- Common authorization mechanism: **one shared dependency**, with no duplicated
  per-endpoint logic:

  ```python
  _ADMIN    = require_institution_roles("admin")
  _APPROVAL = require_institution_roles("admin", "staff")
  ```

  The same mechanism is applied to the institution document pipeline
  (`/api/v1/documents/*` -> `require_institution_roles("admin","staff","faculty")`).

Families verified: identity, dashboard, knowledge sources, documents
(list/get/upload/version/delete), FAQ (CRUD + publish), notice (CRUD), students
(list/create/get/update/archive), approval queue, student results
(list/create/get/update/delete + CSV upload), test results
(list/create/update/delete), attendance (list/create/update/delete), audit logs
(list/detail). Read endpoints are included — no endpoint was assumed safe.

## Tenant Filtering

Downstream reads/writes are filtered by the resolved context, never by input:

* **Dashboard** (`app/services/admin_dashboard.py`) — every count is scoped:
  `knowledge_sources`, `faqs` (active), `notices` (active) and `students` filter
  on `institution_id`; `documents`, `student_results`, `test_results` and
  `student_attendance` use relational `!inner` joins through
  `knowledge_sources` / `students` filtered on the context institution.
  No unfiltered count remains.
* **Resource-level authorization** — resources without their own
  `institution_id` are resolved through the relationship chain and rejected
  cross-tenant:
  * student -> document -> `knowledge_sources.institution_id`
  * FAQ / notice rows -> own `institution_id`
  * results / test results / attendance -> owning `student.institution_id`
  * documents and versions -> now 404 when the document or its knowledge source
    is missing (previously a silently skipped tenant check)
  * Global rows (`institution_id IS NULL`) are **not** readable or writable by a
    University Admin operation (`_assert_row_tenant` rejects `None`).
* The endpoint layer rejects a client-supplied `institution_id` that disagrees
  with the context (`scope_tenant`) and ignores it when it agrees.

## Dashboard Scope

Phase 7.19 flagged document metrics, result metrics, test-result metrics,
attendance metrics and recent audit metrics as unsafe. All are now scoped:

| Metric | Before | After |
| --- | --- | --- |
| `documents` | unscoped count | `!inner knowledge_sources` filtered by context institution |
| `student_results` | unscoped count | `!inner students` filtered by context institution |
| `test_results` | unscoped count | `!inner students` filtered by context institution |
| `attendance_records` | unscoped count | `!inner students` filtered by context institution |
| `recent_audit` | institution-wide | own-actor only (see below) |
| `students`, `knowledge_sources`, `faqs`, `notices` | institution-level | unchanged — already direct institution data |

No new metrics and no analytics infrastructure were introduced.

## Audit Scope

`admin_audit_log` has **no** `institution_id` column, so institution ownership
cannot be derived from the row. The conservative, fail-closed contract applied:

* `GET /api/v1/admin/audit-logs` always forces `actor_user_id = current_user`
  and returns **403** if a client supplies a different `actor_user_id`.
* `GET /api/v1/admin/audit-logs/{audit_id}` returns **403** unless the entry's
  actor is the caller.
* Dashboard `recent_audit` uses the same own-actor filter.

Consequence: another institution's audit records, and platform-level Super Admin
records, are never exposed to a University Admin. No schema change was made.

## Legacy Helpers

| Helper | Class | Disposition |
| --- | --- | --- |
| `scope_tenant` / `assert_tenant_object` | A | **Retained as defensive row guards.** The tenantless passthrough is no longer reachable for admin operations because `require_institution_roles` resolves and validates an institution scope first. |
| `_approval_scope` | A | **Retained, hardened** — the platform-admin global branch was removed; it now fails closed with `SCOPE_MISSING`. |
| `user_tenant_id` | A | Retained — reads the now-authoritative server-owned `institution_id`. |
| `require_roles` | C | Retained unchanged for genuinely role-only boundaries. |
| `_assert_row_tenant` / `_assert_student_tenant` | A | Retained and strengthened (global rows rejected). |
| `get_sign_in_context` students projection | B | Retained — legitimate student sign-in lifecycle. |
| Student profile/result/attendance `students.institution_id` joins | B | Retained — legitimate student data relations. |
| `require_super_admin` | — | **Unchanged** (Phase 7.12–7.18 behaviour preserved). |

No valid student data relationship was removed; the duplicated *authorization*
tenancy derivation was eliminated.

## Security Tests

New file `backend/tests/test_phase_7_20_university_admin_tenant_isolation.py` —
**24 passed**. It uses two institutions (A/B), two institution-scoped admins,
two students, and a platform `super_admin`, and covers:

* `/auth/me` projects institution scope from `user_roles.scope_id` with **no**
  student profile, and never from a student row.
* Admin A can read its own institution; Admin B can read its own.
* Cross-tenant **read** denied for FAQ, notice, students, results, test-results
  and attendance.
* Cross-tenant **mutation** denied for FAQ and notice.
* Global (`institution_id IS NULL`) FAQ mutation denied for a tenant admin.
* Missing admin scope denied; inactive institution denied; inactive account
  denied; wrong scope type (organization/platform) denied.
* Forged `institution_id` in body and query are ignored for authorization.
* Unknown resource id denied.
* Audit list forced to own actor; cross-actor detail and filter denied.
* `super_admin` -> `/api/v1/platform/*` allowed, `super_admin` -> ordinary
  `/admin` endpoint **403** (no privilege broadening).

Legacy suites updated to the corrected fail-closed policy (expectations changed
from "tenantless admin is unrestricted" to "denied"; cross-tenant assertions
were never relaxed): `test_rbac_phase_6_6`, `test_tenant_isolation`,
`test_role_scope_enforcement_phase_6_13_7`,
`test_security_final_validation_phase_6_13_9`, `test_student_approval_phase_6_4`,
`test_attendance_phase_6_7`, `test_results_phase_6_8`,
`test_cross_role_integration_phase_6_20`, `test_staff_experience_phase_6_18`,
`test_faculty_experience_phase_6_17`, `test_sign_in_phase_6_13_6`,
`test_complete_product_demo_phase_6_22`,
`test_platform_production_readiness_phase_6_21`,
`test_student_experience_dashboard_phase_6_16`,
`test_student_academic_detail_phase_6_16_2`,
`test_organization_institution_phase_6_13_1`, plus the ingestion / chunking /
extraction / embedding suites.

## Regression Tests

| Suite | Result |
| --- | --- |
| Phase 7.20 focused | **24 passed** |
| Admin API / dashboard / admin experience / auth | passed |
| RBAC (`test_rbac_phase_6_6`) | passed |
| Role + scope enforcement (6.13.7) | passed |
| Security final validation (6.13.9) | passed |
| Tenant isolation | passed |
| Organization/institution (6.13.1) | passed |
| Super Admin authorization (7.12) | passed |
| Ingestion / chunking / extraction / embedding | 139 passed |
| Invitation & admin lifecycle (7.14–7.18) | passed |
| Complete product demo (6.22) / platform readiness (6.21) | passed |

## Full Verification Results

| Check | Command | Result |
| --- | --- | --- |
| Focused Phase 7.20 | `pytest tests/test_phase_7_20_university_admin_tenant_isolation.py` | **24 passed** |
| Complete backend suite | `pytest tests` (from `backend/`) | **2451 passed, 27 skipped**, 7 warnings |
| Backend, production-like (`DEBUG=false`) | `DEBUG=false pytest tests` | **2449 passed, 2 failed, 27 skipped** |
| Frontend | `npm test` (from `frontend/`) | **58 files / 510 tests passed** |
| TypeScript | `npx tsc -b --force` | **passed** (exit 0) |
| Production build | `npm run build` | **passed** — 112 modules transformed |
| Artifact / secret scan | `node scripts/verify_frontend_build_security.mjs` | **PASSED** (4 dist files scanned) |
| Python lint | `python -m ruff check` | **not available** — ruff is not installed in this venv, so no lint run was possible |

**Environment-specific failures disclosed (not hidden):** the two `DEBUG=false`
failures are `test_conversational_rag.py::test_dev_diagnostics_attach_to_generation_metadata`
and `test_conversational_rag.py::test_standalone_question_diagnostics_rewritten_query_is_none`.
They assert development diagnostics that are intentionally absent when
`DEBUG=false`, are unrelated to authorization or tenant isolation, and are
identical to the failures recorded in the Phase 7.19 baseline. Rerun with
`DEBUG=true`: **2 passed**.

Frontend note: one `src/App.test.tsx` test failed in a first full parallel run
(509/510) and passed both in isolation (8/8) and on the full rerun (510/510).
It is a load-related flake in an untouched frontend file; no frontend source was
changed in this phase.

## Migration

**NONE**

`user_roles.scope_type` / `scope_id` already carried the required institution
scope, so no schema change was necessary and none was created. No migration file
was added; `supabase/migrations` is unchanged.

## Remote Safety

- Remote Supabase changed: **NO**
- Migrations pushed remotely: **NO**
- Production users / roles / data changed: **NO**
- Production institutions modified: **NO**
- Production email sent / Mailgun invoked: **NO**
- Remote Supabase status: **unchanged**; only the local/test database and mocked
  clients were used. No live server was started and no validation target was
  contacted.

## Remaining Limitations

1. **Audit scoping is own-actor, not institution-wide.** `admin_audit_log` has no
   `institution_id` column, so a University Admin sees only their own entries
   rather than all activity for their institution. This is deliberately
   conservative and fail-closed. Adding an immutable `institution_id` (written
   server-side at write time from the authorization context) would safely widen
   this later, but that is a schema change and therefore out of scope here.
2. **No schema-level tenant constraint.** Supabase RLS is not used for these
   tables (service-role client plus application-layer authorization, the
   existing project architecture). The boundary is the application layer.
3. **Platform-admin global approval authority was intentionally removed.** There
   is no longer any way to approve students across institutions through
   `/admin`; cross-institution administration lives only in the Super Admin
   surface. This is a deliberate behaviour change required by this phase, and
   the affected legacy expectations were updated accordingly.
4. **Scoped authorization depends on the `get_current_user` projection.** Callers
   that bypass `get_current_user` (tests using `dependency_overrides`) must
   supply a `get_current_user`-shaped principal; production callers cannot.
