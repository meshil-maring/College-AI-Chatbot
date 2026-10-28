# Frontend working guide

Read [STRUCTURE.md](docs/STRUCTURE.md) for module ownership and [ROUTES.md](docs/ROUTES.md)
for routes. Start with the relevant feature and its adjacent tests instead of
loading every workspace into context.

Follow [DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) for visual changes: shared colors,
typography, spacing, component states and responsive behavior.

- Before creating a file, follow the [shared project rules](../AGENTS.md): inspect
  the existing structure, search for reusable code, and choose the owning feature.
- Keep each folder at or below 15 directly contained, project-maintained files.
  If the destination already exceeds 15 files, or a new file would exceed the
  limit, group related files into descriptive subfolders before adding it.
  Apply the same limit to every resulting subfolder.
- Keep frontend guides in `docs/` and local verification logs in the repository
  `logs/frontend/` folder. Create that log folder before redirecting output; keep
  ad hoc logs and reports out of the frontend root.
- Keep source, tests, styles, and scripts at or below 250 physical lines.
  Split by responsibility before reaching the limit; do not compress statements
  or remove useful comments just to pass the check.
- Keep screen state and request handling in feature hooks. Keep rendering in
  focused components, with helpers and types beside their owning feature.
- Share code across features only when it has multiple consumers. API transport
  belongs in `services`; API contracts belong in `types`.
- Keep service clients and their tests inside the domain folders listed in the
  [services guide](src/services/README.md). Preserve exported contracts when
  moving modules; update all callers and mock paths instead of leaving aliases
  in the services root. Type entry files remain public facades.
- Keep feature tests adjacent to the screen. Shared test fixtures and mock setup
  belong in `__tests__`, which is excluded from the production TypeScript build.
  Import mock setup before importing the component under test. Keep
  `vi.hoisted` declarations local and export their values separately.
- Keep auth screens, state, and tests in the workflow folders listed in the
  [auth guide](src/features/auth/README.md). The auth root contains its guide
  and workflow folders; update imports and mocks when moving auth modules.
- Keep faculty screens and tests in the workflow folders listed in the
  [faculty guide](src/features/faculty/README.md). Attendance and student
  subfolders group state, UI, and registration code by responsibility.
- Keep student self-service pages and tests in the domain folders listed in the
  [student guide](src/features/student/README.md). The workspace composes those
  pages; shared UI and resource state belong in `student/shared/`.
- Preserve authentication generation guards, identity keys, cancellation checks,
  and server-authoritative permissions when extracting hooks or components.
- Preserve CSS rule order when splitting stylesheets. Entry stylesheets import
  the smaller files in cascade order.
- Do not edit `features/auth/access/rbacPolicy.generated.ts` directly; use the existing backend RBAC
  generator when policy changes are required.

From `frontend`, run `npm run check:structure`, `npm run build`, and `npm test`.
Use `npx prettier --write <changed-files>` to format focused edits.
The validator checks file length and the 15-file limit throughout `src/services`,
`src/features/auth`, `src/features/faculty`, and `src/features/student`.
Review direct file counts in other affected folders against the same shared rule.
