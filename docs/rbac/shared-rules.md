# Shared authorization rules

**Status: DRAFT — REVIEW ONLY.** Read this before the relevant [role document](README.md). Rules are proposed policy unless labeled source-observed. Evidence IDs are defined in [source references](source-references.md).

## Authorization decision

`ALLOW = authenticated caller AND eligible account AND permitted endpoint role AND required permission(s) AND valid institution context AND valid resource/ownership scope AND applicable workflow checks`

All applicable checks MUST pass. Deny access by default. Missing, ambiguous, expired, revoked, or unavailable authorization data MUST NOT produce broader access. Public endpoints use their explicit public policy, visibility rules, input validation, and abuse controls instead of an authenticated role.

Roles, tenant membership, actor identity, approval state, and effective permissions MUST come from trusted server-side records. Record IDs, email links, URL parameters, filters, AI answers, and visible buttons are not grants.

## Permissions and roles

**Source-observed — S01–S03:** Real resolved requests use database permissions without falling back to bootstrap defaults when grants are absent or revoked. The fallback supports internal/test contexts only. Matching recognizes exact codes, `*`, or the first resource prefix followed by `.*`; it is not arbitrary nested wildcard matching.

Every protected operation MUST also satisfy endpoint role and scope checks. Wildcards require explicit review because they can include future actions. Primary-role precedence (`super_admin`, `admin`, `staff`, `faculty`, `student`) selects an application identity, not unrestricted inheritance. The catalog's `university_admin` alias is not a sixth canonical role. The legacy Admin `platform.manage` entry does not satisfy a Super Admin platform guard.

## Scope, ownership, and validity

| Boundary | Rule |
|---|---|
| Platform | Requires explicit platform authority; a missing institution ID does not establish it. |
| Institution | The caller's trusted grant must match the resource's owning institution. Resolve ambiguous grants explicitly. |
| Academic unit | Match the required department, program, course, year, semester, section, and subject/teaching context. |
| Own resource | Derive ownership from the authenticated user, not a submitted student/user ID. |
| Batch | An admission cohort such as 2026–2030; distinct from academic year and not an access grant. |

**Source-observed — S07–S09:** Teaching and responsibility validity uses timezone-aware `start <= now < end`; no end permits continuing validity. Inactive/revoked assignments do not qualify. Class scope uses normalized program/year/semester/section identifiers. Responsibility permissions remain scoped. Teaching-only operations do not become available from an unrelated responsibility.

Reads, writes, search, exports, counts, pagination, and related-resource queries MUST preserve these boundaries. Organization-scoped and legacy tenantless helpers require independent review and MUST NOT bypass institution-role checks.

## Workflow and separation of duties

Registration, invitation delivery, identity verification, account approval, subject enrollment, and academic writes are distinct operations. Users MUST NOT approve their own registration or privileged grant. Formal identity repair follows its separately approved independent-review process. Evidence access and security investigations require explicit scope.

An authorized administrator does not automatically bypass independent workflow controls. Emergency access, if introduced, requires an authorized actor, bounded scope, recorded termination condition, and audit trail. No emergency bypass is established here.

## Enforcement and sessions

The frontend presents access; the API enforces roles and permissions; services enforce resource/workflow scope; database/RPC paths must enforce applicable integrity and commit-time controls. Review service-role access independently of browser RLS. Imports, background jobs, and AI tools MUST retain an accountable actor/context and revalidate authority before sensitive commits.

**Source-observed — S01, S04, S06, S16, S19, S22:** Admin/platform route maps fail closed for missing mappings. Server-resolved roles select the workspace. Student invitation links preserve their institution hint through account switching; they never assign a role. Logout clears the shared browser session; refresh-session revocation does not instantly invalidate every self-contained access JWT. Account/grant checks, access-token lifetimes, restoration, and cross-tab changes require verification.

## Audit

Sensitive changes SHOULD record actor, action, resource, scope, outcome, timestamp, and correlation context. Critical workflows MUST meet their durable-audit requirements. Never expose passwords, API keys, raw authentication/invitation tokens, or unrestricted evidence contents. Audit access requires its own authority. A post-mutation log alone does not prove transactional atomicity; failures and concurrency must be checked.

See [module policies](module-policies.md) for specific controls and [verification](verification.md) for unverified coverage and owner decisions.
