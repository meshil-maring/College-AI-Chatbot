# Student transfers

Students request a move from their current-term section to another section.
A **section transfer** stays in the same batch; a **program transfer** moves to
a section of another program in the same term. Moving to another batch of the
same program is not handled here.

## Source of truth

`student_semester_registrations` remains the only record of where a student is.
Approving a request reassigns the student's current-term registration (the latest
term, as in the student directory) to the target section in one transaction:

1. re-checks that the student is still in the original section, that the term is
   open, that the target is active and has a free seat;
2. copies the previous registration and enrolled subjects onto the request;
3. removes the enrolments of the old section's offerings and resets the
   registration to `assigned`, so the student registers subjects again.

The request row (from/to section and program, previous registration and subjects)
and `student_transfer_events` form the placement history.

## Who decides

- Students (`transfers.request`, `transfers.read`) submit, view and cancel their own
  requests. One open request per student.
- Institution administrators (`transfers.read`, `transfers.approve`) review and
  decide every request.
- A Head of Department decides requests **into** the department they head. HOD is
  not a role: an administrator appoints one active faculty member per department
  (`department_heads`, managed with `departments.manage`). Ending or replacing an
  appointment keeps the earlier row. A faculty member who loses their faculty grant
  loses HOD authority immediately.

Rejection requires a reason. Reviewers may first mark a request `under_review`.

## Other changes

- `assign_student_semester` now compares a new assignment's batch with the student's
  current placement instead of every past registration, so a transferred student
  can be assigned to later terms of the new batch.
- The superseded `20261107000000_student_academic_transfers` draft tables are
  dropped. The migration stops if any of them contains rows.

Generate with `python scripts/maintenance/student_transfers/build_migration.py`;
use `--check` to verify parity. Generation does not deploy SQL.
