# Authentication feature

Keep auth UI, state, permissions, and tests in their owning workflow folder.
The auth root contains this guide and the workflow folders; import a module
directly from its workflow, and update mock paths when moving code.

| Folder          | Responsibility and entry points                                                                      |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| `session/`      | `AuthProvider.tsx`, context, browser storage, restore, renewal, cross-tab events, login/logout state |
| `login/`        | `LoginForm.tsx`, login audience selection, and form validation tests                                 |
| `password/`     | Password fields, change-password form, recovery, and reset screens                                   |
| `registration/` | `RegistrationForm.tsx`, university onboarding, institution lookup, fields, and confirmation          |
| `access/`       | Server-resolved permission helpers, the permissions hook, and the generated RBAC reference           |

Keep tests beside their screen or helper. Shared test setup belongs in the
workflow's `__tests__/` folder and must be imported before the component under
test. Preserve that import order when editing or formatting tests.

Each folder must stay within 15 direct maintained files; code files must stay
within 250 physical lines. `npm run check:structure` checks both limits here.
Group further by responsibility before exceeding either limit.

HTTP clients belong in `src/services/auth/` or `src/services/registration/`.
Auth UI modules may consume those clients and shared API contracts; service
clients must not import feature UI code.

Preserve session generation guards, token-scoped expiry handling, and canonical
server identity when extracting hooks. Permission checks render available UI;
the backend authorizes requests and determines effective grants.
The context exposes a session generation that remains stable through local token
renewal. Academic drafts use it together with the user, institution and permission
identity, so renewal preserves entries while a replacement login clears them.

Do not edit `access/rbacPolicy.generated.ts` by hand. From `backend/`, run
`python scripts/generate_frontend_rbac.py` to regenerate it and rerun the command
with `--check` to verify the snapshot.
