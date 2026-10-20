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
