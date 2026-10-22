# Package selection, change requests, and semester locks

Status: implemented locally. See [implementation evidence](implementation.md);
the live database has not been migrated.

## Initial assignment

A package assigns every subject in its bundle plus the curriculum's shared core
for that study semester. Selecting ABC assigns DSA, ML, A, B, C together.
Students cannot select a partial or mixed package.

| Actor / setting | First assignment | Later change |
| --- | --- | --- |
| Student, choice enabled | Select an available package for their own eligible placement. | Request a change before cutoff. |
| Student, choice disabled | Administration assigns it. | Request a change before cutoff. |
| Authorized administration | Assign within their scope. | Apply a direct change or review a request before cutoff. |
| After cutoff | First assignment remains possible under the same authority and choice setting. | Changes are closed for everyone. |

Student choice defaults off and belongs to the class. Enabling it permits only
initial selection; students cannot replace an assigned package directly.
Toggling choice does not change any existing assignment.

There is one package assignment per placement in a class/term. A registration
can progress through explicitly configured classes in later dated terms; the
original admission registration and batch remain unchanged.
Class placements for the same registration must have nonoverlapping captured
teaching periods. A second term ID cannot create a competing plan in the same
calendar period or bypass an existing class deadline.

## Authority

All commands use the authenticated server-resolved user and institution.
The database checks permissions, active accounts, active institution, and scope.

- Admin needs the exact operation permission within the institution.
- Staff needs an explicit delegated capability through the existing audited
  permission-grant workflow. No new package authority is granted to all staff.
- HOD must have a live responsibility for the program's department. A subject's
  owning department does not grant authority over another program's class.
- Class incharge must have a live matching responsibility explicitly connected
  to this class, including its batch. Equal section letters are insufficient.
- Students need an approved active linked account and can only read/select or
  request against their own placement.
- Ordinary teaching assignments confer no package-management authority.

Client-side visibility and readable selection codes never grant permission.
Direct browser table access and helper-function execution are revoked.

## Complete, atomic assignment

The database validates the class, batch, dated term, curriculum version, allowed
package, registration identity, active subjects/offerings, teaching mappings,
and capacity before publishing the assignment.

Every shared core and selected package subject must have a valid teaching group.
A missing, full, inactive, foreign, or conflicting group rolls back the entire
operation, including any prepared rosters, assignment history, and audit writes.

An initial retry of the same package returns the existing assignment without
new memberships, revisions, or audit entries. Later changes require the expected
assignment revision and an administrative reason. A stale revision cannot
overwrite a newer assignment.

Account approval and activation remain separate from subject participation.
Package selection never approves or activates a student account.

## Student requests

A request records the current assignment revision, target package, reason,
requester, and time. It leaves the current subjects unchanged. There can be one
pending request for an assignment; the database rejects duplicates.

| State | Meaning |
| --- | --- |
| Pending | Awaiting a scoped decision; current subjects stay active. |
| Approved | The complete package change succeeded atomically. |
| Rejected | A scoped reviewer declined it and recorded a reason. |
| Expired | The deadline passed before successful application. |
| Superseded | An intervening assignment change invalidated its source revision. |

Approval uses the same validated assignment operation as a direct change.
Submission before cutoff never reserves a later approval window. Reads project
expired requests immediately; review records expiry without changing subjects.
Student cancellation and request notifications are outside this version.

## Cutoff policy

The administrator sets a deadline no later than the dated semester's calendar
midpoint. Omitting the deadline uses the midpoint. This is the user's confirmed
policy: **admin deadline, capped at midpoint**.

Dated terms use UTC boundaries from start-date 00:00 through the day after
end-date 00:00 (exclusive). The midpoint is halfway between those instants.
The UI edits and displays the stored deadline in IST (`Asia/Kolkata`), with
the timezone stated in the label.
Holidays and teaching-week counts do not alter this calendar calculation.

A change is allowed only while the live database clock is strictly before the
deadline. Exactly at and after cutoff, direct changes, new requests, and late
approvals are blocked for all roles. Authority and time are rechecked after
lock waits, immediately before the mutation.

Class identity and captured teaching dates are immutable. A deadline can only
be shortened, never extended. Curriculum/package content freezes as soon as a
class references its curriculum, including before the first assignment. Package
availability edits do not modify any existing student's assignment.

The cutoff controls changes to existing assignments. It does not introduce an
admission deadline; eligible first assignments may still be made later.

## Participation and history

A successful change keeps shared subject roster IDs, attendance, and marks.
Removed subjects receive an ended participation episode; new subjects receive
new episodes. Rejoining a subject reuses its historical roster and starts a
new episode rather than deleting old records.

Student attendance, performance, published results and timeline preserve past
subject history. Upcoming assessments require current participation. Current
faculty rosters exclude ended memberships. Marks screens retain previously
entered marks while excluding ended memberships without saved marks. Historical
attendance and published results remain available through their existing views.

The legacy attendance and test schemas store event dates, not event timestamps.
Event eligibility therefore uses inclusive UTC start/end dates of participation
episodes; same-day historical marking is possible. Exact episode timestamps
remain recorded. No marks transfer to a different subject automatically.

Managed teaching groups cannot accept individual subject additions, removal,
or identity reinterpretation through the old manual/import/reconciliation
paths. Canonical account reconciliation may update linkage and approval state,
but it cannot hijack a package roster or change its participation cache.

Roster deletion cannot erase attendance, marks, or package history. Assignment,
revision, participation, request decision, and audit changes commit together.
