# Verification, open decisions, and change control

**CAI-RBAC-001 v1.2; DRAFT - REVIEW ONLY; 21 October 2026.** Read the [reading guide](README.md) and relevant role first. Source observations are not live-deployment certification.

No tests were executed for this documentation task. The following is a future authorized verification plan, not a list of passed checks.

| ID | Scenario | Required outcome |
|---|---|---|
| V01 | Missing, malformed, expired, or invalid authentication. | Protected operation denied using the supported authentication error contract. |
| V02 | Pending, inactive, suspended, or revoked account. | Protected academic access denied as required by account policy. |
| V03 | Permission absent or revoked while role remains. | Action denied without fallback to bootstrap defaults. |
| V04 | Correct permission but disallowed endpoint role. | Action denied. A permission alone must not bypass the endpoint role guard. |
| V05 | Foreign institution ID in path, query, body, export, or relationship. | Foreign data is not returned or changed. |
| V06 | Student submits another student's ID. | Own-record scope retained; unauthorized access denied. |
| V07 | Faculty uses an unrelated, scheduled, expired, inactive, or revoked assignment. | Protected academic operation denied. |
| V08 | HOD/Class In-Charge uses a resource outside responsibility scope. | Action denied; no institution-wide permission expansion. |
| V09 | Staff opens Roster/Register or calls their current Admin/Faculty registration APIs. | Existing role restrictions retained; no access gained from shared components. |
| V10 | User attempts self-approval or self-approved privileged grant. | Required separation of duties enforced. |
| V11 | Bulk file validates, then scope/grants change before commit. | Commit rechecks authority and cannot persist unauthorized rows. |
| V12 | Foreign/inactive batch or conflicting identifiers submitted. | Invalid placement or identity change rejected without silent overwrite. |
| V13 | Invitation request supplies a different recipient or foreign registration ID. | Recipient comes from the saved authorized record; foreign record denied. |
| V14 | Duplicate/concurrent invitation attempts, delivery failure, or interruption. | Saved registration preserved; claims and uncertain delivery handled without an unsupported exactly-once claim. |
| V15 | Admin session opens a student registration link. | Student account-switch entry shown; after sign-out, requested student registration opens with the institution code intact. |
| V16 | Public chat or search encounters restricted/foreign content. | Unauthorized content excluded before retrieval results enter model context. |
| V17 | Permission revocation, institution suspension, or account change across tabs. | Supported fresh authorization and session behavior enforced; stale frontend state cannot grant API access. |
| V18 | Critical mutation/audit failure or concurrent state transition. | Required transaction and audit guarantees hold; no unauthorized partial change. |
| V19 | Missing route mapping, missing authorization schema, or unavailable authorization data. | Fail closed with a controlled response; no privilege fallback. |
| V20 | Role, scope, status, actor, or permission injected through registration/UI input. | Rejected or ignored according to strict contracts; authority remains server-owned. |

Acceptance requires a reviewed route inventory, role/grant definitions, resource-scope rules, database-policy evidence, and meaningful positive and negative checks. Live database enforcement, deployed grant contents, every background path, and all legacy routes remain unverified here.

## Open decisions and change control

| ID | Decision / gap | Required review |
|---|---|---|
| D01 | Policy ownership and approval. | Assign an accountable owner and approver; record their approval before implementation. |
| D02 | Bootstrap grants versus live database grants. | Compare through a separately authorized environment review. This document does not access hosted Supabase. |
| D03 | Staff catalog permissions versus endpoint/UI availability. | Preserve current Students access. Any expansion needs an explicit role, route, scope, and UI decision. |
| D04 | Faculty registration uses `attendance.manage`. | Review whether this remains the intended permission vocabulary; do not rename or grant permissions through documentation alone. |
| D05 | Batch management uses `departments.manage`. | Review whether a dedicated permission is needed later; no new permission is introduced now. |
| D06 | `university_admin` alias and legacy Admin `platform.manage`. | Confirm compatibility requirements and actual grants without confusing them with canonical platform authority. |
| D07 | Formal verification/repair and self-approval controls. | Obtain the required governance decisions and permitted evidence review separately. Restricted artifacts remain untouched. |
| D08 | Route, retrieval, database, and audit completeness. | Complete a separate coverage review; representative source examples are not certification. |
| D09 | Multi-role scope conflicts and revocation timing. | Verify ambiguous grants, precedence, concurrent revocation, and access-token lifetime behavior. |

The present activity is limited to rewriting and source-informed documentation. It does not authorize application changes, migrations, hosted database access, deployment, restricted-artifact inspection, or permission provisioning. Approval of the document and authorization to implement it are separate decisions.

### Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 21 October 2026 | User-supplied review-only roles and permissions draft. |
| 1.1 | 21 October 2026 | Clarified canonical/platform roles, scoped responsibilities, Staff boundaries, registration stages, invitation semantics, permission vocabulary, representative guards, verification gaps, and source references. |
| 1.2 | 21 October 2026 | Split the review draft into shared rules, role documents, and focused references; preserved policy approval status and checked documentation consistency. |

Version 1.2 (21 October 2026) splits the review draft into shared, role-specific, and supporting reference files. Policy approval status is unchanged. Documentation links and source-derived grant summaries are checked separately from application behavior.
