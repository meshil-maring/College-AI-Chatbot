# Semester registration

This additive migration connects the existing versioned curriculum, batch-owned
academic sections and academic offerings to actual student registration. It does
not reuse or restore the retired academic-package tables or endpoints.

For the B.Tech CSE Semester 3 example, create eight reusable subjects and map all
eight to the same draft curriculum and program semester. Mark DSA and OOP as
Required. Leave the six alternative subjects optional. Under Curriculum → Subject
Options, create one group with Option 1 containing Digital Logic, Discrete Maths
and Computer Organization; Option 2 contains DBMS and the two laboratories.
Students must choose exactly one option, including every subject in that option.

Publish the curriculum, assign it to a batch, create a section for Semester 3 and
the dated term, and create academic offerings for all subjects available there.
Under Sections → Manage Student Enrollment, assign an approved active student.
The student then opens Semester Registration to select an available option.
The server automatically enrolls the student in the two common subjects and all
three option subjects within one transaction. No subject list is trusted from
the browser. Exact retries are idempotent; a different completed choice is denied.

Curriculum groups can be edited or deleted only while their version is draft.
One subject may appear in several alternatives of the same group, but cannot
belong to different groups. Group membership requires active optional mappings
from that exact curriculum and semester. Published groups remain preserved.

An administrator needs Courses read/manage and Students read/update to assign
students. Student reads and writes use the separate registration.own.read/manage
grants, an exact institution student role, approval, active ancestry and ownership.
Tables deny browser access and service-role direct writes. Trusted backend RPCs
repeat authorization and hold the existing tenant academic advisory lock.
Section assignment reserves section capacity. Registration checks every subject
offering and its capacity atomically. A failed registration leaves no enrollment
rows. Registered subjects retain name, code and credit snapshots.

This first workflow supports one section per student per dated term and preserves
the original batch across terms. Registered selections cannot be edited, cancelled
or transferred here; those actions require an explicit future academic workflow.
Registration is allowed before and during a teaching term, and closes after its
end date. Dedicated opening/closing dates and academic prerequisite or credit
limits are not configured by this migration.

Generate with `python scripts/maintenance/migrations/build_semester_registration.py`;
use `--check` to verify parity. Generation does not deploy SQL. Review target
migration history before applying only this forward migration.

Run `python scripts/validation/semester_registration/run.py` for a full migration
replay and fictional registration contracts in an owned local PostgreSQL container.
The runner has no network or persistent mounts and removes its own container.
Keep output under `logs/backend/`.
