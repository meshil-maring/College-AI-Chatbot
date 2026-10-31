# Calendar and class-section deletion

The service-only `delete_unused_academic_calendar_record` RPC permits only
academic years, dated semesters and cohort-owned academic sections. Exact active
institution-admin grants use `academic_years.manage`, `semesters.manage` and
`courses.manage` respectively. Semester institution ownership is derived through
its year; missing and foreign IDs return the same not-found error.

Current years/semesters cannot be deleted. Select their replacement first. Every
foreign-key dependency blocks deletion, including inactive/historical semesters,
curricula, batches, offerings, subject mappings, class sections and student
assignments/registrations. No linked records are deleted or detached. Future
cascade/set-null dependencies also block. Tenant advisory and parent row locks
serialize writes, and deletion commits atomically with its before-image audit.

The existing offering-owned legacy sections remain separate and have no new
DELETE endpoint. Account identities and academic history are preserved.

Generate with `python scripts/maintenance/migrations/build_calendar_section_deletion.py`;
add `--check` for parity. Generation never applies SQL. Deploy this forward
migration in normal order before using the new delete actions.
