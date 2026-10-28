# Academic Setup design review and improvement backlog

[Reading guide](README.md) · [Current workflows](WORKFLOWS.md)

This page separates observed implementation from proposed decisions. Priorities
are review suggestions based on local source, not a production incident ranking.
No proposed behavior is implemented by this documentation update.

## Present interaction design

The academic workspace uses a black-and-yellow visual system with a sidebar,
breadcrumbs, page descriptions, summary cards, filterable lists and record drawers.
Calendar and Curriculum group related subviews. Search covers management areas
and readable records. Quick actions use permitted entities and parent availability.

Dedicated foundation/batch/section pages use focused state hooks and components.
Program semesters, curriculum versions/mappings and offerings reuse the shared
structure table/drawer. Forms filter choices by relationships and expose fixed
assignments as immutable rather than treating them as editable selectors.

Drawers share a native dialog lifecycle, keyboard focus handling, scroll locking
and focus return. Dedicated editors retain failed entries and confirm discard or
existing status changes. Loading, empty, denied, unavailable and stale states have
different meanings; unconnected enrollment never becomes a fake zero.

The older generic catalogue remains separately accessible and has simpler forms.
Do not assume its interaction safeguards match every newer dedicated drawer.

## Architectural decisions to preserve

| Decision                                     | Benefit                                           | Tradeoff to review                                            |
| -------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------- |
| Separate dated terms from progression stages | One calendar can serve multiple intake stages     | Requires clear labels and two selectors                       |
| Reuse subjects across programs               | Avoids duplicated catalogue definitions           | Published curricula still see mutable subject metadata        |
| Pin curriculum to batch                      | Prevents silent replacement of an intake's plan   | Corrections/transfers need an explicit future workflow        |
| Additive workspace beside export model       | Preserves existing data and API contracts         | Two mapping/delivery structures need clear ownership          |
| Server-owned tenant and audited RPC writes   | Stronger authority and transaction boundary       | Database functions become important business-rule owners      |
| Per-institution advisory lock                | Serializes relationship-sensitive writes          | Bulk throughput is limited within one institution             |
| Soft lifecycle and dependency guards         | Preserves references and audit history            | Historical mappings complicate full retirement                |
| Feature-owned UI state                       | Keeps rendering, requests and draft logic focused | Shared query keys and reconciliation need consistent adoption |

## Review first: historical correctness and closure

### R1. Define what a published curriculum must preserve

**Observed:** Publication freezes version metadata and mapping rows. Subject names,
credits and hours remain on editable `courses` rows. A future edit can therefore
change the information displayed for an earlier published plan.

**Decision:** Is a curriculum a fixed arrangement of live subject references, or a
historical academic specification? If historical details matter, consider subject
revisions or version-owned snapshots of the relevant academic fields. Keep one
clear source for effective credits instead of duplicating ambiguous values.

**Acceptance condition:** Changing a reusable subject after publication produces
the explicitly chosen historical behavior, demonstrated with an older batch and
two curriculum versions. Describe which labels may remain live references.

Evidence: [workspace tables](../../../supabase/migration_sources/academic_workspace/tables.sql),
[publication lifecycle](../../../supabase/migration_sources/academic_workspace/lifecycle.sql),
[editable subject contracts](../../../backend/app/schemas/academics/academic_setup.py).

### R2. Define retirement across published dependencies

**Observed:** Archive status does not deactivate mappings. Published mappings
cannot be deactivated, while active mappings prevent deactivation of their
version, subject and progression stage. A completed batch alone does not resolve
those historical dependencies.

**Decision:** Specify the difference between no longer admitting new batches,
finishing existing delivery, and retiring a reusable definition. Consider an
effective availability/retirement model that preserves immutable published rows.
Avoid bypassing dependency checks to accomplish normal closure.

**Acceptance condition:** A full lifecycle rehearsal can publish, teach, finish,
archive and retire the intended foundations while all historic links and audit
records remain readable and no active delivery is orphaned.

Evidence: [lifecycle](../../../supabase/migration_sources/academic_workspace/lifecycle.sql),
[dependency guards](../../../supabase/migration_sources/academic_workspace/parent_guards.sql),
[editor freezing](../../../frontend/src/features/admin/academic-setup/structure/useStructureEditor.ts).

### R3. Agree on publication completeness and temporal rules

**Observed:** One active valid mapping is enough to publish an eight-semester
version. The model does not enforce stage coverage or credit totals. Batch year
spans are not derived from duration, and section-term selection does not enforce
that term dates fall within a batch's year span. Active year overlap is prevented;
equivalent term-overlap policy is not enforced by the current database constraints.

**Decision:** Which rules are mandatory, which are warnings, and which allow
institution-specific exceptions? Define elective groups/credit alternatives before
requiring a naive sum of every optional subject. Decide whether overlapping
dated terms support legitimate parallel calendars.

**Acceptance condition:** Publication returns an explicit readiness report;
required missing stages, inconsistent credits and invalid calendar assignments
receive actionable errors, while documented exceptions remain possible.

Evidence: [relationship checks](../../../supabase/migration_sources/academic_workspace/relationships.sql),
[publication checks](../../../supabase/migration_sources/academic_workspace/lifecycle.sql),
[foundation constraints](../../../supabase/migration_sources/academic_export/constraints.sql).

## Review next: dependable editing and understandable recovery

### R4. Distinguish rejected saves from uncertain outcomes

