# Phase 7.11 — Demo Landing Page & Platform Role Gateway

## 1. Objective

Phase 7.11 adds a desktop-first public demo gateway that makes the College AI Platform hierarchy visible without replacing the existing public chat, authentication, tenant, or RBAC systems.

Status: **COMPLETE**

## 2. Final landing-page structure

The root route now presents:

- College AI identity and a `DEMO` indicator;
- a short multi-tenant platform explanation;
- a visually separate public area with Public AI Chat;
- an authenticated area with Student, University Admin, Staff, Teacher / Faculty, and Super Admin entries;
- a roadmap-only `Add more` dialog for FAQ, Notices, Learning Resources, University Contact, WhatsApp, and Support;
- an explicit statement that public AI cannot access authenticated/student information.

The existing slate/emerald visual language, card patterns, focus rings, and typography conventions are reused. Super Admin uses a restrained violet accent to distinguish platform scope from institution scope.

## 3. Routes

| Route | Purpose |
|---|---|
| `/` | Public demo landing page; an already authenticated session resumes its server-selected shell. |
| `/login` | Existing shared authentication flow, general presentation. |
| `/login/student` | Student-labelled entry into the same authentication flow. |
| `/login/admin` | University-admin-labelled entry into the same authentication flow. |
| `/login/staff` | Staff-labelled entry into the same authentication flow. |
| `/login/faculty` | Teacher/faculty-labelled entry into the same authentication flow. |
| `/super-admin` | Existing authentication flow followed by strict `super_admin` role gating and a read-only platform placeholder. |
| `/u` | Institution-code selector using the existing safe public lookup endpoint. |
| `/u/{institution-code}` | Institution presentation gateway. |
| `/u/{institution-code}/ai` | Presentation alias that renders the existing `PublicChatPage`. |
| `/public-chat/{institution_code}` | Existing validated public-chat route, unchanged and still supported. |

Unknown and malformed routes fail to a safe local not-found page. Institution codes are decoded, normalized to uppercase, and restricted to the same narrow character/length boundary already used by public chat.

## 4. Role mapping

```text
Public AI          -> public
Student            -> student
University Admin   -> admin
Staff              -> staff
Teacher / Faculty  -> faculty
Super Admin        -> super_admin
```

The selected card is presentation and navigation context only. It is not sent as a role claim and cannot select a shell. After authentication, the existing `/auth/me` response remains authoritative.

## 5. Super Admin architecture

Implemented:

- `super_admin` is recognized by the canonical server role resolver with highest precedence;
- the frontend auth contract recognizes `super_admin`;
- `/super-admin` uses the existing `AuthProvider` and shared login form;
- only a server-returned `super_admin` role renders `SuperAdminShell`;
- the shell lists Institutions, University Admins, Platform AI, Usage, Features, Security, and Platform Settings as `Coming Soon`;
- the shell makes no management requests and contains no fabricated CRUD.

Not implemented:

- no `roles` seed row or Super Admin account assignment;
- no provisioning UI or credentials;
- no institution, administrator, AI-provider, usage, feature-flag, security, or analytics management API;
- no existing tenant-level `require_roles(...)` check grants access to `super_admin`.

The future control model is:

```text
Platform
├── Institutions
│   ├── Create
│   ├── Suspend
│   ├── Configure
│   └── Branding
├── University Admins
├── AI Platform
│   ├── Models
│   ├── Usage
│   ├── Limits
│   └── Provider configuration
├── Plans / Usage
├── Feature Flags
├── Security
└── Platform Analytics
```

## 6. Public vs authenticated AI boundary

`/u/{code}/ai` is only a presentation alias for the existing unauthenticated `PublicChatPage`; it sends the same narrow `{ institution_code, message }` contract and remains governed by the existing public visibility policy. The original `/public-chat/{institution_code}` route was not renamed or removed.

Authenticated AI remains inside the existing role shells and existing JWT-backed API flow. No student or authenticated data is exposed through the new public routes.

## 7. Tenant handling

The backend currently exposes a safe public lookup by institution code, not an institution list or public slug catalogue. Therefore the demo selector accepts a code supplied by the institution and verifies it with `GET /api/v1/institutions/lookup` before opening `/u/{code}`.

No institution is hardcoded and no fake institution is inserted. Login may receive the verified public code as display/form context, but the backend continues to resolve the authenticated user's actual institution from the established JWT → user → tenant chain.

