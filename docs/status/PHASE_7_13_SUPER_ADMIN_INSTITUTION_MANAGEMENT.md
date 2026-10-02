## Phase Status

**COMPLETE**

All acceptance criteria are met. The Super Admin can list, create, view, update,
suspend and reactivate institutions; assign a University Admin; and the platform
boundary is enforced server-side on every endpoint with tenant roles uniformly
denied. Existing authentication, RBAC, public-chat and tenant-isolation behaviour
is unchanged (2,229 backend tests, +83 over the 2,146 baseline, zero failures).

## 1. Objective

Deliver the first real Super Admin platform-management capability: **institution
management**. The Super Admin manages the universities/colleges registered on the
platform *without* gaining unrestricted access to student data and *without*
bypassing tenant boundaries.

Primary demo workflow delivered end to end:

```
Super Admin -> Institutions -> Create Institution -> Configure Institution
            -> Assign University Admin -> University Admin manages institution
```

## 2. Existing institution model (reused, never duplicated)

The canonical tenant **already existed**; Phase 7.13 reuses it.

| Table | Role in Phase 7.13 |
|---|---|
| `public.institutions` | **Canonical tenant.** PK `institution_id`, `code` (globally UNIQUE), `name`, `status`, `is_active`. |
| `public.organizations` | Phase 6.13 parent. `institutions.organization_id` is NOT NULL, so an institution cannot exist without one. |
| `public.users` | Actor and assignment target. |
| `public.roles` / `public.user_roles` | Role + Phase 6.13 scope (`scope_type` / `scope_id` / `scope_organization_id`). |
| `public.students` | Untouched; `students.institution_id` remains the tenant key for student data. |

Fields reused as-is: `id` (`institution_id`), `code`, `name`, `status`.
No `university`, `college`, `institution`, `tenant` or `organization` table was
created for this concept, and a test asserts the migration creates no such table.

### Slug decision — no `slug` column

The existing `institutions.code` **already fulfils** the user-facing URL
identifier requirement for both routes:

```
/u/{institution-code}          (Phase 7.11)
/u/{institution-code}/ai       (Phase 7.11)
/public-chat/{institution_code} (existing public chat)
```

Adding a `slug` column would create a second source of truth for the same public
identifier and a migration strategy for existing codes. Phase 7.13 therefore
makes the **smallest schema change** and keeps `code` as the single routing
identifier. A test asserts `"slug"` never appears in the migration.

## 3. API design

