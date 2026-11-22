# Student transfers

Students move between sections of the current term:

- **Section transfer:** another section of the same batch and program.
- **Program transfer:** a section of a different program in the same term.

Moving to another batch of the same program is not handled here.

## Migrations

| Version | Name | Adds |
| --- | --- | --- |
| `20261121000000` | `student_transfer_workflow` | Requests, review queue, HOD appointments, permissions |
| `20261122000000` | `student_transfer_direct` | Admin/HOD direct transfers and the shared placement move |
| `20261123000000` | `student_transfer_same_semester` | Same-semester rule and the admin override |
| `20261124000000` | `student_transfer_notifications` | Student notifications for transfer outcomes |
| `20261126000000` | `department_co_heads` | Several equal HODs per department; one HOD may head several departments |

Applied migrations never change; new behaviour is a new entry in `follow_ups`
(`manifest.json`) with its SQL in a subfolder. Generate everything with
`python scripts/maintenance/student_transfers/build_migration.py`; `--check`
verifies parity. Generation never deploys SQL.

The superseded `20261107000000_student_academic_transfers` draft created tables
no code could write to. `20261121000000` drops them only while empty, and the
draft is recorded as applied on hosted projects so it never runs again. The
draft file is now an empty, documented no-op: its tables referenced
`public.subjects` and `public.academic_batches`, which no longer exist after
`20261026000000`, so it blocked every fresh local replay.

## Source of truth

`student_semester_registrations` is the only record of where a student is. Every
approved transfer runs `transfer_apply` in one transaction, which:

1. re-checks that the student is still in the original section, the term is open,
   the target is active, the semester rule holds and a seat is free;
2. copies the previous registration and enrolled subjects onto the request;
3. removes the old section's subject enrolments and resets the registration to
   `assigned`, so the student registers subjects again.

The request row and `student_transfer_events` form the placement history.
`assign_student_semester` compares a new assignment's batch with the student's
current placement, so a transferred student can be assigned to later terms.

## Who does what

| Actor | Can |
| --- | --- |
| Student (`transfers.request`, `transfers.read`) | Request, view and cancel their own transfers; one open request at a time |
| Administrator (`transfers.read`, `transfers.approve`) | Review every request; transfer any student directly |
| Head of Department | Review requests into every department they head; transfer students directly only between sections of those departments |

HOD is an appointment, not a role: an administrator appoints active faculty
members as heads (`department_heads`, managed with `departments.manage`). Since
`20261126000000` a department may have several equal heads and one faculty member
may head any number of active departments in the institution; the only rule is one
current appointment per person per department. Every current head of a department
may review its requests, and the first decision counts. `add_department_head` and
`end_department_head` change one appointment; `assign_department_head` still
replaces all heads with one (or removes all). Ended appointments keep their row,
and every change is audited. A faculty member who loses their faculty grant loses
HOD authority immediately.

- Rejection requires a reason. Reviewers may first mark a request `under_review`.
- A direct transfer applies immediately, with no approval step. It is refused while
  the student has an open request; that request must be decided first.
- `initiated_by` records who started each transfer (`student`, `admin`, `hod`).

## Same-semester rule

Every transfer keeps the student's semester number (Semester 5 → Semester 5),
checked by `transfer_stage_matches`. Only an administrator's direct transfer may
override it, with `allow_other_semester` set explicitly. The override is stored
as `semester_override`, shown in history and written to the audit log.

## Notifications

A trigger on `student_transfer_requests` writes to `student_notifications` when a
request moves to review, or when any transfer is approved or rejected. A student's
own cancellation sends nothing. The existing unique index keeps one message per
step: review start uses `academic_admin`, the final outcome `academic_status`.

## Errors

| Code | Meaning |
| --- | --- |
| `P1101` | Request already closed |
| `P1102` | Student's section changed since the request |
| `P1103` | Current term closed |
| `P1104` | Target section unavailable |
| `P1105` | Target section full |
| `P1106` | Student already has an open request |
| `P1107` / `P1112` | Student has no current section |
| `P1108` | Reason must be 10–2000 characters |
| `P1109` | Rejection needs a reason |
| `P1110` | Invalid Head of Department appointment |
| `P1111` | Direct transfer blocked by an open request |
| `P1113` | Semester number differs without an admin override |
