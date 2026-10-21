# Student class registration

Registration selects Course (the program's degree type), Branch (the program),
Section (the class code), and Batch (an explicit admission cohort such as
2026–2030). Batch is not inferred from the current academic year. Individual
and bulk registration use the same placement.
Admin and Faculty now share the same registration component and validation/import
workflow. Admin saves use institution-scoped Admin endpoints and `students.create`;
Faculty saves retain the active teaching-assignment and `attendance.manage` checks.

Create batches in **Admin → Academic Setup → Batches → Add record**. Select
the branch/program, enter the admission year (2026) and completion year (2030),
and save the active record. Registration then offers **2026–2030** in its Batch
dropdown for that branch. Use **Refresh batches** after an administrator adds
or changes availability. An empty dropdown explains which setup step is missing.
Batch management uses the existing program-management permission
(`departments.manage`). Branch and cohort years are immutable after creation;
deactivation removes a batch from new selections and preserves existing history.

The new `student_registrations` table stores these pre-account class records.
It does not insert subject attendance rosters, course enrollments, user accounts,
or approvals. Existing subject rosters and academic history are preserved.
Class registrations appear in Students, pending account registrations appear in
Waiting approval, and creation appears in Record history. Subjects are assigned
through the separate academic workflows.

Existing authorized teaching sections provide class scope and access checks.
Sibling subject sections with the same program, academic year, semester, and
section code become one class choice. The section ID in the API path is only an
authorization reference; subject/offering IDs are absent from the saved record.
Academic year and semester preserve that scope independently of admission batch.
Course/branch options require active program metadata.

Apply `supabase/migrations/20261020000000_subject_independent_student_registrations.sql`,
then `supabase/migrations/20261020010000_academic_batches.sql`, before deploying
the new registration API/UI in each environment. Both migrations were applied
to the linked backend Supabase project on 20 October 2026. Live PostgREST checks
of both tables returned HTTP 200, and the batch-management function appeared in
the API schema. The registration migration adds a table with
tenant academic reference checks, institution-level identifier uniqueness, RLS,
and service-role-only read/insert grants. Account approval is resolved from the
existing student identity when displaying registrations.
The batch migration preserves cohorts explicitly saved by the previous registration
flow, adds a batch reference with matching institution/program/year constraints,
and requires an active configured batch for new registrations. It does not infer
admission cohorts from enrollment dates or academic years. Batch writes and audit
entries are committed atomically by a restricted database function.

New individual and bulk registrations require a valid student email. The shared
registration UI defaults **Automatically send invitation emails** to off. With
it off, successful results offer **Send invitations to all** (or a single-student
equivalent) and **Not now**. Only saved students are included. With it on, each
save requests delivery explicitly; delivery failures do not undo a registration.
Invitation retries send email without repeating registration saves.

`20261020020000_student_registration_invitation_delivery.sql` adds a required-email
check for new records without changing historical rows, and service-only delivery
tracking with atomic claim/completion functions. Concurrent requests cannot both
claim a delivery, and a completed real send is not repeated. A request interrupted
while delivery is uncertain remains pending for administrator review rather than
automatically risking a duplicate email. Local captures are labeled as undelivered
and may be retried after real delivery is configured.

Admin invitation requests require `students.create`; Faculty requests require
their existing section-management access and `attendance.manage`. Recipient,
institution, register number and class come from the authorized saved record.
Staff receives no new access. Emails link to the existing public student signup
route using the institution code and `EMAIL_BASE_URL`; the link grants no account,
session, role or approval. The existing email provider sends messages. Development
captures locally, while real delivery requires the configured production provider.

The invitation migration was applied to the linked backend Supabase project on
20 October 2026. A zero-row live PostgREST read of the delivery table returned
HTTP 200, and both claim/completion functions appeared in its API schema. This
verification sent no email and created no student or delivery records. Validation
passed 165 frontend tests, 131 backend tests, and the frontend production build.

For an intentional real inbox test while keeping `ENVIRONMENT=development`,
configure `EMAIL_PROVIDER=mailgun` and `EMAIL_ALLOW_LIVE_IN_DEVELOPMENT=true` in
the private backend environment, along with `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`,
and `EMAIL_FROM`. A sandbox sender must use its actual sandbox domain, such as
`noreply@sandbox123.mailgun.org`; `noreply@yourcollege.edu` is an example for a
future domain owned and verified by the institution. The recipient must first
be added and verified as an Authorized Recipient in Mailgun. Sandbox testing
does not require changing the app to a production environment. Test/testing
still always captures. Without this explicit development flag, development
continues capturing locally. `EMAIL_BASE_URL` controls the registration link;
localhost works only on the computer running the app.

Student invitation failures now show fixed, actionable guidance for provider
authentication (HTTP 401), sending permissions (HTTP 403), missing configuration,
temporary failures, rate limits and unconfirmed delivery. Provider response text,
credentials and student email addresses are excluded from failure diagnostics.
Failed attempts remain retryable without saving the student again.

On 21 October 2026, the local configuration was restored to the existing Mailgun
sandbox and its US endpoint because a custom sending domain was not owned.
The saved API key was preserved. One real test to the previously verified
recipient was accepted by Mailgun with HTTP 200; this confirms provider
acceptance, not inbox delivery. The running backend was reloaded and returned
HTTP 200 after the configuration change. Regression checks passed 89 backend
tests and 5 frontend invitation tests.

Student invitations include an HTML **Complete registration** button and a
copyable URL alongside the plain-text version. Saved names and identifiers are
HTML-escaped. Localhost invitations explain that the app must run on the same
computer and recommend a private browser window if another account is signed
in. The local student-registration URL and public institution lookup were
verified to return HTTP 200. The template and transport changes passed 80
backend tests; the existing frontend registration-link tests also passed.
An email's Gmail authentication warning requires its SPF/DKIM/DMARC results
to diagnose; changing the message template does not resolve authentication.

Student invitation routes now remain on student access when the browser already
has an authenticated account. The page explains the current session and offers
**Sign out and continue** or **Continue with current account**. Signing out uses
the existing session logout, then opens the requested student registration with
the institution code and query preserved. Guests open registration directly;
ordinary student login still opens the dashboard for an existing student session.
No role is inferred or reassigned from the URL. Validation passed 95 frontend
tests covering real authentication-provider transitions and the production build.
