-- Student Academic Experience & Performance — read-path indexes ONLY.
--
-- The student-facing read layer resolves the authenticated student's own
-- academic footprint through two existing lookups that currently have NO
-- supporting index, which would force an institution-wide sequential scan on
-- every student dashboard request:
--
--   1. faculty_attendance_rosters(linked_student_id)
--      -> "the rosters this one student belongs to"
--         (existing identity link maintained by roster reconciliation);
--   2. faculty_attendance_records(roster_id)
--      -> "this one student's attendance marks".
--
-- This migration is strictly additive: no table, column, constraint,
-- foreign key, trigger, policy or privilege changes. Row Level Security
-- stays exactly as configured by the Faculty Attendance migrations, and the
-- service-role-only read path is unchanged. Existing indexes are preserved.
--
-- Per-student subject-attendance aggregation, upcoming-assessment lookup
-- (idx on faculty_tests(institution_id, section_id, scheduled_date)),
-- legacy attendance (idx_student_attendance_student_id) and published
-- results (idx_test_results_student_id / idx_test_results_student_conducted)
-- already have covering indexes and need no change here.

CREATE INDEX IF NOT EXISTS idx_faculty_attendance_rosters_linked_student
    ON public.faculty_attendance_rosters (linked_student_id)
    WHERE linked_student_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_faculty_attendance_records_roster
    ON public.faculty_attendance_records (roster_id);