## 8. Branding boundary

`InstitutionBranding` establishes the frontend boundary for:

- `institution.name`;
- `institution.logo`;
- `institution.primary_color`;
- `institution.secondary_color`;
- `institution.welcome_message`.

Only the institution name is currently available from the safe lookup response. Logo, colors, and welcome text use neutral local defaults. No persistence model or fabricated backend fields were added.

## 9. Future contact architecture

The `Add more` dialog marks contact and support as roadmap-only. The intended boundary is:

```text
Contact University
├── WhatsApp
├── Email
├── Phone
├── Contact Form
├── Direct Message
└── Request Callback
```

Future requests should flow from Student/Visitor → AI/Contact → Support request → University Admin → Admin follow-up. No WhatsApp integration, messaging, form submission, or support inbox was implemented.

## 10. Desktop-first scope

The layout targets laptop and desktop use at 1280px and above, uses bounded fluid containers and CSS grids, and avoids page-level absolute positioning or rigid fixed widths. Basic grid collapse prevents obviously broken narrower desktop layouts. Full mobile/tablet optimization is deferred.

## 11. Security decisions

- Existing JWT login, `get_current_user`, `get_user_by_auth_id`, canonical role resolution, `/auth/me`, `AuthProvider`, and shell selection remain the only authentication path.
- No frontend role selection is trusted for authorization.
- `super_admin` was not added to tenant-level backend permission checks.
- Super Admin is server-authoritative and fail-closed; tenant roles receive the existing restricted screen on `/super-admin`.
- No hardcoded password, authentication bypass, secret, service-role key, or fake production credential was introduced.
- Public routes stay outside `AuthProvider` and reuse only public lookup/chat contracts.
- Error states use controlled user-safe messages and do not expose backend diagnostics.

## 12. Tests

Frontend:

- full Vitest suite: **52 files, 440 tests passed**;
- focused coverage includes all six entries, route destinations, exact role-label mapping, Add More behavior, inert Coming Soon content, institution lookup/loading/error behavior, public-chat alias reuse, Super Admin shell selection, and existing cross-role/session lifecycle behavior.

Backend:

- focused authentication/RBAC role regression: **109 passed** (including a server-side proof that `super_admin` does not satisfy `require_roles("admin")`);
- complete automated `backend/tests` production-mode corpus: **2,129 passed, 15 skipped, 2 debug-only tests deselected**;
- two existing development-diagnostics tests require `DEBUG=true` and passed separately: **2 passed**;
- an unscoped `pytest` invocation was intentionally not treated as the automated result because it also collects live/manual scripts that require a separately running API. The complete automated corpus is `pytest tests`.

## 13. Build result

- `npx tsc --noEmit -p tsconfig.json`: **PASS**
- `npm run build`: **PASS**
- Vite production output: 103 modules transformed; JS 384.68 kB (98.18 kB gzip), CSS 45.26 kB (8.27 kB gzip).
- `git diff --check`: **PASS**.

## 14. Migration changes

Migration changes: **NONE**

The existing role table is name-based and the existing `user_roles.scope_type='platform'` structure can represent the future assignment, so no schema migration is required for code-level recognition. A future, separately reviewed migration/provisioning phase is required to seed and assign `super_admin`; Phase 7.11 deliberately does not improvise that data change or modify the validated migration chain.

## 15. Known limitations

- desktop-first; full mobile/tablet optimization is deferred;
- WhatsApp is not implemented;
- support inbox/ticketing is not implemented;
- full Super Admin management is not implemented;
- `super_admin` is not yet persisted/seeded or assigned to an account;
- institution branding beyond the safe public name uses frontend defaults;
- no public institution directory exists, so evaluators need an existing institution code;
- production deployment is not implemented.

## 16. Next-phase recommendations

The next phase should be a narrow Super Admin identity provisioning and authorization design review: define the local migration/seed strategy for the platform-scoped `super_admin` role, specify auditable assignment/revocation, and add dedicated platform APIs without broadening tenant-level role checks. After that contract is validated locally, institution branding fields and a safe public institution discovery/slug contract can be designed. Mobile/tablet refinement and support/contact workflows should remain separate phases.

## Remote safety

```text
Remote database modified: NO
Remote migrations applied: NO
Remote Auth modified: NO
Remote data modified: NO
Production deployment: NO
DNS modified: NO
```

