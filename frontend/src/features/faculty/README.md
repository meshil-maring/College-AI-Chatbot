# Faculty workspace

`workspace/FacultyShell.tsx` composes the identity profile, existing notices and
resource placeholders, and the shared chatbot. `facultyRoutes.ts` owns direct
links and browser navigation; `facultyNavigation.ts` applies server identity and
permission visibility. Endpoints enforce authorization independently.

Teaching assignments, academic responsibilities, student rosters, attendance,
assessment and package workflows have been removed. The former dashboard source
and its historical test remain at the owner's request and are disconnected from
the shell. See the [removal record](../../../../docs/retirements/academic-setup/README.md).

Keep profile UI in `profile/`, shell/routes in `workspace/`, and tests adjacent
to the workflow. Keep each folder within 15 maintained files and each code file
within 250 physical lines. `npm run check:structure` enforces both limits and
rejects active imports into retained legacy source. Preserve server-authoritative
identity, cancellation, session handling and tenant boundaries when moving code.
