# Phase 7.24 — Staff & Faculty Operational Capabilities Audit

## 1. Executive Summary

Phase 7.24 is an **audit and scope lock**. It adds no role, permission model,
user model, academic relationship, invitation system, email system, or
migration. Its only code artifact is a test suite
(`backend/tests/test_phase_7_24_staff_faculty_capabilities_audit.py`, 83
tests) that proves the conclusions below against the running application
rather than asserting them from reading alone.

### Headline findings

1. **Staff and Faculty are far more limited than their names suggest.** Across
   the entire API surface, Staff has exactly **two** operational capabilities
   and Faculty has exactly **one**:

   | Role | Operational capabilities |
   | --- | --- |
   | Staff | Student approval queue (tenant-scoped), Document ingestion pipeline |
   | Faculty | Document ingestion pipeline |

   Everything else — student records, attendance, results, tests, notices, FAQ,
   knowledge-source management, institution administration — is **not
   available** to either role.

2. **The Faculty role currently has zero Faculty-specific capability.** Faculty
   is authorized on precisely the same non-chat surface as Staff (the ingestion
   pipeline) and is denied the one capability Staff has (student approval). As a
   product surface, `FacultyShell` is a thin wrapper around the AI Assistant.

3. **There is no authoritative student-scope mechanism beyond
   `institution_id`.** Staff and Faculty are scoped **by role to a whole
   institution**. No teaching-assignment, class, section, department-owner, or
   per-student relationship exists anywhere in the schema ledger. This is the
   single most important constraint on Phase 7.25: *no faculty-scoped student,
   attendance, results, or test capability can be safely authorized until such a
   relationship exists.*

4. **The Phase 7.20 authorization chain is intact and was verified to hold.** No
   cross-tenant leak, role escalation, deactivated-account access, or Super
   Admin privilege inheritance was found. All eight required negative scenarios
   are now covered by executable tests.

5. **Two real gaps were found, both "usable surface" gaps rather than security
   holes:** (a) Staff/Faculty ingestion is authorized but has **no listing
   contract or UI**, so the target `knowledge_source_id` cannot be obtained —
   the capability is authorized but not operationally reachable; (b) the
   frontend capability cards for Staff/Faculty are **stale documentation**, and
   the Staff dashboard's Student-Management copy ("reserved for
   administrators") is accurate but the role name invites wrong expectations.

### Scope decision carried forward

Phase 7.25 should **not** attempt faculty teaching assignments. The
architecture does not support it and inventing it in this phase would be
unsafe. The evidence-based Phase 7.25 recommendation is in section 12.

---

## 2. Existing Staff Capabilities

Traced from `backend/app/api/admin.py`, `backend/app/api/ingestion.py`,
`backend/app/main.py`, and the frontend `features/staff/` package.

| Capability | Status | Evidence |
| --- | --- | --- |
| Identity / login | **Implemented** | `POST /api/v1/auth/login`; `GET /api/v1/auth/me` resolves `staff` from DB grant |
| Institution scope | **Implemented** | `require_institution_roles` → `AuthorizationContext(institution_id)` |
| View/manage students | **Missing** | No list/search/profile/update route is staff-authorized. `GET /admin/students` is `_ADMIN`-only |
| Handle student approval | **Implemented** | `GET /admin/students/pending`, `POST /admin/students/{id}/approve|reject` on `_APPROVAL = require_institution_roles("admin","staff")` |
| Access student information | **Missing** | `/students/me/*` requires a `students` row; a staff account has none → `404` |
| Use AI Assistant | **Implemented** | `POST /generation/chat` on `_INSTITUTION_CHAT`; `GET /conversations` |
| Access knowledge resources | **Partial** | No read/list contract exists for staff at all |
| Upload/manage knowledge | **Partial** | Ingestion stages are authorized; **no listing contract and no UI** to select a target |
| Access notices/FAQ | **Missing** | `GET /admin/notices`, `GET /admin/faqs` are `_ADMIN`-only |
| Access attendance | **Missing** | `/admin/students/{id}/attendance` is `_ADMIN`-only |
| Access results | **Missing** | `/admin/students/{id}/results` is `_ADMIN`-only |
| Access tests | **Missing** | `/admin/students/{id}/test-results` is `_ADMIN`-only |
| Onboarding decisions | **Missing** | `/admin/memberships/**` is `_ADMIN`-only (correct: admin manages staff) |
| Platform authority | **Missing (by design)** | `/platform/*` requires `super_admin` |

