# Frontend services

Keep API clients, transport helpers and tests in the owning domain. The services
root contains this guide and domain folders. Update callers, contracts and test
mocks together when moving code.

| Folder          | Responsibility                                                                    |
| --------------- | --------------------------------------------------------------------------------- |
| `admin/`        | Account approvals, institution identity, knowledge, communication and permissions |
| `auth/`         | Authentication, session operations and development authentication status          |
| `chat/`         | Authenticated conversations and public institution chat                           |
| `invitations/`  | Administrator and staff/faculty account invitations                               |
| `platform/`     | Institutions, administrator lifecycle and audit                                   |
| `registration/` | Institution lookup, account registration and onboarding                           |
| `shared/`       | Session-expiry events                                                             |
| `students/`     | Identity profile, notices and resources                                           |

Academic catalogue, curricula/packages, faculty teaching, roster registration,
attendance and result clients have been removed. Do not reconnect retained legacy
screens to retired endpoints; see the [removal record](../../../docs/retirements/academic-setup/README.md).

Keep each folder within 15 direct maintained files and each source/test file
within 250 physical lines. `npm run check:structure` checks both service limits.
Client modules depend on contracts and shared infrastructure, never feature UI.
Keep tokens opaque, authorization on the server and session-expiry behavior
consistent across clients.
