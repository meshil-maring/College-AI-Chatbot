# Module-specific authorization policies

**CAI-RBAC-001 v1.2; DRAFT - REVIEW ONLY; 21 October 2026.** Read the [reading guide](README.md) and relevant role first. Source observations are not live-deployment certification.

The requirements below are **proposed policy**. Permission names are source-observed vocabulary; each endpoint's exact enforcement still requires review.

| Module | Relevant permission vocabulary | Required boundary and behavior |
|---|---|---|
| Own profile | `profile.own.read`, `profile.own.update` | Resolve the caller from authentication. Permit only approved editable fields; exclude role, institution membership, authoritative identifiers, and approval state. |
| User administration | `users.read/create/update/delete` | Permitted endpoint role plus platform or institution management scope. A generic user permission must not grant every workflow-specific mutation. |
| Roles and permissions | `roles.read/manage`, `permissions.read/manage` | Server-owned grants, eligible management scope, separation of duties, and durable audit. Do not infer a generic grant-management API from a catalog code. |
| Student administration | `students.read/create/update/delete/approve/reject/suspend` | Authorized institution or academic scope, supported endpoint role, and state-specific decision checks. |
| Faculty and Staff accounts | `faculty.*`, `staff.*` entries in [permission catalog](permission-catalog.md) | Membership, approval, and lifecycle actions remain distinct from ordinary profile editing. These shorthand families do not create new wildcard grants. |
| Academic setup | `departments`, `courses`, `subjects`, `semesters`, `academic_years` read/manage codes | Active institution scope and valid academic relationships. Batch changes currently map to department permissions. |
| Faculty assignments | `faculty.assignments.read/manage` | Explicit management authority; target faculty, institution, section, validity, and revocation checks. |
| HOD / Class In-Charge | `academic.class.read`, `academic.department.read`, `academic.reports.read`, `attendance.overview.read` where granted by a definition | Valid responsibility scope and interval. No global expansion of the caller's permissions. |
| Attendance | `attendance.read/manage/own.read` | Students read their own eligible records. Faculty writes require valid teaching scope. Updates, imports, reports, and deletions need independent authorization. |
| Examination / test results | `results.read/manage/own.read` | Own-record student access; authorized academic scope for management; publication/release policy and mutation audit must be explicit. |
| Notices | `notices.read/create/update/delete` | Audience, institution, lifecycle, and permitted write actions. A read permission does not authorize publication or editing. |
| Documents / learning resources | `documents.read/create/update/delete` | Private object access, document ownership, institutional provenance, and audience visibility must be preserved. |
| FAQs / knowledge | `ai.knowledge.read/create/update/delete` | Approved content scope and source visibility. Admin FAQ routes reuse knowledge permissions; no `faqs.*` catalog is established here. |
| Knowledge ingestion | `ai.knowledge.create` and applicable document controls | Authorize each processing phase and preserve the source institution and visibility through extraction, chunking, and embedding. |
| Authenticated AI chat | `ai.chat` | Own conversations, approved retrieval scope, and independent authorization for protected tool actions. |
| Public AI chat | Public endpoint policy | Only explicitly public and eligible knowledge; retain request-size, abuse, and conversation-access controls. |
| Notifications | `notifications.own.read/update` | Own notifications and supported read-state actions; no cross-user identifiers supplied as authority. |
| Institution settings | `institution.read/update/settings.manage` | The caller's authorized institution; sensitive configuration follows management policy. |
| Platform institutions | `platform.read/manage`, relevant `institutions.*` codes | Active `super_admin` platform grant and endpoint-specific policy. Institutional Admin does not acquire platform scope. |
| Audit and security | `audit.read`, `platform.audit.read`, relevant settings permissions | Authorized institution or platform investigation context; separate read access from security configuration changes. |

### Official-register verification and identity repair

These workflows require a separate, explicitly reviewed authority model. Register number is the required academic identifier and university roll number is optional in the supplied policy context. Evidence must be private, decisions attributable, and repairs controlled by the required independent review process.

Do not assume that `students.update`, a Students sidebar entry, or a generic document-upload permission authorizes formal identity verification or identity repair. A dedicated verification permission and its endpoint coverage are not established by the inspected catalog. Restricted B05/E23 artifacts remain out of scope, and this document resolves none of their outstanding owner decisions.

### AI retrieval

Authorization filtering MUST occur before protected content enters model context. Generated answers cannot establish identity, expand permissions, approve users, or justify a protected tool call. Public and authenticated conversation histories must remain separated. Source inspection identifies a public-knowledge policy and repository boundary; complete retrieval isolation remains unverified. **S21**
