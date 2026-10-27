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

The existing service assigns sections to offerings. This differs from the proposed
section model, so existing sections and offerings are not relabeled or silently
mapped to the proposed Academic Sections and Academic Offerings.

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
