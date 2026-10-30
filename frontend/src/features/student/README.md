# Student information workspace

| Folder                       | Current responsibility                                                   |
| ---------------------------- | ------------------------------------------------------------------------ |
| `workspace/`                 | Shell, navigation, approval/inactive-account gates and session lifecycle |
| `profile/`                   | Read-only identity profile using `GET /students/me/profile`              |
| `registration/`              | Assigned semesters, complete subject options and atomic course registration |
| `notices/`, `resources/`     | Published institution information                                        |
| `shared/`                    | Resource loading, access-denial context, section UI and formatting       |
| `integration/`, `__tests__/` | Information journeys, navigation and fixture support                     |

The shell loads account approval once and reuses the same identity result on the
profile page. Pending, rejected and inactive accounts cannot mount student views.
The shared ChatShell owns the assistant, and AuthProvider owns session lifecycle.
The resources page also uses the shared Ask AI eligibility button and resource
chat view. Its metadata API still exposes no file/storage fields or downloads.

Attendance, results and subject-package pages have been removed. The former
academic dashboard, its historical tests and `shared/AcademicContextCard.tsx`
remain as disconnected source at the owner's request. Their dependencies include
retired contracts; they are excluded individually from the active TypeScript
project and Vitest suite. See the [removal record](../../../../docs/retirements/academic-setup/README.md).

The replacement Semester Registration page uses the additive academic workspace
and its own API, never retired package endpoints. Its query factories include the
session generation, user, role, institution and sorted permission scope; keyed
sessions discard drafts and ignore late mutations after identity replacement.
Students need registration.own.read/manage grants, approval and an administrator
section assignment. Complete selections include common required subjects and all
subjects in exactly one option per group. Registered subject snapshots remain
visible after confirmation. Backend and SQL enforce every enrollment rule.

Keep information transport in `services/students/` and registration transport in
`services/academics/`; contracts live in `types/student.ts` and
`types/semesterRegistration.ts`. Keep state
in feature hooks and rendering in components. Preserve identity scopes, access
denials, retries, query lifetime and server-authoritative permissions. Keep tests
adjacent, fixture setup in `__tests__/`, files within 250 physical lines and
folders within 15 direct files. `check:structure` also rejects active imports into
retained legacy source; those files remain subject to maintenance limits.