All endpoints live under the existing `/api/v1/platform` router and **every one**
declares `Depends(require_super_admin)`:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/platform/me` | Phase 7.12 authorization proof (unchanged) |
| GET | `/api/v1/platform/institutions` | List institutions (safe metadata) |
| POST | `/api/v1/platform/institutions` | Create institution (ACTIVE) |
| GET | `/api/v1/platform/institutions/{id}` | Institution detail |
| PATCH | `/api/v1/platform/institutions/{id}` | Update safe configuration |
| POST | `/api/v1/platform/institutions/{id}/suspend` | Suspend |
| POST | `/api/v1/platform/institutions/{id}/activate` | Reactivate |
| POST | `/api/v1/platform/institutions/{id}/admins` | Assign University Admin |

Design rules applied:

* **Explicit schemas, never raw rows.** Responses are `InstitutionListResponse`,
  `InstitutionDetailResponse`, `InstitutionLifecycleResponse`,
  `InstitutionAdminAssignmentResponse`.
* **`extra="forbid"`** on every request model, so a client can never inject
  `institution_id`, `organization_id`, `role`, `scope_type`, `scope_id`,
  `status` or any other authorization-control field (422 before service logic).
* **`status` is absent from the PATCH schema.** Lifecycle changes go only through
  the dedicated, separately audited endpoints, so a generic field update can
  never silently suspend or reactivate a tenant.
* **Resource ids are not credentials.** `institution_id` in the path selects a
  target only; authorization is decided by `require_super_admin` alone.

### Safe institution representation

```json
{ "id": "...", "code": "UNICO", "name": "Unico University", "status": "active" }
```

The list projection adds only `is_active` and `admin_count`; detail adds optional
branding and timestamps. `organization_id`, `join_code`, contact details and every
tenant-owned table are never selected by the platform projection — a test asserts
this against the repository column list.

## 4. Institution lifecycle

Phase 6.13 already constrains `institutions.status` to
`pending | active | suspended | rejected` with a trigger that derives
`is_active` from `status`. Phase 7.13 **reuses that exact vocabulary** rather than
inventing a second status system:

```
create  -> ACTIVE          (a Super Admin explicitly provisioned the tenant)
active  -> normal institutional functionality
suspended -> normal institutional access restricted; ALL data retained
activate  -> suspended back to ACTIVE
```

### Suspension behaviour (exactly what is affected)

Suspend writes **only** `status = 'suspended'`. The existing Phase 6.13 trigger
derives `is_active = false`, and the guards that already read that flag now fail
closed:

| Path | Effect while suspended |
|---|---|
| Public AI (`/public-chat/{code}`, `/u/{code}/ai`) | 403 `INSTITUTION_NOT_ACTIVE` |
| Institution lookup (`/institutions/lookup`) | 403 `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS` |
| Sign-in (`sign_in.py`, `student_auth.py`) | denied — `is_active = False` |
| Student context / student surfaces | denied — `institution.is_active = False` |
| Tenant endpoints (`require_roles`) via `assert_tenant_context_active` | 403 `TENANT_INACTIVE` |
| Personalised retrieval | denied — same fail-closed rule |

**Never touched by suspension:** students, faculty, staff, admins, knowledge
sources, documents, embeddings, conversations. No account is revoked and no row is
deleted. Verified live: after suspending, the row is still present and readable,
and reactivating fully restores behaviour.

## 5. Creation flow

Required: **name + code**. Optional: display name, logo, primary colour,
secondary colour, welcome message, email, address, city, country. Branding is
never mandatory; absent values stay NULL and the public gateway keeps its
existing neutral defaults.

The institution is attached to a single reserved platform organization
(`COLLEGE-AI-PLATFORM`) created by the migration, because Phase 6.13 made the
parent FK structurally mandatory. If that reserved row is missing the service
fails closed with 500 `PLATFORM_ORGANIZATION_NOT_CONFIGURED` rather than inventing
a parent.

## 6. Institution code

* **Unique** — the pre-existing `institutions_code_key` UNIQUE plus a new
  `institutions_code_upper_key` unique index on `upper(code)`.
* **Normalized** — stripped and uppercased server-side; the client never decides
  casing (`"unico"` -> `"UNICO"`, verified live).
* **Deterministic** — one canonical stored form for lookup and routing.
* **URL-safe** — `^[A-Z0-9][A-Z0-9_-]{1,31}$`; no whitespace, slashes, percent
  signs, semicolons or non-ASCII. Matches the frontend route guard exactly.
* **No silent rewrites** — changing a code is an explicit PATCH by an authorized
  Super Admin; existing codes are never migrated automatically.

## 7. Institution list

Desktop-first (1280px+) table showing only `Institution | Code | Status | Admins`
plus a Manage action. No student information, academic records, private
documents, passwords, tokens or internal secrets are rendered or fetched.

## 8. Institution details

Implemented: Basic Information, Status, Branding, University Admins.
Labelled **Coming Soon** with no simulated behaviour: Public AI, Public Knowledge,
Platform Information.

## 9. Editing

PATCH updates name, code and optional branding/contact fields. The primary key and
the owning organization are structurally unreachable — `institution_id`,
`organization_id`, `status` and `is_active` are **absent** from
`MUTABLE_INSTITUTION_FIELDS`, which every write is filtered through. Only fields
the operator actually supplied are written (`exclude_unset`), so a partial update
can never blank an untouched value. An update therefore cannot reassign any
student, knowledge or document row.

## 10. University Admin assignment

**A controlled assignment flow, not account creation.**

* The target account must already exist in `public.users`; a missing account is a
  clean 404 `USER_NOT_FOUND` and **nothing is provisioned**.
* The payload carries **no password and no credential material of any kind**, so
  there is no unsafe Auth provisioning path.
* The requested role is **not accepted from the client**. The grant is hard-coded
  to the institution-scoped `admin` role via the existing
  `assign_user_role_scope` primitive, so the Phase 6.13 scope constraints stay
  authoritative and the grant can never become a platform grant or `super_admin`.
* Inactive accounts are refused (403 `ACCOUNT_INACTIVE`).
* Re-assignment is idempotent and audited as `already_applied`.

**Limitation (deliberate):** the Super Admin cannot create the account itself.
Account creation for platform-provisioned admins is documented as follow-up work
so that no unauthenticated or weakly-authorized endpoint can mint accounts.

## 11. Tenant isolation

* Every platform institution endpoint uses `require_super_admin()`.
* The principal is resolved from the verified JWT -> `public.users` ->
  `user_roles`; role, scope and tenant come from **database rows only**.
* `require_super_admin` re-reads account status and the active platform grant on
  **every** request, so revocation is immediate and a stale frontend cannot
  retain access.
* A University Admin from Institution A is refused on **all seven** endpoints for
  Institution B and for Institution A alike — verified by a parametrized matrix
  over `student | faculty | staff | admin`.
* Frontend gating is a UX affordance only; the backend re-authorizes every call.

## 12. Branding foundation

Established on the canonical row: `display_name`, `logo_url`, `primary_color`,
`secondary_color`, `welcome_message`. A basic configuration form only — no full
branding editor. Values are validated server-side: colours must be CSS hex and
logos must be absolute `http(s)` URLs, so `javascript:` and `data:` URLs cannot
reach the gateway's `<img src>` binding.

## 13. Public AI integration

No second public-chat backend was created. Institution creation makes the code
resolvable, and the existing resolution chain is reused:

```
/u/{institution-code}      -> institution lookup -> gateway
/u/{institution-code}/ai   -> existing public AI (same page as /public-chat/{code})
/public-chat/{institution_code} -> unchanged, still working
```

The detail view displays the resulting public URL. Creation returns ACTIVE, so a
newly created institution is immediately resolvable.

## 14. Auditability

New service-role-only ledger `platform_institution_audit_log` reusing the Phase
7.12 audit pattern (same REVOKE/GRANT shape as `platform_role_audit_log`). A
separate table is used because the Phase 7.12 ledger is constrained to the
super_admin role lifecycle and cannot represent institution actions.

Recorded: `actor_user_id`, `action`, `institution_id`, `target_user_id`,
`result`, `details`, `performed_at`.

| Action | Recorded |
|---|---|
| `institution_created` | code, resulting status |
| `institution_updated` | changed field names only |
| `institution_suspended` | resulting status |
| `institution_activated` | resulting status |
| `admin_assigned` | target user + `already_applied` when repeated |

`details` holds only non-sensitive summary data. Passwords, access tokens and
service-role credentials are never accepted — enforced by the function signature
and asserted by a test. `anon` / `authenticated` have no access to the table.

## 15. Security tests

`backend/tests/test_phase_7_13_super_admin_institution_management.py` — 84 tests.

* **Super Admin** can list / create / read / update / suspend / activate, with the
  code normalized server-side and every mutation audited.
* **Anonymous -> 401** on all seven endpoints.
* **student / faculty / staff / admin -> 403** on all seven endpoints (28 cases).
* **Tenant isolation** — an Institution-A admin cannot create, read, edit,
  suspend or activate Institution B; the role can never grant a platform scope.
* **Input attacks** — duplicate code (incl. lowercase and padded), malformed codes
  (too short/long, whitespace, traversal, `;`, non-ASCII, leading hyphen), empty
  and whitespace-only names, unexpected fields, and attempts to smuggle
  `institution_id` / `organization_id` / `role` / `scope_type` / `is_active` /
  `password` into the assignment payload — all 422.
* **Unsafe branding** — `javascript:`, `data:`, CSS-injection colours rejected.
* **Suspension** — writes only `status`; idempotent and audited `already_applied`.
* **Migration** — no destructive SQL, no Auth access, service-role-only grants, no
  duplicate entity, no `slug`, idempotent reserved organization.

Frontend: 19 tests (10 client + 9 component) covering header-only token
transmission, no password in the assignment payload, confirmation-before-suspend
with the retention guarantee, cancel-does-not-call-the-API, activate-vs-suspend
switching, Coming Soon labelling without faked behaviour, and error surfacing.

## 16. Migration details

* File: `supabase/migrations/20261001010000_phase_7_13_super_admin_institution_management.sql`
* Additive only: 5 nullable branding columns, 1 unique index on `upper(code)`,
  1 reserved organization row (`ON CONFLICT DO NOTHING`), 1 audit table.
* No existing migration was edited. The 17-migration validated history is intact.
* **Final migration count: 18** (ledger confirmed via
  `supabase_migrations.schema_migrations`).

Validation performed:

| Check | Result |
|---|---|
| Fresh local reset #1 | PASS — all 18 applied |
| Fresh local reset #2 | PASS — all 18 applied |
| Migration ledger | 18 rows; latest `20261001010000` |
| Phase 7.13 objects | 5 branding cols, audit table, `upper(code)` index, reserved org — all present |
| Duplicate `slug` column | absent (as designed) |
| Phase 6.11 | `student_notifications` present |
| Phase 7.2 | `idx_knowledge_sources_public_policy` present |
| Phase 7.4 | `search_public_knowledge_chunks(...)` present with Phase 7.4 signature |
| Live lifecycle smoke test | create -> suspend (`is_active=False`, row retained) -> reactivate -> update -> cleanup all correct |

Both resets ran through the guarded `scripts/validation/invoke_local_supabase.ps1`
wrapper, which refuses any non-local Docker target and requires
`-ConfirmLocalReset`.

## 17. Regression results

| Suite | Baseline | Final |
|---|---|---|
| Backend (full) | 2,146 passed / 15 skipped | **2,229 passed / 15 skipped** (+83) |
| Focused Phase 7.13 | — | **84 passed** |
| Frontend (full) | 443 passed / 55 files | **462 passed / 55 files** (+19) |
| `npx tsc --noEmit` | pass | **pass** |
| `npm run build` | pass | **pass** (107 modules) |
| `git diff --check` | clean | **clean** |

Existing routes verified intact: `/`, `/login*`, `/super-admin`, `/u`,
`/u/{code}`, `/u/{code}/ai`, `/public-chat/{code}`, `/auth/me`.

## 18. Known limitations

1. **No University Admin account creation.** Assignment only; the account must
   already exist. Follow-up phase.
2. **Code changes alter the public URL.** Changing a code is explicit and audited,
   but existing links to the old code are not aliased.
3. **Branding is a basic form.** No logo upload/storage, no live preview, no
   secondary-colour editor.
4. **Admin list shows a count, not the roster.** Assigning the same account twice
   reports `already_assigned` instead of listing admins.
5. **No admin revocation in this phase.** Assignment is idempotent; removal is
   follow-up work.
6. **Desktop-first only.** No mobile/tablet optimization.
7. **Audit ledger is write-only from the API.** There is no platform audit
   read endpoint yet.
8. **Super Admin cannot see tenant health.** No counts of students/documents per
   institution — deliberately, to avoid a platform view of student data.

## 19. Remote safety

A smoke script was run once while `backend/.env` pointed at the **remote**
project. It failed closed on the Phase 6.13 NOT NULL constraint
(`organization_id`) before writing anything. Remote state was then verified
explicitly and is unchanged.

```
Remote database modified: NO
Remote migrations applied: NO
Remote Auth modified: NO
Remote institution data modified: NO
Production deployment: NO
DNS modified: NO
```

Verified remotely after the fact: no branding columns, no
`platform_institution_audit_log` table, no `COLLEGE-AI-PLATFORM` organization, and
exactly one pre-existing institution (`GIT`). `supabase db push --linked` was
never executed; every reset used `--local` via the guarded wrapper.

## 20. Recommended next phase

**Phase 7.14 — Super Admin University Admin Lifecycle**, completing the
`Create Institution -> Create/Assign First University Admin` loop:

1. A **controlled, audited invitation** flow so the Super Admin can provision the
   first University Admin account without an unsafe public endpoint (one-time
   token, no password in the platform request, no service-role key in the browser).
2. **Admin roster + revocation** for an institution (the missing half of the
   assignment flow), reusing the same audit ledger.
3. Read-only **platform audit view** for institution management actions.

These build directly on this phase's institution entity, assignment grant and
audit ledger, and remain entirely within the platform/institution scope split
established here.
