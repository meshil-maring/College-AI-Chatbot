# Permission catalog and bootstrap role matrix

**CAI-RBAC-001 v1.2; DRAFT - REVIEW ONLY; 21 October 2026.** Read the [reading guide](README.md) and relevant role first. Source observations are not live-deployment certification.

This table records presence in `DEFAULT_ROLE_PERMISSIONS`, not effective live access. **Yes** means the code appears in that role's local bootstrap set; **No** means it does not. Every actual operation still needs eligible role, scope, account state, and endpoint policy. Code-only defaults are not a deployment fallback.

Canonical-role bootstrap counts: Student 9; Faculty 18; Staff 19; Admin 60; Super Admin 19. The noncanonical `university_admin` alias has 59 entries. Admin's legacy `platform.manage` entry does not satisfy the independent `super_admin` platform guard. Responsibility-definition grants are not expanded into this table.

| Permission code | Student | Faculty | Staff | Admin | Super Admin |
|---|---|---|---|---|---|
| `profile.own.read` | Yes | Yes | Yes | Yes | Yes |
| `profile.own.update` | Yes | Yes | Yes | Yes | No |
| `notifications.own.read` | Yes | Yes | Yes | No | No |
| `notifications.own.update` | Yes | Yes | Yes | No | No |
| `users.read` | No | No | No | Yes | Yes |
| `users.create` | No | No | No | Yes | Yes |
| `users.update` | No | No | No | Yes | Yes |
| `users.delete` | No | No | No | No | Yes |
| `roles.read` | No | No | No | Yes | Yes |
| `roles.manage` | No | No | No | Yes | Yes |
| `permissions.read` | No | No | No | Yes | Yes |
| `permissions.manage` | No | No | No | Yes | Yes |
| `students.read` | No | Yes | Yes | Yes | No |
| `students.create` | No | No | No | Yes | No |
| `students.update` | No | No | Yes | Yes | No |
| `students.delete` | No | No | No | Yes | No |
| `students.approve` | No | No | Yes | Yes | No |
| `students.reject` | No | No | Yes | Yes | No |
| `students.suspend` | No | No | No | Yes | No |
| `faculty.read` | No | No | No | Yes | No |
| `faculty.create` | No | No | No | Yes | No |
| `faculty.update` | No | No | No | Yes | No |
| `faculty.approve` | No | No | No | Yes | No |
| `faculty.suspend` | No | No | No | Yes | No |
| `staff.read` | No | No | No | Yes | No |
| `staff.create` | No | No | No | Yes | No |
| `staff.update` | No | No | No | Yes | No |
| `staff.approve` | No | No | No | Yes | No |
| `staff.suspend` | No | No | No | Yes | No |
| `departments.read` | No | No | No | Yes | No |
| `departments.manage` | No | No | No | Yes | No |
| `courses.read` | No | No | No | Yes | No |
| `courses.manage` | No | No | No | Yes | No |
| `subjects.read` | No | No | No | Yes | No |
| `subjects.manage` | No | No | No | Yes | No |
| `semesters.read` | No | No | No | Yes | No |
| `semesters.manage` | No | No | No | Yes | No |
| `academic_years.read` | No | No | No | Yes | No |
| `academic_years.manage` | No | No | No | Yes | No |
| `attendance.read` | No | Yes | Yes | Yes | No |
| `attendance.manage` | No | Yes | Yes | Yes | No |
| `attendance.own.read` | Yes | Yes | No | No | No |
| `results.read` | No | Yes | Yes | Yes | No |
| `results.manage` | No | Yes | No | Yes | No |
| `results.own.read` | Yes | Yes | No | No | No |
| `documents.read` | Yes | Yes | Yes | Yes | No |
| `documents.create` | No | Yes | Yes | Yes | No |
| `documents.update` | No | No | Yes | Yes | No |
| `documents.delete` | No | No | No | Yes | No |
| `notices.read` | Yes | Yes | Yes | Yes | No |
| `notices.create` | No | No | Yes | Yes | No |
| `notices.update` | No | No | Yes | Yes | No |
| `notices.delete` | No | No | No | Yes | No |
| `ai.chat` | Yes | Yes | Yes | Yes | No |
| `ai.knowledge.read` | No | Yes | No | Yes | No |
| `ai.knowledge.create` | No | Yes | Yes | Yes | No |
| `ai.knowledge.update` | No | No | No | Yes | No |
| `ai.knowledge.delete` | No | No | No | Yes | No |
| `ai.configuration.manage` | No | No | No | No | No |
| `institution.read` | No | No | No | Yes | No |
| `institution.update` | No | No | No | Yes | No |
| `institution.settings.manage` | No | No | No | Yes | No |
| `organizations.manage` | No | No | No | Yes | No |
| `faculty.assignments.read` | No | Yes | No | No | No |
| `faculty.assignments.manage` | No | No | No | Yes | Yes |
| `institutions.read` | No | No | No | No | Yes |
| `institutions.create` | No | No | No | No | Yes |
| `institutions.update` | No | No | No | No | Yes |
| `institutions.delete` | No | No | No | No | Yes |
| `platform.read` | No | No | No | No | Yes |
| `platform.manage` | No | No | No | Yes | Yes |
| `platform.settings.manage` | No | No | No | No | Yes |
| `platform.audit.read` | No | No | No | No | Yes |
| `audit.read` | No | No | No | Yes | Yes |
| `academic.class.read` | No | No | No | No | No |
| `academic.department.read` | No | No | No | No | No |
| `academic.reports.read` | No | No | No | No | No |
| `attendance.overview.read` | No | No | No | No | No |
