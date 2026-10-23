# Student information workspace

| Folder                       | Current responsibility                                                   |
| ---------------------------- | ------------------------------------------------------------------------ |
| `workspace/`                 | Shell, navigation, approval/inactive-account gates and session lifecycle |
| `profile/`                   | Read-only identity profile using `GET /students/me/profile`              |
| `notices/`, `resources/`     | Published institution information                                        |
| `shared/`                    | Resource loading, access-denial context, section UI and formatting       |
| `integration/`, `__tests__/` | Information journeys, navigation and fixture support                     |

The shell loads account approval once and reuses the same identity result on the
profile page. Pending, rejected and inactive accounts cannot mount student views.
The shared ChatShell owns the assistant, and AuthProvider owns session lifecycle.

Attendance, results and subject-package pages have been removed. The former
academic dashboard, its historical tests and `shared/AcademicContextCard.tsx`
remain as disconnected source at the owner's request. Their dependencies include
retired contracts; they are excluded individually from the active TypeScript
project and Vitest suite. See the [removal record](../../../../docs/retirements/academic-setup/README.md).

Keep API transport in `services/students/`, contracts in `types/student.ts`, state
in feature hooks and rendering in components. Preserve identity scopes, access
denials, retries, query lifetime and server-authoritative permissions. Keep tests
adjacent, fixture setup in `__tests__/`, files within 250 physical lines and
folders within 15 direct files. `check:structure` also rejects active imports into
retained legacy source; those files remain subject to maintenance limits.
