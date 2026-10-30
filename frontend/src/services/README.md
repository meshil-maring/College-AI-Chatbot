# Frontend services

Keep API clients, transport helpers and tests in the owning domain. The services
root contains this guide and domain folders. Update callers, contracts and test
mocks together when moving code.

| Folder          | Responsibility                                                                           |
| --------------- | ---------------------------------------------------------------------------------------- |
| `admin/`        | Account approvals, institution identity, knowledge, communication and permissions        |
| `academics/`    | Curriculum choices, semester assignment and student course registration                  |
| `auth/`         | Authentication, session operations and development authentication status                 |
| `chat/`         | Authenticated conversations and public institution chat                                  |
| `invitations/`  | Administrator and staff/faculty account invitations                                      |
| `knowledge/`    | Shared learning resource library, drafts, staged file uploads, indexing retry and review |
| `platform/`     | Institutions, administrator lifecycle and audit                                          |
| `registration/` | Institution lookup, account registration and onboarding                                  |
| `shared/`       | Session-expiry events                                                                    |
| `students/`     | Identity profile, notices and resources                                                  |

`admin/academics.ts` owns department, degree-program, academic-year, dated-semester,
course, program-course, offering and section reads/writes. Descendant
`institution_id` values are server-derived API context. Faculty teaching,
attendance, results and retired academic packages remain removed. Do not reconnect retained legacy
screens to retired endpoints; see the [removal record](../../../docs/retirements/academic-setup/README.md).

`admin/academicStructure.ts` owns the additive program-semester, curriculum-version,
curriculum-subject, admission-cohort, academic-section and academic-offering API.
Its contracts live in `types/academicStructure.ts`. It uses the same authenticated
transport, session-expiry events and server-selected tenant context.

`academics/semesterRegistration.ts` owns the additive administrator option-group
and assignment endpoints and student own-semester reads/completion. It reuses the
authenticated transport with cancellation and token-scoped expiry. Its contracts
live in `types/semesterRegistration.ts`; all tenant and ownership context comes
from the server rather than student write bodies.

Keep each folder within 15 direct maintained files and each source/test file
within 250 physical lines. `npm run check:structure` checks both service limits.
Client modules depend on contracts and shared infrastructure, never feature UI.
Keep tokens opaque, authorization on the server and session-expiry behavior
consistent across clients.

`knowledge/resources.ts` uses the established authenticated transport in
`admin/http.ts`, including token-scoped expiry and optional read cancellation.
It targets the shared knowledge API; no admin route is opened to other roles.

`chat/publicChat.ts` sends the narrow anonymous contract without browser credentials.
Its deadline covers response-body parsing as well as fetch. Safe error types retain
bounded Retry-After metadata for explicit retry controls; no automatic write retry
or authenticated recovery request is added to public chat.