**Net:** Staff is a single-capability role — "help the registrar clear the
student approval backlog."

---

## 3. Existing Faculty Capabilities

| Capability | Status | Evidence |
| --- | --- | --- |
| Faculty profile | **Missing** | No `faculty`/`staffs` table. `FacultyIdentityCard` renders only email/role/institution, and explicitly states department is "Not provided by your institution yet" |
| Teaching assignments | **Missing** | No assignment table, no FK from any academic table to `users` |
| Student scope | **Missing** | No faculty→student relationship exists |
| Attendance | **Missing** | No faculty-authorized route |
| Results | **Missing** | No faculty-authorized route |
| Tests | **Missing** | No faculty-authorized route |
| Knowledge management | **Partial** | Ingestion pipeline only; no listing/UI |
| AI Assistant | **Implemented** | `POST /generation/chat`, `GET /conversations` |
| Notices/FAQ | **Missing** | Admin-only routes |
| Student information | **Missing** | Denied; no students row, no scope |

**Net:** Faculty's *only* implemented capability is the AI Assistant plus the
shared ingestion pipeline. It has **no Faculty-specific capability at all**.

---

## 4. Authorization Matrix (authoritative, code-verified)

Legend: ✅ implemented · ⚠️ partial · ❌ denied · ➖ role not applicable.
Every cell was verified against the dependency wired to the route.

| Capability | Admin | Staff | Faculty | Student | Super Admin |
| --- | :---: | :---: | :---: | :---: | :---: |
| Institution management | ✅ | ❌ | ❌ | ❌ | ✅ |
| Institution lifecycle (suspend/activate) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Staff/Faculty onboarding & roster | ✅ | ❌ | ❌ | ❌ | ❌ |
| Student approval | ✅ | ✅ | ❌ | ❌ | ❌ |
| Student CRUD | ✅ | ❌ | ❌ | ❌ | ❌ |
| Student information (own) | ❌ | ❌ | ❌ | ✅ | ❌ |
| AI Assistant | ✅ | ✅ | ✅ | ✅ | ❌ |
| Knowledge ingestion pipeline | ✅ | ✅ | ✅ | ❌ | ❌ |
| Knowledge source/document management | ✅ | ❌ | ❌ | ❌ | ❌ |
| Knowledge resource read | ❌ | ❌ | ❌ | ✅ | ❌ |
| Notices/FAQ management | ✅ | ❌ | ❌ | ❌ | ❌ |
| Notices read | ❌ | ❌ | ❌ | ✅ | ❌ |
| Attendance | ✅ | ❌ | ❌ | ✅ (own) | ❌ |
| Results | ✅ | ❌ | ❌ | ✅ (own) | ❌ |
| Test results | ✅ | ❌ | ❌ | ✅ (own) | ❌ |
| Audit log read | ✅ (own actor) | ❌ | ❌ | ❌ | ➖ |
| Admin dashboard | ✅ | ❌ | ❌ | ❌ | ❌ |
| Platform administration | ❌ | ❌ | ❌ | ❌ | ✅ |
| University Admin invitation | ➖ | ➖ | ➖ | ➖ | ✅ |

**Notable, verified corrections to assumptions in the brief:**

- The brief's template cell "Student approval → Faculty: ❌ unless explicitly
  supported" resolves definitively to **❌**. Faculty is absent from
  `_APPROVAL`; no faculty approval support exists.
- The brief's template cell "AI Assistant → Super Admin: ❌/platform" resolves to
  **❌**. `_INSTITUTION_CHAT` does not include `super_admin`, so Super Admin
  has *no* institution AI Assistant access. Verified by test.
- The brief's "Knowledge operations → Student: read-only where applicable"
  resolves to **✅ via `/students/me/resources`**, a *different* route from the
  admin knowledge-source surface. Students read only `published` sources.
- The brief's "Attendance/Results/Tests → Admin" resolves to **✅ for Admin,
  ❌ for Staff and Faculty**. There is no partial or implied staff/faculty path.

---

## 5. Student-Scope Analysis

