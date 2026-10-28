# Authentication API

`auth.py` assembles the core authentication routes. Each feature owns its
handlers; request models live in `app/schemas/auth/auth.py`.

| Module | Responsibility |
| --- | --- |
| `auth.py` | Router composition and the shared `auth` tag |
| `signup.py` | Provider signup and signup-specific password validation |
| `login.py` | Email login, account eligibility and pending registration responses |
| `password_recovery.py` | Recovery emails, recovery-session freshness and single-use password reset |
| `password_change.py` | Current-password verification, password changes and revoking other sessions |
| `sessions.py` | Refresh, current-session logout and global logout |
| `common.py` | Provider dependencies, security hooks, session response validation and feature router factory |
| `../../schemas/auth/auth.py` | Request schemas, strict input fields and password length constraints |
| `student_auth.py` | Student login by email or institution-scoped academic identifier |
| `registration.py` | Student account registration |
| `users.py` | Student/faculty/staff registration |
| `identity.py` | Identity bootstrap; admin institution codes come from the server-resolved tenant via `services/auth/identity.py` |
| `dev_auth.py` | Development/test password tools, protected by their existing environment and role guards |

## Shared boundaries

Core features call `common.create_feature_router()` to put `/auth` on their
route templates. The assembler includes each feature once and adds the `auth`
tag. `app/main.py` continues to register the core router and the separate
student, registration and development routers.

Provider clients and security-event/rate-limit hooks are accessed through
`common`. Supabase Auth remains the credential authority; these modules reuse
the existing account eligibility and recovery-session services.

Login and refresh share `common.session_payload` so both require usable provider
access and refresh tokens. Password reset still requires a recent provider
recovery session and consumes it once. Password change still verifies the
current credential and revokes other sessions. Protected handlers retain their
`get_current_user` dependency; public handlers retain their existing rate limits.

## Adding or testing a route

Add a handler to its feature module. For a new core feature, use the common
router factory and include it in `auth.py`; add request models to
`app/schemas/auth/auth.py`. Keep provider/account orchestration in the appropriate
existing services.

Tests patch shared provider dependencies and security hooks on
`app.api.auth.common`, and patch account repositories/services directly.
The assembler exports its router rather than handler implementation details.
Historical phase reports may refer to the previous monolithic file.