**Observed:** Record writes are atomic, but calendar setup spans multiple requests
and retains checkpoints only in memory. A network timeout can occur after commit.
The public API has no idempotency key or expected revision. The tenant lock does
not prevent a later editor overwriting a previously saved field.

**Proposal:** Introduce idempotent create requests and optimistic concurrency where
needed. For multi-record setup, compare a resumable operation with an atomic
backend workflow; preserve per-record audit either way. Make “saved, refresh
failed” distinguishable from “save rejected.”

**Acceptance condition:** Lost-response retries do not create a second logical
record, stale edits receive a conflict, and partial calendar creation can be
reconciled after reload without losing successful records.

Evidence: [calendar saver](../../../frontend/src/features/admin/academic-setup/calendar/editor/saveCalendar.ts),
[shared writer](../../../frontend/src/features/admin/academic-setup/structure/useStructureWrite.ts),
[RPC payloads](../../../backend/app/repositories/academics/academic_structure.py).

### R5. Standardize academic queries and mutation reconciliation

**Observed:** Foundation queries have instance-specific keys and immediate cache
collection, while structure queries retain navigation data. Versioned Curriculum
and its shared records page can each compose catalogue hooks. Writes refresh
their local query instances; a foundation update does not establish a unified
invalidation rule for all retained academic data and activity.

**Proposal:** Adopt the project's domain-query guidance across this feature.
Centralize identity-scoped academic keys and owning query functions, define
affected-query invalidation for each mutation and keep previous data visibly stale
when appropriate. Retain identity replacement and late-result protections.
Bring the existing generic catalogue's token-based inner identity into the same
session-generation policy so renewal does not discard its draft.

**Acceptance condition:** A foundation edit immediately reconciles overview counts,
related parent choices, structure labels and recent activity; navigation avoids
redundant full-catalogue reads and never reveals another identity's cached data.

Evidence: [query wrapper](../../../frontend/src/hooks/useApiQuery.ts),
[composed queries](../../../frontend/src/features/admin/academic-setup/structure/useAcademicStructure.ts),
[frontend server-state guide](../../../frontend/docs/SERVER_STATE.md).

### R6. Make the setup dependency graph visible to administrators

**Observed:** The overview is organized by management area. Program semesters and
offerings use a generic records layout. Admin academic pages use local state, so
specific curriculum or section views cannot be bookmarked. Generic hierarchy
errors do not identify all blocking children. Some overview model copy still
contains proposed Planned/Closed/Cancelled states, while persisted states differ.

**Proposal:** Add a setup-readiness checklist with links to missing parents and
next actions. Explain both semester meanings beside selectors. Show a curriculum
matrix by progression stage, a section-to-offering view and lifecycle blockers.
Add URL-backed subpages where sharing, refresh and Back/Forward matter. Align
state labels and confirmations across dedicated pages and the existing catalogue.

**Acceptance condition:** A new administrator can finish the example workflow,
recover a blocked save and return to a shared record link without guessing a
relationship or reading database terminology. Retain keyboard and mobile usability.

Evidence: [overview definitions](../../../frontend/src/features/admin/academic-setup/overview/academicOverviewModel.ts),
[workspace dispatcher](../../../frontend/src/features/admin/academic-setup/overview/AcademicWorkspace.tsx),
[generic catalogue hook](../../../frontend/src/features/admin/academic-setup/useAcademicSetup.ts).

## Scale and expand after the core decisions

| Proposal                                                    | Current trigger / reason                                            | Completion evidence                                                                                             |
| ----------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Server-filtered, paginated list and parent-choice endpoints | Both APIs assemble complete catalogues; browser tables page locally | Realistic large-institution payload, query-count and latency measurements improve without losing tenant filters |
| Set-based bulk workflows                                    | Every write takes the same institution lock                         | Measured imports improve while duplicate races, audit atomicity and child/parent safety still pass              |
| Curriculum clone and comparison                             | New versions currently require explicit record/mapping authoring    | Clone creates an independent draft; diff explains changes without altering the original                         |
| Explicit compatibility policy                               | Existing and versioned models are independent                       | Document which path new work uses; any conversion has a reviewed mapping and preservation proof                 |
| Enrollment as its own domain                                | Capacity and expected intake are not student membership             | Tenant-safe student/batch/section membership, movement history and effective counts have explicit contracts     |
| Teaching, attendance and results integrations               | Offerings currently represent delivery structure only               | New capabilities reference the intended offering model and enforce their own permissions and lifecycle          |
| Unified lifecycle audit presentation                        | Foundation actions name activation; workspace actions use update    | Activity explains publication/archival/closure consistently without exposing restricted actor or audit data     |

Do not build enrollment counts from capacity, restore disconnected legacy teaching
source implicitly, or silently write both academic models as a synchronization
shortcut. Those choices would obscure ownership and historical meaning.

## Suggested review order

1. Agree on publication history and retirement semantics: R1–R2.
2. Define academic completeness, credit and calendar policy: R3.
3. Harden save/recovery contracts and cache reconciliation: R4–R5.
4. Improve navigation, setup guidance and curriculum/section visualization: R6.
5. Measure scale, then prioritize bulk operations and later domain integrations.

For every accepted change, record the problem, chosen behavior, affected entities,
migration impact, permission impact, historical-data impact and regression proof.
Keep that decision separate from the description of behavior already implemented.