**Question asked:** is Faculty/Staff access to students institution-wide,
explicitly assigned, role-based, or academic-assignment-based?

**Answer: role-based and institution-wide, and nothing narrower exists.**

### What the code proves

- `get_current_user` derives non-student `institution_id` **solely** from the
  primary role's institution grant:
  ```python
  scoped_institutions = {
      str(grant["scope_id"])
      for grant in role_assignments
      if grant.get("role") == primary_role
      and grant.get("is_active", True)
      and grant.get("scope_type") == "institution"
  }
  ```
- `user_roles` carries exactly `scope_type` + `scope_id`. A verified test
  asserts the table contains **no** `course_id`, `department_id`, `section_id`,
  or `program_id` column.
- Academic tables (`courses`, `departments`, `sections`, `course_offerings`)
  **do** exist, but a verified test asserts **none** references `public.users`
  and none carries an `instructor_/faculty_/teacher_` user column. There is
  therefore no path, even an indirect one, from a faculty account to a class.
- `institution_membership_requests.department` and `.designation` are **free-text
  onboarding metadata** collected at registration. They are not an authorized
  scope relationship and must not be read as one.

### Consequence (the important part)

Any implementation that grants a faculty member access to "their" students
would have to **invent** the definition of "their". There is no data to derive
it from. Doing so implicitly — e.g. treating `department` text on the membership
request as a scope key — would create an unsafe, client-influenceable scope
built on free-text supplied by the applicant at sign-up. **Phase 7.24
explicitly declines to create this and documents it as a prerequisite for a
later phase.**

The only student-scoped access that exists today is the **Student's own**,
resolved from the authenticated user id, and the **Admin's institution-wide**
list, resolved from the admin's institution grant.

---

## 6. Frontend Audit

| Surface | File | Real or placeholder | Notes |
| --- | --- | --- | --- |
| Staff shell | `features/staff/StaffShell.tsx` | **Real** | Reuses `ChatShell`; no second chat/session/token logic |
| Staff navigation | `staffNavigation.ts` | **Real** | 4 views, all server-verified; no router library, view state is local |
| Staff dashboard | `StaffDashboard.tsx` | **Real (zero-request)** | Renders identity + static capability map; no invented counts |
| Staff approvals | `StaffApprovals.tsx` | **Real** | The only data-loading staff view; loading/empty/error/retry/409-refresh |
| Staff profile | `StaffProfile.tsx` | **Real but thin** | Honestly states no department/designation/assignment exists |
| Staff identity | `StaffIdentityCard.tsx` | **Real** | Email/role/institution-link only; never renders internal ids |
| Faculty shell | `features/faculty/FacultyShell.tsx` | **Real** | 3 views |
| Faculty navigation | `facultyNavigation.ts` | **Real** | 3 views; no academic surfaces rendered |
| Faculty dashboard | `FacultyDashboard.tsx` | **Real (zero-request)** | Capability map with all academic areas marked not-available |
| Faculty profile/identity | `FacultyProfile.tsx`, `FacultyIdentityCard.tsx` | **Real but thin** | Department shown as "Not provided by your institution yet" |

### Shell selection and unauthorized states

- `App.tsx` `AuthenticatedShell` selects the shell **only** from the
  server-authoritative `/auth/me` role. No role probe, no inference from email
  or local storage.
