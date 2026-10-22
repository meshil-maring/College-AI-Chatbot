# Frontend services

Keep API clients, transport helpers, and their tests in the owning domain.
Import the relevant domain entry directly; keep the services root for this guide
and domain folders. Preserve the exported contracts when moving implementations,
and update callers, type imports, and Vitest mock paths together.

| Folder          | Responsibility and entry points                                              |
| --------------- | ---------------------------------------------------------------------------- |
| `admin/`        | `adminApi.ts`, admin student workspace, and domain-specific admin operations |
| `academics/`    | Cross-role curriculum, class, package assignment, request and history API    |
| `auth/`         | `auth.ts`, authentication endpoints/errors/transport, and development auth   |
| `chat/`         | `api.ts` for authenticated conversations; `publicChat.ts` for public chat    |
| `faculty/`      | Faculty attendance and examination clients                                   |
| `invitations/`  | University admin, staff/faculty membership, and super admin invitations      |
| `platform/`     | Platform identity, institutions, admin lifecycle, and audit                  |
| `registration/` | Institution lookup, account registration, and university onboarding          |
| `shared/`       | Session-expiry events shared across API clients                              |
| `students/`     | Student self-service, class registration, and student workspace clients      |

Keep tests beside their client. Shared test setup belongs in the domain's
`__tests__/` folder and must be imported before the client under test.

Keep each folder within 15 direct files and each code file within 250 physical
lines. Group further by responsibility when approaching either limit.
`npm run check:structure` checks both limits for the services tree.

Client code may depend on shared infrastructure and API contracts in `src/types`.
It must not depend on feature UI components. Internal domain modules should
import their siblings directly, avoiding a dependency back through their entry
module. Keep tokens opaque, backend authorization authoritative, and API failures
consistent with the existing session-expiry behavior.
