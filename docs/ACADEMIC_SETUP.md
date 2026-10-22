# Academic Setup

Sign in as an authorized institution administrator and open **Academic Setup**.
The workflow follows six stages. Use the institution's official names, codes,
calendar dates, and subject definitions.

| Stage | What to enter |
| --- | --- |
| College basics | Departments, degree programs/branches, and admission batches. |
| Calendar | Academic years and their dated teaching terms. |
| Subjects | Reusable subject definitions owned by departments. |
| Curricula & packages | Named curriculum versions, study semesters, classifications, shared core, and complete subject packages. |
| Classes | Batch, teaching term, study semester, class section, curriculum, enabled packages, rules, and teaching groups. |
| Assignments | Student placements, complete package assignment, change requests, and history. |

Departments, programs, batches, calendar terms, and subjects remain separate
normalized records. Their forms sit in the relevant stages. The old nine-entity
tab bar and separate legacy Program Curriculum editor are retired from this
workflow. Offerings and subject teaching sections are prepared within Classes.

## College basics, calendar, and subjects

Create departments first, then programs and their admission batches. A program
represents the degree and branch, such as B.Tech Computer Science. A batch is an
admission cohort, such as 2026-2030, rather than the current academic year.

The **Course / branch** selector in Curricula & packages and Classes uses these
degree programs. Subjects such as DSA or ML belong in the subject library. If no
program is available, use **Set up a course / branch** to open College basics
with Degree programs selected. Saving academic records refreshes the current
session's curriculum/class options automatically.

Academic years have real start and end dates. Active years cannot overlap, and
an inactive year cannot be Current. Clear Current on the previous year before
choosing a new current year. Dated semesters belong to an academic year; their
dates must fit that year. Codes and semester numbers are unique within the year,
and only one dated semester per year can be Current.

A dated teaching term is distinct from a study semester in a degree. Class Setup
connects, for example, study Semester 5 to the actual term in academic year
2028-2029. Programs can use the same institution calendar.

Subjects are reusable definitions, such as DSA or Machine Learning. Curriculum
membership determines whether a subject is core, elective, open elective, skill,
or project. One subject may have different classifications in different plans.

Searchable directories and detail panels support creation and safe metadata or
activation changes. Required fields have an asterisk. Context explanations and
prerequisites guide each form. Academic parent identifiers remain fixed after
creation; deactivation retains dependent data and history.

## Curricula and packages

Create a named version, such as curriculum code `CSE-202-DSEE`. Add the subjects
and classifications for each study semester. Mark shared core subjects and
create complete packages from the other curriculum subjects.

| Package | Shared core | Package subjects | Assigned together |
| --- | --- | --- | --- |
| ABC | DSA, ML | A, B, C | DSA, ML, A, B, C |
| EFG | DSA, ML | E, F, G | DSA, ML, E, F, G |

Finish the plan before creating its first class. Referenced curriculum content
freezes, so later changes require a new curriculum version. A class requires at
least one complete package for its chosen study semester.

Subjects use references to the shared library. Do not create duplicate subject
definitions, legacy curriculum links, or copied core subjects for each package.

## Classes and teaching groups

Choose the admission batch, dated term, study semester, class section, and
curriculum. Enable the packages offered to this class. Class codes identify the
shared context; selection codes append the package code. Preview the full
context and subject set instead of inferring relationships by parsing a code.

Set whether students may select their first package; this defaults off. Set an
administrator deadline no later than the semester's calendar midpoint. The
stored instant is edited and displayed in IST (`Asia/Kolkata`). An omitted
deadline uses the midpoint. A configured deadline can only be shortened.

Use **Prepare teaching groups** after enabling packages. It prepares offerings
and class-specific subject sections for shared core and enabled-package subjects
in one transaction, then maps them to the class. Existing valid mappings remain.
Invalid or foreign mappings stop the operation without partial writes.

This action requires an institution administrator with both class-management
and existing course-management permission. No manual legacy curriculum link is
needed. Canonical offerings
remain unique by subject, program, academic year, and teaching term. Teaching
sections remain subject-specific because faculty, rosters, attendance, and
results use them; they are not additional shared classes.

Assign real faculty to the prepared subject sections in **Faculty Assignments**.
That workflow retains its existing permissions and responsibility checks.

## Assignments and changes

Place an eligible registration in its class, then assign a package. Selection
assigns every package subject and all shared core together. Missing, inactive,
conflicting, or full teaching groups roll back the complete operation.

If initial student choice is enabled, an eligible student may choose once for
their own placement. Otherwise authorized administration makes the assignment.
Students can request later changes. Only authorized administration can apply a
change or approve a request, within the verified class/department scope.

At and after the deadline, package changes and late approvals are blocked for
everyone. Submitting a request earlier does not extend the deadline. First
assignments remain possible for late admissions under the same authority.

Changes preserve shared memberships and recorded attendance/results. Removed
subjects receive ended participation; rejoining preserves the historical roster
and starts a new participation episode. Current teaching views exclude ended
participation while historical attendance and published results remain visible.

Package assignment does not create, approve, or activate student accounts.
Original admission identity and batch remain intact during progression to later
dated terms. Managed classes require complete packages; legacy unmanaged groups
retain their existing individual roster/import behavior.

## Access, refresh, and operations

The server derives the institution and actor from authenticated state. Browser
visibility never grants authority. Staff need explicit delegation; HOD and class
incharge authority requires a live matching scoped responsibility. Ordinary
teaching assignments do not confer package-management authority.

Academic catalogues reuse recent data for one minute and retain it in memory for
five minutes after leaving the screen. Saves refresh affected catalogues. Use
Refresh to fetch immediately. Data is scoped to the session token and cleared
on logout, expiry, or replacement.

See [implementation and validation](proposals/academic_curriculum_packages/implementation.md)
for API contracts, schema installation, regression evidence, and release status.
The [fresh-start record](proposals/academic_curriculum_packages/fresh-start.md)
defines the authorized Quest academic reset. Accounts, roles, audit history, and
unrelated modules are outside that reset.