- Unknown/unsupported role (`null`) → `UnsupportedRoleShell` ("Access
  restricted", sign-out). Fails safe.
- Shells are keyed on `` `${role}:${auth_user_id}` `` so a session replacement
  can never leave a previous role's or a previous tenant's view state mounted.

### Deactivated-user behavior

`AuthProvider` continues to hold a valid JWT after an admin deactivates the
account. The frontend therefore **still renders the shell**; the backend
re-reads `users.status` on every protected request and returns
`403 ACCOUNT_INACTIVE`. This is correct defense-in-depth, but the frontend has
**no deactivated-state UI** — the user sees the shell and then empty/failed
views rather than an explicit "your account was deactivated" message. Listed as
a UX gap, not a security gap.

### Institution identity display

Both shells render a generic **"College AI Chatbot"** header. The institution is
shown only as the boolean-ish string *"Linked to your institution"*. No
institution **name or code** is displayed anywhere in the Staff or Faculty
shell, even though `/institutions/{code}` lookup exists for the public flow.
Staff/Faculty cannot tell *which* institution they are acting for.

### Empty states

- Staff Approvals: full empty state with neutral copy.
- Staff/Faculty Dashboard capability cards: honest "Not available yet" wording,
  never a fake number or a misleading "coming soon" promise.
- **Faculty shell has no genuinely empty operational view** — Dashboard and
  Profile are static. This is the practical signature of a role with no
  operational capability.

---

## 7. Backend / API Audit

### Routers and their authorization dependencies

| Router | Dependency | Reachable by staff/faculty |
| --- | --- | --- |
| `/api/v1/admin/*` (most) | `_ADMIN = require_institution_roles("admin")` | ❌ |
| `/api/v1/admin/students/pending`, `/{id}/approve`, `/{id}/reject` | `_APPROVAL = require_institution_roles("admin","staff")` | ✅ staff only |
| `/api/v1/admin/memberships/**` | `_ADMIN` | ❌ |
| `/api/v1/documents/*` | `_INGEST_ALLOWED = require_institution_roles("admin","staff","faculty")` | ✅ |
| `/api/v1/generation/chat` | `_INSTITUTION_CHAT = require_institution_roles("admin","staff","faculty","student")` | ✅ |
| `/api/v1/conversations` | `get_current_user` | ✅ (owner-scoped) |
| `/api/v1/students/me/*` | `get_current_user` + student-profile resolution | ❌ (no students row) |
| `/api/v1/platform/*` | `require_super_admin` | ❌ |

### Legacy `require_roles` still exists

`require_roles(*allowed)` in `core/security.py` remains and does **not** require
an institution scope. All audited staff/faculty-reachable paths use the scoped
`require_institution_roles`. The legacy helper is a latent footgun (see §10).

### Services actually invoked by staff/faculty

- `services/admin_academics.approve_student` / `reject_student` →
  `_resolve_approval_target` enforces tenant **before** state (no state leak),
  then a conditional write; 409 on a lost race.
- `services/ingestion.ingest_document` + `chunking` / `embeddings` /
  `extraction` — four-stage pipeline with per-run tenant checks.
- `services/generation.process_chat_request`.

### The operational gap in knowledge

`_INGEST_ALLOWED` authorizes Staff and Faculty for `/documents/*`, but
`GET /admin/knowledge-sources` is `_ADMIN`-only. A staff/faculty member
therefore has **no way to learn a valid `knowledge_source_id`** for their own
institution. They would need a UUID supplied out of band. The capability is
*authorized* but not *operationally usable* — the honest classification is
**Partial**, and this is the clearest Phase 7.25 opportunity.

---

## 8. Authorization / Security Audit

### Chain verified intact

```
verified JWT
  -> get_current_user                       (JWT verify, load app user + grants)
  -> resolve_primary_role                   (super_admin>admin>staff>faculty>student)
  -> require_institution_roles(...)         (role ∩ active grants ∩ institution scope)
  -> resolve_institution_authorization_context
         - status must be 'active'          -> ACCOUNT_INACTIVE
         - role must be allowed             -> FORBIDDEN
         - role_assignments must be present -> SCOPE_MISSING
         - an institution grant must exist  -> FORBIDDEN / SCOPE_MISSING
         - exactly one institution          -> SCOPE_INCONSISTENT
         - institution active + is_active   -> TENANT_INACTIVE
  -> returns a COPY pinned to the resolved institution_id
  -> scope_tenant / assert_tenant_object / resource relationship checks
  -> tenant-filtered query
```

The pinned copy is significant: `require_institution_roles` overwrites
`institution_id` on the user dict it returns, so downstream `scope_tenant`
compares against a server value, not anything the client sent.

### Required negative scenarios — all now executable tests

| Scenario | Result | Error code asserted |
| --- | --- | --- |
| Staff A → Institution B (queue `?institution_id`) | **PASS** | `TENANT_MISMATCH`, repository never called |
| Staff A → Institution B (approve foreign student) | **PASS** | `TENANT_MISMATCH`, write never issued |
| Faculty A → Institution B (ingest) | **PASS** | `TENANT_MISMATCH` |
| Faculty A → Institution B (chat) | **PASS** | `TENANT_MISMATCH` |
| Staff → Admin capability (11 routes) | **PASS** | `FORBIDDEN` |
| Faculty → Admin capability (11 routes) | **PASS** | `FORBIDDEN` |
| Student → Staff approval capability | **PASS** | `FORBIDDEN` |
| Student → Faculty ingestion capability | **PASS** | `FORBIDDEN` |
| Deactivated Staff → approval queue / approve / ingest / chat | **PASS** | `ACCOUNT_INACTIVE` |
| Deactivated Faculty → ingest / chat | **PASS** | `ACCOUNT_INACTIVE` |
| Super Admin → approval queue / dashboard / roster / students | **PASS** | `FORBIDDEN` |
| Super Admin → ingestion / institution chat | **PASS** | `FORBIDDEN` |
| Staff/Faculty → platform surface | **PASS** | `FORBIDDEN` |
| Staff/Faculty → membership lifecycle | **PASS** | `FORBIDDEN` |
| Tenant-less staff/faculty grant | **PASS** | refused, queue never read |
| Suspended institution | **PASS** | refused, queue never read |

### Role escalation

- `institution_membership_requests.requested_role` is CHECK-constrained to
  `{staff, faculty}` at the database level — `admin` is not representable.
- `platform_admin_invitations.role_name` is CHECK-constrained to
  `{admin, staff, faculty}` — `super_admin` is not representable.
- `MembershipDecisionBody` is `extra="forbid"`; a verified test confirms
  `institution_id`, `requested_role`, `user_id`, `role`, and `organization_id`
  are each rejected with 422.
- No generic role-edit interface exists (verified by route inspection).
- Phase 7.23 approval RPC re-checks the role allowlist inside the transaction.

### Residual risk (documented, not exploitable today)

- `admin_audit_log` has **no immutable `institution_id`**; the audit read
  contract is own-actor filtering as a conservative tenant-safe workaround.
  A cross-tenant admin could not read another admin's rows today, but the table
  cannot *prove* tenant ownership.
- Tenant isolation is enforced by service-role-backed application code and DB
  integrity triggers, **not end-user RLS**. Consistent with existing
  architecture; noted as a standing design limitation.

---

## 9. Data-Model Gaps

| Gap | Current state | Impact |
| --- | --- | --- |
| Faculty/staff profile | No table | Profile pages can show only email/role/institution |
| Teaching assignment | No table, no FK | Blocks **all** faculty-scoped academic capability |
| Faculty ↔ student | No relationship | No safe per-student scope exists |
| Department ownership | `departments` exists but no owner FK | Cannot scope a faculty member to a department |
| Section/course offering ↔ faculty | Tables exist, no faculty column | Cannot scope to a class |
| Knowledge source visibility | No staff/faculty-visible listing | Ingestion target undiscoverable |
| Audit log tenant key | Absent | Audit reads use own-actor fallback |
| Role conversion (staff↔faculty) | No semantic | Out of scope since 7.23, still true |
| Multi-institution employment | `(user_id, role_id)` PK | One role cannot span two institutions |

---

## 10. Existing Architecture Duplications

Only duplications that carry **security, correctness, or maintenance** risk are
listed. Purely cosmetic overlap is deliberately excluded.

### 10.1 `require_roles` vs `require_institution_roles` — RISK

Two role-guard primitives exist. The legacy `require_roles` performs **only**
a role-name check: it does not require an active account, an institution grant,
or an active institution. Phase 7.20 correctly moved the audited admin and
ingestion paths onto the scoped dependency, but the weaker primitive is still
importable and still used elsewhere.

*Risk:* a future contributor adds `Depends(require_roles("staff"))` to a new
route and silently reintroduces the Phase 7.22 chat defect class (a tenant-less
principal being treated as unrestricted).

*Mitigation (recommended):* deprecate `require_roles` explicitly, or add a
guard test asserting it is not used on any institution-scoped router.

### 10.2 Duplicate `user_tenant_id` definition — LOW

`user_tenant_id` is defined twice in `core/security.py` (lines 143 and 280 in
the audited file). The second shadows the first. Behaviourally identical today,
so this is maintenance risk only, but it is exactly the kind of drift that
becomes a security bug when only one copy is later edited.

*Note:* this was flagged in 7.22 and remains **unfixed**. Phase 7.24 does not
fix it because this is an audit-only phase.

### 10.3 Duplicate tenant-resolution in the router — LOW/MEDIUM

`admin.py` defines local wrappers `_scope_institution` and
`_assert_row_tenant` that add policy on top of `scope_tenant` /
`assert_tenant_object` (notably: admin rows must be institution-owned, so a
global `institution_id = NULL` FAQ/notice is rejected with 403). The extra
policy is correct and deliberate, but it lives in a router instead of a shared
guard, so a new router could easily omit it.

### 10.4 Two student-approval presentations — LOW

`AdminApprovals.tsx` and `StaffApprovals.tsx` render the same API with different
copy and shells. Not a security issue (both call the same server-authorized
endpoints with no body), only duplication.

### 10.5 Registration path overlap — MEDIUM (unchanged from 7.22)

`services/tenancy.register_staff_or_faculty` and
`services/user_registration.register_user` both cover staff/faculty onboarding.
Phase 7.23 chose `/users/register` as canonical. The older service is not
mounted. *Risk:* a future phase mounts it and creates a second, inconsistent
onboarding path.

### 10.6 NOT duplicated (verified)

- **Authentication:** one chain — Supabase Auth + `get_current_user`. No second
  staff/faculty auth implementation exists.
- **Role storage:** one store — `roles` + `user_roles` +
  `assign_user_role_scope`. Platform assignment and membership approval both
  delegate to it.
- **AI Assistant:** one implementation. `StaffShell` and `FacultyShell` both
  reuse the shared `ChatShell`; there is no separate staff or faculty chat.
- **Invitations/email:** Phase 7.23 **extended** the existing Phase 7.14–7.18
  lifecycle (table reused, `phase717_create_invitation_with_outbox` overloaded,
  `email_outbox` reused). No second invitation or email system was created.

---

## 11. Implemented / Partial / Missing / Out-of-Scope Matrix

| Area | Implemented | Partial | Missing | Intentionally out of scope |
| --- | --- | --- | --- | --- |
| **Staff** | Login/identity; institution scope; student approval; AI Assistant | Knowledge ingestion (authorized, not usable); profile | Student CRUD/search; attendance; results; tests; notices; FAQ; knowledge management; roster access | Platform authority; institution management; role assignment |
| **Faculty** | Login/identity; institution scope; AI Assistant | Knowledge ingestion (same gap) | **Faculty-specific profile; teaching assignments; student scope; student info; attendance; results; tests; notices; FAQ** | Student approval (deliberately staff-only); platform authority |
| **Student** | Own profile, results, attendance, tests, notices, resources | — | — | Management surfaces |
| **Admin** | Institution academics; knowledge; notices/FAQ; dashboard; staff/faculty onboarding & roster | Audit-log read (own-actor fallback) | — | Platform authority |
| **Super Admin** | Institution CRUD/lifecycle; admin assignment/invitation | — | — | **All institution staff/faculty capabilities** (verified) |

---

## 12. Recommended Phase 7.25 Scope

Derived strictly from the evidence above. Ordered by value ÷ risk.

### P0 — Close the authorized-but-unusable knowledge gap (highest confidence)

The strongest evidence-backed finding: `/documents/*` is already authorized for
staff **and** faculty, but there is no listing contract to obtain a
`knowledge_source_id`. Add:

- `GET /admin/knowledge-sources` authorized for **admin + staff + faculty**,
  returning a minimal safe projection of the **caller's own institution only**
  (id, name, status — no storage keys, buckets, or internal metadata).
- A minimal staff/faculty knowledge view in the existing shells listing those
  sources and uploading into them.

*Why this is safe:* it reuses `require_institution_roles`, the existing
repository, and the existing ingestion pipeline. No new relationship, no new
role, no schema change, no new permission concept. Write authority beyond
ingest stays admin-only.

### P1 — Make the frontend capability presentation truthful

- Update `staffNavigation.ts` / `facultyNavigation.ts` capability maps and the
  Faculty dashboard so they describe what is actually available, including the
  honest "authorized to upload, cannot manage sources" distinction.
- Add explicit deactivated-account UI handling so a deactivated user sees
  "your account is no longer active" rather than a shell full of failures.
- Display institution **name/code** (not just "linked") in both shells.

*Why:* no backend or security change; removes the main source of confusion.

### P2 — Document (do not build) the faculty academic scope decision

Write the explicit product decision on what "a faculty member's students" means
and which table expresses it, and stop. Only after that decision exists should
any faculty academic capability be designed. This phase must not create the
table.

### Explicitly NOT recommended for 7.25

Faculty attendance/results/tests management; faculty student search; any
generic role editor; role conversion; multi-institution employment; RLS
rollout. Each either requires the unbuilt assignment relationship or would
weaken a currently-correct boundary.

---

## 13. Explicit Non-Goals

Phase 7.24 did **not**, by design:

- Implement any Phase 7.25 feature.
- Create an authentication, invitation, or email system (or a second of any).
- Weaken or bypass the Phase 7.20 tenant isolation chain.
- Make `institution_id` a client-controlled authorization input.
- Introduce generic role editing or role conversion.
- Invent faculty/student assignment semantics or any academic relationship.
- Modify remote Supabase or push a migration.
- Send production email or call Mailgun.
- Refactor duplicated code for aesthetics (duplications are **documented only**).
- Change any runtime behavior of the application.

---

## 14. Test Evidence

New audit suite: `backend/tests/test_phase_7_24_staff_faculty_capabilities_audit.py`

| Group | Coverage |
| --- | --- |
| Capability inventory | 22 cases — 11 admin-only routes × {staff, faculty}, all `403 FORBIDDEN` |
| Role separation | 3 — faculty denied on all three approval endpoints |
| Student boundary | 2 — student denied approval queue and ingestion |
| Cross-tenant | 6 — staff queue redirect, staff foreign approve, staff list, staff+faculty ingest, staff+faculty chat |
| Fail-closed scope | 4 — tenant-less and suspended-institution × {staff, faculty} |
| Deactivated users | 6 — staff queue/approve, staff+faculty ingest, staff+faculty chat |
| Super Admin isolation | 6 — 4 routes + ingestion + chat, plus symmetric staff/faculty→platform |
| Role escalation | 3 — no generic role editor, decision body forbids 5 fields, no onboarding lifecycle |
| Positive capability | 5 — ingestion reachable in-tenant, chat reachable and tenant-pinned, staff approval queue reachable and pinned, ingestion role tuple |
| Student-scope model | 8 — no profile tables, no assignment tables, `user_roles` has only scope columns, no academic table references `users`, no staff/faculty router |

| Suite | Command | Result |
| --- | --- | --- |
| Phase 7.24 audit | `uv run pytest tests/test_phase_7_24_staff_faculty_capabilities_audit.py -q` | **83 passed** |
| Backend (full) | `uv run pytest tests -q` | **2600 passed, 27 skipped** (was 2517; +83) |
| Frontend | `npm.cmd test -- --run` | **521 passed / 59 files** (unchanged) |
| TypeScript | `npx.cmd tsc -b --force` | **PASS** (exit 0) |
| Production build | `npm.cmd run build` | **PASS**, 113 modules transformed, Vite 7.3.6 |

Warnings are the pre-existing Starlette/httpx and Supabase client
deprecations. The host exports an invalid `DEBUG=release`, so runs explicitly
set `DEBUG=true`, matching the repository's established development-test
baseline.

**No existing test was modified, skipped, or weakened.** Six collection errors
under `scripts/manual_tests/` and `scripts/validation/` remain pre-existing
network-dependent scripts that are not part of `tests/`.

---

## 15. Remote-Safety Statement

| Item | Status |
| --- | --- |
| Remote Supabase modified | **NO** |
| Migration pushed or created | **NO** — no new migration in this phase |
| Production users/roles/institutions/data changed | **NO** |
| Production email sent / Mailgun invoked | **NO** |
| Production webhook invoked | **NO** |
| Second auth/invitation/email system | **NO** |
| New role or permission model | **NO** |
| Runtime behavior changed | **NO** — test-only additions |
| Phase 7.23 work preserved | **YES** — untouched and still passing |
| Files added | `backend/tests/test_phase_7_24_staff_faculty_capabilities_audit.py`, this document |

All verification used local unit/integration doubles. No local or remote
Supabase mutation command was run.