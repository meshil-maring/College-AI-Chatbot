# Academic Setup overview

The administrator sidebar opens Academic Setup on the responsive black-and-yellow
overview. The feature retains the existing authenticated shell, account navigation,
server grants and catalogue workflows. It does not change backend contracts or
database relationships.

Academic Setup remains visible to authenticated administrators even when their
account has no academic catalogue grants. In that case it opens the design
preview without making catalogue requests; counts remain unavailable and record
actions are disabled. Live catalogue reads require an existing academic read
grant, and writes still depend on server-advertised manageable access.

## Entity mapping

| Overview management area | Approved entities                        |
| ------------------------ | ---------------------------------------- |
| Departments              | Departments                              |
| Programs                 | Programs                                 |
| Academic Calendar        | Academic Years, Academic Terms           |
| Subjects                 | Subjects                                 |
| Program Semesters        | Program Semesters                        |
| Curriculum               | Curriculum Versions, Curriculum Subjects |
| Admission Cohorts        | Admission Cohorts                        |
| Academic Sections        | Academic Sections                        |
| Academic Offerings       | Academic Offerings                       |

The desktop grid uses four, three and two cards. Narrower desktop/tablet widths
reflow cards to two columns; mobile uses one. Summary cards retain their icons.
Desktop navigation can collapse; mobile navigation opens above a dismissible scrim.

Academic Terms describe dated teaching periods. Program Semesters describe program
progression. A proposed Academic Section belongs to one cohort, one program semester
and one academic term, and may contain multiple Academic Offerings. Cohorts retain
their assigned published curriculum. These descriptions do not modify existing data.

## Existing data and actions

Departments, programs, academic years and teaching courses have compatible summary
concepts. Subject summaries read the existing teaching-course catalogue. Counts use
only records matching the response institution and authenticated institution.
Missing catalogues display an em dash; confirmed empty catalogues display zero.

Search covers the approved academic areas and readable names/codes from these four
compatible catalogues. Search results open the existing catalogue for the record.
Unreadable or foreign-institution records never appear in results.

The four compatible creation shortcuts open the existing forms only when the
response advertises readable and manageable access and required parents exist.
The form independently rechecks its own catalogue response. It sends no mutation
until the user submits the existing Save action. Activation/deactivation requires
confirmation, with an additional explanation when clearing a current designation.

## Departments management

The Departments destination now opens its own dark-and-yellow management page in
`academic-setup/departments/`. It uses the existing department catalogue and
create/update endpoints; it does not introduce a replacement academic contract.
The overview's Add Department shortcut opens this page's drawer directly. Other
catalogues and the eleven-entity navigation remain unchanged.

Institution-scoped totals show total, active and inactive departments. The table
supports name/code search, status filtering, name/code sorting and five-record
pagination. Associated program counts and details use only the readable,
institution-scoped program catalogue; unavailable program data is never zero.
Read-only and disconnected states disable mutations, and denied reads expose no
records. Failed refreshes label retained records as stale and disable changes.

Add, View and Edit use a keyboard-accessible modal drawer with mobile record
cards, a full-screen mobile drawer and pinned footer actions. Forms preserve
entries after errors, require an explicit creation status and use the existing
API's text limits (name 160, code 32, description 2000). Codes are trimmed without
inventing case or syntax rules; duplicate conflicts remain server-authoritative.
Discarding edits and changing an existing status require confirmation. There is
no deletion action, Campus field, Head of Department relationship or new grant.
Pending mutations cannot update a replacement identity's UI or trigger its reads.

The existing service assigns sections to offerings. This differs from the proposed
section model, so existing sections and offerings are not relabeled or silently
mapped to the proposed Academic Sections and Academic Offerings.

## Programs management

The Programs destination opens the dedicated `academic-setup/programs/` page.
It follows the supplied dark-and-yellow design with four summary cards, combined
name/code, department, degree-type and status filters, sortable table columns and
eight-record pagination. Narrow content widths use record cards. Add, View and
Edit share a modal drawer with pinned actions and a full-screen mobile layout.
The overview's Add Program shortcut opens this drawer directly.

Records, department choices and totals use only readable institution-scoped
catalogues. Missing department data displays Unavailable. Creation requires an
active readable department, and mutations require the existing server-advertised
program access. Denied reads hide records; failed refreshes label retained data
as stale and disable writes. Identity replacement clears the screen and prevents
late mutation results from triggering replacement-identity reads.

Forms use the existing program endpoints and field limits (name/degree type 160,
code 32, description 2000), retain custom existing degree types and fractional
durations, and preserve nullable credits. New programs default to Active as in
the reference. A saved program's department remains immutable. Status changes
and discarding unsaved entries require confirmation; duplicate and request
errors retain the draft. Both department and program drawers use the shared
keyboard and focus lifecycle in `academic-setup/dialogs/`.

## Academic Calendar management

Academic Calendar and its Years/Terms destinations open `academic-setup/calendar/`.
The page follows the supplied dark-and-yellow reference with four summary cards,
expandable year records and nested dated semesters, search/status/sort controls,
pagination and responsive record cards. Its four tabs expose Academic Years,
Semesters, Important Dates and Overview Timeline. Dates come from existing year
and semester boundaries; timeline bars open semester details. Dated semesters
retain their existing meaning and do not stand in for proposed program stages.

Add/View/Edit use the shared accessible modal lifecycle with pinned actions and
a full-screen mobile drawer. The overview's Configure Academic Year shortcut
opens the year drawer. Creation supports two, three or custom initial semesters
when both catalogues are readable and the server advertises both management
capabilities. Initial dates divide the selected year and remain editable. Year
descriptions and independent event records have no existing API fields and are
not offered as editable data.

Writes retain existing text limits, date bounds, active/current flags and the
immutable semester parent. Status/current changes and discarding unsaved entries
require confirmation. Multi-request creation checkpoints each saved record;
after partial failure, the drawer locks saved values and retries only remaining
semesters. Already saved records remain if the draft is discarded. Unknown
network outcomes still require the server's existing conflict handling.

Counts and records use tenant-verified catalogues. Current badges and current
summary counts use server flags. Display statuses otherwise derive from dates
and active flags. Denied reads hide data; failed refreshes mark retained data
stale and block writes until Retry succeeds. Identity replacement discards UI
state and stops further requests in a pending multi-request save.

## Integration previews and states

New areas expose descriptions, distinct child destinations and relevant proposed
status labels. Their records and mutation controls await separate integration.
Proposed creation shortcuts are disabled and marked Not connected; they do not
invent permission grants. The activities panel is explicitly illustrative.

Loading preserves the four-card summary layout. Failed requests provide Retry and
block creation shortcuts. Search has a distinct no-results state and Clear search.
Existing forms retain required-field/date validation and server error feedback.
Inactive entities remain visible in existing records. Draft/Published apply only
to curriculum versions; other proposed lifecycle states are labeled as proposals.
No publish or historical curriculum reassignment action is connected.

Queries and local record requests are scoped to the authenticated identity. Token,
tenant or permission replacement remounts the feature and discards pending UI state.

## Remaining integration decisions

- Approved contracts and grants for the eleven-entity model.
- Supported lifecycle states and transitions per entity.
- Real recent activity feed and cross-entity search for the new areas.
- A separate authorized workflow for exceptional historical curriculum changes.
