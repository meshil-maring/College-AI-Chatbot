# Normalization, functional dependencies, and data duplication

Status: source assessment. See the [audit summary](README.md) for scope and
limitations. Table names and constraints below describe local migrations,
not a queried live catalog or measured data-cleanliness result.

## Assessment method

Normalization depends on business facts and all candidate keys, not simply on
whether a table has a UUID primary key. Interpret dependencies in the context
of current foreign keys and validation triggers, and distinguish operational
facts from retained historical snapshots.

- **1NF:** represent individual relationship facts without repeating subject
  columns or operational subject lists whose members require separate rules.
- **2NF:** non-prime attributes must depend on the whole of every candidate key;
  a generated surrogate key does not remove dependencies on natural-key subsets.
- **3NF:** a nontrivial dependency must have a superkey determinant or a prime
  dependent attribute. Watch context facts reached through non-key references.
- **BCNF:** determinants must be superkeys. No blanket BCNF claim is possible
  while the controlled dependencies below remain.
- **4NF/5NF:** a full certification needs agreed multivalued/join dependencies.
  Keep independent subject membership, faculty assignment, package availability,
  and student placement relationships separate to avoid accidental cross-products.

## Existing relationship inventory

| Relation | Key/relationship evidence | Assessment |
| --- | --- | --- |
| Departments | Institution plus normalized code. [Master indexes](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L6). | Reusable department facts; keep institutional identity. |
| Programs and subjects | Department plus normalized code. [Indexes](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L7). | Program is degree/branch; subject belongs to its owning department. |
| Dated semesters | Year-owned term with number/code. [Definition](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L470). | Does not separately model a student's degree stage. |
| Program curriculum | Unique program/subject pair, optional dated semester, classification and required flag. [Key](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L675). | Individual links, not a named curriculum/version or package. |
| Offerings | Unique subject/program/year/term; FK to program/subject curriculum pair. [Key](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L560), [FK](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L868). | Real scheduled occurrences; preserve these references. |
| Teaching sections | Unique normalized section code within an offering. [Index](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L11). | Subject teaching group, not a batch-specific shared class. |
| Batches | Program/admission-year cohort, plus tenant. [Definition](../../../../supabase/migrations/20261020010000_academic_batches.sql#L4). | Explicit admission data; distinct from academic year. |
| Registrations | Unique institutional register/roll, with one class/period and batch context. [Definition](../../../../supabase/migrations/20261020000000_subject_independent_student_registrations.sql#L4). | Persistent identity/admission and fixed placement currently combined. |
| Subject rosters | Unique institutional section/register and optional roll, linked account optional. [Definition](../../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L5). | Per-subject participation and pre-account identity snapshots. |
| Attendance | Session/roster result, plus section/date session uniqueness. [Definition](../../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L30). | Separate relationship/event facts; historical identities matter. |

## 1NF assessment

The inspected academic model stores one subject relationship per row. No
`subject_1`/`subject_2` columns or CSV package list was found in this model.

Import raw data, source metadata, imported summaries, validation errors, and
before/after audit JSON are workflow/provenance records. Their use of JSON is
not by itself a normalization failure. They must not become the sole source
for operational package membership, permission scope, or subject eligibility.

The new collection must have one package-subject relationship per member, with
foreign keys and uniqueness. An API can transport a list, but storage and
enforcement must still identify each subject and its curriculum scope.

## 2NF / 3NF: controlled context redundancy

The following dependencies are supported by source constraints/triggers.
They expose partial or transitive dependencies; they do not prove bad data.

| Dependency | Repeated value and normal-form implication | Current safeguard |
| --- | --- | --- |
| `semester_id -> academic_year_id` | Offering year depends on the semester subset of the implied minimal subject/program/term natural key; strict 2NF/3NF is not uniform. | [Composite semester/year FK](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L878). |
| `program_id -> department -> institution` | Batch tenant repeats a program-derived fact; the minimal cohort key can omit tenant under this dependency. | [Tenant/parent guard](../../../../supabase/migrations/20261020010000_academic_batches.sql#L18). |
| `batch_id -> program, institution, start_year, end_year` | Registration repeats cohort facts alongside batch reference, creating non-key dependencies. | [Composite batch FK](../../../../supabase/migrations/20261020010000_academic_batches.sql#L53); batch identity is immutable. |
| `section_id -> offering -> semester/year/tenant` | Roster offering/term/tenant depend on section, a subset of its effective section/register natural key. | [Roster context trigger](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L10). |
| `section_id -> offering/tenant` | Attendance sessions use section/date uniqueness while repeating section-derived context. | [Session key](../../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L30) and context trigger above. |

These are deliberate integrity/query-scope redundancies. State the authority
for each copy and retain a composite FK or authoritative trigger wherever it
remains. Application filtering alone is insufficient for redundant tenant data.
Removing tenant fields without replacing their guards would weaken isolation.

## Duplication that needs a design decision

### Identity copies and snapshots

Registration and each subject roster retain names, identifiers, email, and
other pre-account information. Assignment explicitly copies registration values:
[assignment service](../../../../backend/app/services/students/subject_assignments.py#L83).
Pre-account rosters make this purposeful, rather than redundant student accounts.

Account reconciliation updates account linkage/status, but it is not a general
synchronizer for every copied display field:
[reconciliation](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L294).
Different names/emails are therefore possible without a defined snapshot versus
canonical-display policy. No actual disagreement was measured.

Choose immutable source snapshots versus current canonical identity explicitly.
New memberships need stable placement/registration provenance; package revisions
should reference that identity instead of copying another independent student.

### Repeated class context

Current class scope repeats program/year/dated term/section code across teaching
sections and registrations. Optional batch filtering in list reads is different
from an authoritative batch-aware class identity. See
[class reads](../../../../backend/app/services/students/student_registrations.py#L103)
and [exact assignment lookup](../../../../backend/app/repositories/students/subject_assignments.py#L6).
Introduce explicit shared class relationships; do not collapse rows using code
or student name equality.

### Subject classification and credit facts

The current type belongs to the program-subject relationship. Keep classification
on the curriculum-subject relationship so one subject can be core in one plan
and elective in another. Do not copy it independently into every package member.

Existing subject credits and any curriculum-specific credit overrides need one
declared source of truth. An override is a separate policy decision; cached
totals or result snapshots must not become competing editable credit masters.

## Proposed normalized relationship direction

These are conceptual responsibilities, not approved table names or SQL.

| Relationship | Required uniqueness / compatibility |
| --- | --- |
| Curriculum -> version -> study semester -> subject membership | One authoritative curriculum-subject/classification fact per applicable study semester; preserve any legitimate repeated-study policy. |
| Package -> curriculum-subject membership | No duplicate member and no foreign curriculum/version/study-semester reference. Package lifespan remains a product decision. |
| Shared class -> program/batch + dated term + study semester + curriculum version | One explicit class identity; enforce matching batch/program/tenant and term/year ancestry. |
| Student identity/admission -> temporal class placement | Distinguish persistent register identity from each class/period placement; define nonoverlap and progression rules. |
| Class -> available package version | Unique availability and selection code in a defined scope; references carry authority, not parsed labels. |
| Class + subject -> offering / teaching group | Prevent ambiguous duplicate mappings; explicitly decide legitimate shared teaching groups. |
| Placement -> package assignment -> revision | One active package per agreed scope; immutable revision history, retry identity, and stale-request protection. |
| Placement + subject participation -> effective episodes/provenance | Reuse shared core membership and historical roster IDs; separately track why membership is required and when it applies. |

Normalize operational facts first. Where performance or tenant enforcement
justifies a repeated attribute, document the dependency, source, consistency
constraint, and mutation path rather than claiming strict 3NF.

## Data quality that remains unmeasured

The live audit must count, rather than expose student details: exact and
normalized-code duplicates; academic ancestry mismatches; conflicting cohort
copies; ambiguous shared-section groups; mixed batches; identity disagreements;
orphaned references; duplicate linked-student memberships under different
identifiers; and legacy curriculum semester-column shapes/values.

Case/space normalization of academic codes already has dedicated unique indexes.
Register/roll identifiers require their own approved normalization policy; do not
silently fold case, strip leading zeros, or merge students to remove duplicates.
