# Design system adoption

The active frontend uses the [Academic Setup design system](DESIGN_SYSTEM.md).
This is a presentation change; authentication, permission checks, institution
boundaries, API contracts and existing record workflows remain owned by their
current features.

## Screen coverage

| Area                                  | Applied style                                                                            |
| ------------------------------------- | ---------------------------------------------------------------------------------------- |
| Administration                        | Shared dark sidebar, yellow selection, header and page title/description                 |
| Profile                               | Consistent identity panels, field labels and supporting text                             |
| Academic Setup                        | Canonical tokens across overview, all entity pages, forms, drawers and tables            |
| Staff & Faculty                       | Membership requests, filters, roster and actions                                         |
| Student Approvals                     | Shared approval queue presentation and controls                                          |
| Notices, Documents, FAQs              | Standard panels, forms, actions and error states                                         |
| Shared Learning Resources             | One admin/faculty/staff library, audience form, staged files, review and modal lifecycle |
| Staff Permissions                     | Consistent selectors, checkbox accents, grant actions and messages                       |
| Staff and Faculty portals             | Shared workspace frame, profile and information states                                   |
| Student portal                        | Shared sidebar/header, approval gate, profile, notices and resources                     |
| Platform Administration               | Shared responsive frame, institution management, invitations and audit                   |
| Public entry and institution gateways | Neutral panels, yellow actions, consistent type and gutters                              |
| Authentication and invitations        | Sign-in, registration, recovery, reset and account security controls                     |
| AI assistants                         | Workspace-sized chat, neutral speaker bubbles, reading type and yellow send actions      |

## Implementation ownership

- `src/styles/tokens.css`: CSS properties and matching semantic Tailwind colors,
  type roles, radii and overlay shadow. Legacy academic variables alias these values.
- `src/styles/base.css`: shared font, native controls, focus, tables and reduced motion.
- `src/styles/components.css`: shared actions, panels, page header and chat layout.
- `features/workspace/`: the frame and styles consumed by all authenticated roles.
- Feature styles retain local layout and responsive record/card rules. Academic
  dialogs share `workspace/useWorkspaceDialog.ts` with resource drawers and retain identity-safe state.
- Notice form rendering/state lives in `admin/notices/NoticeForm.tsx` to keep the
  manager focused and both files within the source-size limit.

The font uses the shared Inter/system stack. Inter is not bundled; the same system
fallback applies throughout. Institution gateway logos and supplied brand metadata
continue to come from the institution. Retained, disconnected historical source
is not an active screen and has not been reintroduced into the application.

## Verification

Run structure validation, the production build and the full frontend test suite.
Browser review should cover public/auth pages, all role shells, each administrator
section, academic drawers, narrow layouts, keyboard focus and reduced motion.
Browser fixtures intercept API requests locally; they do not authenticate against
or write to a real institution. Logs and screenshots belong in repository-level
`logs/frontend/`, with design rollout evidence under the `design-rollout` prefix.
