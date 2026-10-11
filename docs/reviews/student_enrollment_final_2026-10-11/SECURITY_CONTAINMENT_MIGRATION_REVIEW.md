# Security containment migration candidate review

Prepared 2026-10-11 (Asia/Calcutta). **REVIEW-ONLY — NOT FOR EXECUTION. Not PostgreSQL-validated.** The minimum containment statements are concrete for review, but installation/acceptance is blocked. No SQL, database/catalog connection, Docker, application/harness test, external service, push or deployment occurred. Both unconditional exceptions and final `ROLLBACK` are intentional.

[Candidate SQL](SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql), [candidate results](SECURITY_CONTAINMENT_CANDIDATE_RESULTS.json), [approved plan](SECURITY_CONTAINMENT_CHANGE_PLAN.md), [containment review](SECURITY_CONTAINMENT_REVIEW.md), [original static evidence](SECURITY_CONTAINMENT_STATIC_RESULTS.json), [SQL repair review](SQL_REPAIR_REVIEW.md), [security review](STUDENT_ENROLLMENT_SECURITY_REVIEW.md) and [unchanged enrollment draft](student_enrollment_schema_review_draft.sql) establish scope. The user's follow-up explicitly authorizes exactly `public.security_containment_prevent_audit_truncate()` for the distinct audit TRUNCATE guard. No other new helper is created. The helper has no business permission or external consumer.

## Ordered operation and compatibility profiles

Every top-level statement has a C identifier. Each inventory row below inherits its profile, exact-object evidence and required tests. Dynamic statements are explicitly inventoried: the audit block has three column-ACL templates; the stage-5 block has five table/column/RLS/master templates limited to 20 literal table names (master branches to eight). JSON expands every dynamic table mutation target; columns mean all live, non-dropped columns in those approved objects, subject to later source/catalog comparison B04. No table name comes from a request, regex wildcard or catalog schema sweep.

All REVOKEs use RESTRICT. A dependent onward grant causes failure; CASCADE is not used to remove unreviewed dependencies. Grants and revokes occur in one proposed transaction following the exact stage order: assumptions, defaults, six RPCs/helper clients, audit, authority/academic tables, deferred body assessment, postflight. Nothing is installed by this review.

| Profile | Existing source behavior / proposed statement | PUBLIC / anon / authenticated | service_role / owner and consumers | Recovery / tests |
| --- | --- | --- | --- | --- |
| transaction | BEGIN, unconditional review stop, unconditional B01-B07 stop, local catalog search path/timeouts, final ROLLBACK. No commit/reload/ledger write. | No added capability. | postgres migration executor only; no human JWT/GUC manipulation. | Whole transaction aborts on any failure; executable successor needs exact-byte approval and deliberate transaction behavior. All applicable tests. |
| preflight | PostgreSQL 17/postgres executor/owners; exact 39 ledger versions; ordinary non-partition/non-inherited tables; known ACL grantee/grantor sets; no client permissive policies; required service DML; audit 11-column/type/non-null/default and PK/check/restrictive-FK shape; sensitive routine result/language/default counts; exact signature/overload sets; 17 retained guard bindings; new guard-name absence. Ledger versions alone do not attest applied bytes. | Reject privileged inherited/settable roles and unreviewed policy bridges. Source grants are not today's effective ACLs. | **Conditional BYPASSRLS branch only**, pending B01. Existing direct service helper/entry grants required independently of PUBLIC. No non-bypass policy is guessed. | Compare catalog/applicable source hashes, column layout, policy and function/trigger definitions externally in later approved collection. Fail on unknown variants. T01,T05-T12. |
| defaults | Baseline explicitly grants public future function EXECUTE to clients and service; builtin/global PUBLIC is independent. Revoke postgres global PUBLIC EXECUTE and postgres/public anon/authenticated defaults. Existing objects and replacements keep ACLs. | Deny those future defaults; global direct client or schema PUBLIC defaults outside source cause a blocker, not extra mutation. | Existing service ACLs unchanged. Automatic public service default **retained pending B02**; new guard explicitly revokes it. Owner retained. | Accept global future effect on other schemas/extensions/creator pipelines B03. No table/sequence defaults or other creators changed. Keep safe client defaults on recovery. T05,T07,T12. |
| rpc | Six sensitive signatures have PUBLIC-only source revokes; later resolver replacement keeps old ACL. Exact client revoke plus explicit existing service EXECUTE. No body/drop/default/result change. | Deny each exact signature; postflight covers PUBLIC/direct/inherited/SET privileges. No assertion that all other RPC bridges are repaired. | Both invitation paths, worker leases/completion/context and verified Mailgun reconciliation retain access. Existing human actor/request-role boundary remains. | Preserve client denial during recovery; repair only needed reviewed service EXECUTE. Tests T06-T08,T12. |
| helper | Eighteen source-inventoried trigger-returning helper identities lack complete explicit client denial. Revoke client EXECUTE only; no service revoke/regrant, body replacement or search-path change. | Direct EXECUTE denied; RETURNS trigger is not ordinary RPC reachability. | Existing service helpers/default-origin direct ACLs, owner nesting and trigger bindings retained. Existing invoker nested calls retain grants. | Missing direct service grant or unknown overload blocks rather than guessing. Trigger creation/invocation and nested calls T07,T11-T12. |
| audit | Admin-1 ALL and later Phase 10 broad service DML leave destructive/utility audit grants. Phase 8.1 rejects populated row UPDATE/DELETE, not TRUNCATE. Revoke destructive/utility grants, independent UPDATE/REFERENCES columns and all service SELECT/INSERT delegation options; deny client tables/columns; retain SELECT/INSERT; enable RLS. | No table/column/utility access. No new client permissive policy, existing unexpected policies fail. | Effective SELECT/INSERT only; no UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER/PG17 MAINTAIN or grant options. Row guard, audit PK/checks/FKs/defaults/institution column untouched. BYPASS contract pending B01. | Direct trusted INSERT can supply provenance; ACLs do not authenticate humans. Denial-preserving recovery only; retention/reset B06. T01-T04,T12; zero-row mutation is not immutability proof. |
| newguard | Exactly one authorized invoker helper always raises 42501; empty search_path. Revoke PUBLIC/client/service EXECUTE immediately after creation, then bind separate BEFORE TRUNCATE FOR EACH STATEMENT trigger. | No helper EXECUTE or audit TRUNCATE. | postgres creator/owner only. Owner binds trigger without a service helper grant; existing row guard unchanged. Service TRUNCATE denied by ACL, ordinary owner TRUNCATE rejected even for an empty ledger. | Owner/superuser can disable/replace guards: trusted maintenance boundary. Never disable for tests/retention. T03,T07, including cascade fixture and transaction rollback. |
| table_acl | Seven authority, five legacy academic and eight master tables: table/client independent SELECT/INSERT/UPDATE/REFERENCES column denial; enable/reassert RLS. Masters also reassert DELETE/TRUNCATE denial and SELECT/INSERT/UPDATE service grants, following source. | Deny reads/writes/utilities, including valid-shaped unauthorized authority grants. RLS is not utility/TRUNCATE protection. | Preserve authority/legacy service DML and all scope/tenant/ancestry/integrity guards. No global service revoke or speculative policy. Masters retain other existing service utilities outside this approved narrowing. | Unknown inherited/settable/view/RPC bridges remain blockers; no membership alteration. Preserve client denials on recovery; only review safe service policies/grants. T09-T12,T14; historical/context/calendar/publication adapters separate. |
| postflight | Effective table/column/client/PUBLIC/inherited/SET checks; audit utility/options denial; backend DML; exact overloads; old/new guard bindings; owner-only helper; source service entry points and private implementation; global/schema defaults. | Reject unexpected grants/bridges. No incidental repair of unreviewed roles/policies/objects. | Six/seven/18-helper access and preserved service commands retained; renamed assignment original stays service-denied. | Assertions do not prove policy/body/view/RPC/claim/concurrency semantics. Later definition comparison and role/populated/runtime tests required. T01-T12,T14. |

## Exact objects, source evidence and required consumers

Underlying source sections were inspected directly for relevant declarations, guards, grants and backend calls. All 39 migration hashes were rechecked. Fingerprints alone do not mean every inventoried file was read semantically. Source behavior is not current effective privilege evidence.

| Exact table (all live columns also reviewed for independent ACL denial) | Supporting migration / existing contract | Backend consumers retaining service access | Profile |
| --- | --- | --- | --- |
| `public.admin_audit_log` | [20260909000000_phase_admin_1_admin_student_schema.sql:479](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L479); [20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql:505](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L505) | [admin_audit.py:24](../../../backend/app/repositories/admin_audit.py#L24) INSERT/SELECT; all atomic SQL audited commands | audit |
| `public.users` | [20250717000000_reconstructed_pre_phase_3_6_baseline.sql:346](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L346) | [supabase.py:40](../../../backend/app/db/supabase.py#L40) identity/roles/permissions; [phase81_rbac.py:127](../../../backend/app/services/phase81_rbac.py#L127) grants; [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) assignments/cleanup | table_acl |
| `public.user_roles` | [20250717000000_reconstructed_pre_phase_3_6_baseline.sql:346](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L346) | [supabase.py:40](../../../backend/app/db/supabase.py#L40) identity/roles/permissions; [phase81_rbac.py:127](../../../backend/app/services/phase81_rbac.py#L127) grants; [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) assignments/cleanup | table_acl |
| `public.roles` | [20250717000000_reconstructed_pre_phase_3_6_baseline.sql:346](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L346) | [supabase.py:40](../../../backend/app/db/supabase.py#L40) identity/roles/permissions; [phase81_rbac.py:127](../../../backend/app/services/phase81_rbac.py#L127) grants; [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) assignments/cleanup | table_acl |
| `public.role_permissions` | [20250717000000_reconstructed_pre_phase_3_6_baseline.sql:346](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L346) | [supabase.py:40](../../../backend/app/db/supabase.py#L40) identity/roles/permissions; [phase81_rbac.py:127](../../../backend/app/services/phase81_rbac.py#L127) grants; [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) assignments/cleanup | table_acl |
| `public.permissions` | [20250717000000_reconstructed_pre_phase_3_6_baseline.sql:346](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L346) | [supabase.py:40](../../../backend/app/db/supabase.py#L40) identity/roles/permissions; [phase81_rbac.py:127](../../../backend/app/services/phase81_rbac.py#L127) grants; [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) assignments/cleanup | table_acl |
| `public.institutions` | [20250717000000_reconstructed_pre_phase_3_6_baseline.sql:346](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L346) | [supabase.py:40](../../../backend/app/db/supabase.py#L40) identity/roles/permissions; [phase81_rbac.py:127](../../../backend/app/services/phase81_rbac.py#L127) grants; [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) assignments/cleanup | table_acl |
| `public.user_permission_grants` | [20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql:47](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L47) | [supabase.py:40](../../../backend/app/db/supabase.py#L40) identity/roles/permissions; [phase81_rbac.py:127](../../../backend/app/services/phase81_rbac.py#L127) grants; [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) assignments/cleanup | table_acl |
| `public.students` | [20260909000000_phase_admin_1_admin_student_schema.sql:41](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L41) | [results.py](../../../backend/app/repositories/results.py) legacy reads/CRUD or notification read-mark; [supabase.py:40](../../../backend/app/db/supabase.py#L40) student identity | table_acl |
| `public.student_attendance` | [20260909000000_phase_admin_1_admin_student_schema.sql:41](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L41) | [attendance.py](../../../backend/app/repositories/attendance.py) legacy reads/CRUD or notification read-mark; [supabase.py:40](../../../backend/app/db/supabase.py#L40) student identity | table_acl |
| `public.student_results` | [20260909000000_phase_admin_1_admin_student_schema.sql:41](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L41) | [results.py](../../../backend/app/repositories/results.py) legacy reads/CRUD or notification read-mark; [supabase.py:40](../../../backend/app/db/supabase.py#L40) student identity | table_acl |
| `public.student_result_items` | [20260909000000_phase_admin_1_admin_student_schema.sql:41](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L41) | [results.py](../../../backend/app/repositories/results.py) legacy reads/CRUD or notification read-mark; [supabase.py:40](../../../backend/app/db/supabase.py#L40) student identity | table_acl |
| `public.student_notifications` | [20260914000000_phase_6_11_student_notifications.sql:83](../../../supabase/migrations/20260914000000_phase_6_11_student_notifications.sql#L83) | [student_notifications.py](../../../backend/app/repositories/student_notifications.py) legacy reads/CRUD or notification read-mark; [supabase.py:40](../../../backend/app/db/supabase.py#L40) student identity | table_acl |
| `public.departments` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |
| `public.programs` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |
| `public.courses` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |
| `public.academic_years` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |
| `public.semesters` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |
| `public.program_courses` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |
| `public.course_offerings` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |
| `public.sections` | [20261016000000_academic_master_data_management.sql:155](../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155) RLS/grants/ancestry guard; [20250717000000_reconstructed_pre_phase_3_6_baseline.sql](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql) | [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) master save/read; [phase81_rbac.py:18](../../../backend/app/services/phase81_rbac.py#L18) ancestry reads | table_acl |

Audit source [20260909000000_phase_admin_1_admin_student_schema.sql:566](../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L566) grants ALL; [20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql:40](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L40) adds nullable restrictive institution FK; [20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql:123](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L123) INSERT does not subtract earlier ALL; [20261010000000_phase_10_faculty_attendance_management.sql:197](../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L197) regrants broad service DML. Audit row immutability is [20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql:505](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L505). Creator defaults are [20250717000000_reconstructed_pre_phase_3_6_baseline.sql:1172](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L1172). Final targeted containment must follow the full chain; future blanket regrants can reopen access.

| Exact signature | Declaration / source ACL behavior | Required consumer / compatibility | Profile |
| --- | --- | --- | --- |
| `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)` | [20261002000000_phase_7_17_email_outbox_worker.sql:139](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L139); PUBLIC-only revoke and explicit service grant | [platform_admin_invitations.py:265](../../../backend/app/repositories/platform_admin_invitations.py#L265): six-argument admin invitation, fixed server role/protected token | rpc |
| `public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)` | [20261002000000_phase_7_17_email_outbox_worker.sql:180](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L180); PUBLIC-only revoke and explicit service grant | [platform_admin_invitations.py:319](../../../backend/app/repositories/platform_admin_invitations.py#L319): locked resend/token rotation | rpc |
| `public.phase717_claim_email_outbox(integer,integer,integer)` | [20261002000000_phase_7_17_email_outbox_worker.sql:260](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L260); PUBLIC-only revoke and explicit service grant | [email_outbox.py:23](../../../backend/app/repositories/email_outbox.py#L23): worker claim leases and protected-token row result | rpc |
| `public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)` | [20261002000000_phase_7_17_email_outbox_worker.sql:344](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L344); PUBLIC-only revoke and explicit service grant | [email_outbox.py:58](../../../backend/app/repositories/email_outbox.py#L58): attempt completion/idempotency, three default optional arguments retained | rpc |
| `public.phase717_resolve_email_outbox_context(uuid,text)` | [20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql:71](../../../supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql#L71); PUBLIC-only revoke and explicit service grant | [email_outbox.py:38](../../../backend/app/repositories/email_outbox.py#L38): processing/current-token context; resolver replacement preserved | rpc |
| `public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)` | [20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql:55](../../../supabase/migrations/20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql#L55); PUBLIC-only revoke and explicit service grant | [email_outbox.py:87](../../../backend/app/repositories/email_outbox.py#L87): verified-event replay/delivery reconciliation | rpc |
| `public.faculty_assignment_touch()` | [20261011000000_faculty_responsibilities_and_validity.sql:189](../../../supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql#L189); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.faculty_attendance_context_guard()` | [20261012000000_faculty_attendance_workflow.sql:10](../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L10); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.faculty_attendance_record_scope_guard()` | [20261010000000_phase_10_faculty_attendance_management.sql:173](../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L173); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.faculty_attendance_set_updated_at()` | [20261010000000_phase_10_faculty_attendance_management.sql:91](../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L91); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.faculty_responsibility_scope_guard()` | [20261011000000_faculty_responsibilities_and_validity.sql:84](../../../supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql#L84); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.phase613_assert_child_organization()` | [20260915000000_phase_6_13_organization_institution_tenancy.sql:720](../../../supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql#L720); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for authority scope/status/organization integrity; service grants and dependencies untouched | helper |
| `public.phase613_assert_role_scope()` | [20260915000000_phase_6_13_organization_institution_tenancy.sql:764](../../../supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql#L764); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for authority scope/status/organization integrity; service grants and dependencies untouched | helper |
| `public.phase613_sync_institution_status()` | [20260915000000_phase_6_13_organization_institution_tenancy.sql:305](../../../supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql#L305); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for authority scope/status/organization integrity; service grants and dependencies untouched | helper |
| `public.phase712_assert_super_admin_scope()` | [20261001000000_phase_7_12_super_admin_identity_authorization.sql:23](../../../supabase/migrations/20261001000000_phase_7_12_super_admin_identity_authorization.sql#L23); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for authority scope/status/organization integrity; service grants and dependencies untouched | helper |
| `public.phase714_assert_invitation_transition()` | [20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql:116](../../../supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql#L116); PUBLIC-only revoke | Existing bound triggers/owner/service nesting for invitation/outbox lifecycle; service grants and dependencies untouched | helper |
| `public.phase715_assert_invitation_transition()` | [20261001030000_phase_7_15_invitation_delivery_email_verification.sql:125](../../../supabase/migrations/20261001030000_phase_7_15_invitation_delivery_email_verification.sql#L125); PUBLIC-only revoke | Existing bound triggers/owner/service nesting for invitation/outbox lifecycle; service grants and dependencies untouched | helper |
| `public.phase717_cancel_terminal_invitation_email()` | [20261002000000_phase_7_17_email_outbox_worker.sql:112](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L112); PUBLIC-only revoke | Existing bound triggers/owner/service nesting for invitation/outbox lifecycle; service grants and dependencies untouched | helper |
| `public.phase81_prevent_audit_mutation()` | [20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql:505](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L505); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for audit row mutation rejection; service grants and dependencies untouched | helper |
| `public.reconcile_faculty_attendance_roster_student()` | [20261012000000_faculty_attendance_workflow.sql:289](../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L289); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.student_attendance_tenant_guard()` | [20260913000000_phase_6_7_attendance.sql:82](../../../supabase/migrations/20260913000000_phase_6_7_attendance.sql#L82); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.student_results_tenant_guard()` | [20260913010000_phase_6_8_results.sql:249](../../../supabase/migrations/20260913010000_phase_6_8_results.sql#L249); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.test_results_tenant_guard()` | [20261013000000_faculty_tests_examination.sql:388](../../../supabase/migrations/20261013000000_faculty_tests_examination.sql#L388); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.trg_student_notifications_tenant_guard()` | [20260914000000_phase_6_11_student_notifications.sql:83](../../../supabase/migrations/20260914000000_phase_6_11_student_notifications.sql#L83); creator/default-dependent ACL | Existing bound triggers/owner/service nesting for academic/faculty integrity or roster reconciliation; service grants and dependencies untouched | helper |
| `public.security_containment_prevent_audit_truncate()` | New; specific user authorization for SC-01 only | Owner-only rejecting `public.admin_audit_log.security_containment_admin_audit_no_truncate`; no external consumer | newguard |

The helper allowlist includes trigger helpers on adjacent faculty/test/roster tables, as authorized by the source inventory; only those exact helper client ACLs change. This does not expand table ACL scope. Old `phase714_assert_invitation_transition()` is retained even if no longer bound after Phase 7.15. No permission/role/new business helper is invented.

The distinct seven-argument signature is unchanged: `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)`. [20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql:20](../../../supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql#L20) creates it and explicitly denies clients; the nested legacy approval calls seven arguments. The six-argument backend call still works. Resolver replacement at line 71 does not reset ACLs. Mailgun [mailgun_webhooks.py:29](../../../backend/app/api/mailgun_webhooks.py#L29) parses/verifies before DB reconciliation; [mailgun_webhooks.py:59](../../../backend/app/services/mailgun_webhooks.py#L59) performs freshness/HMAC validation. SQL argument checks do not verify provider HMAC.

Audit SELECT/INSERT remains for [admin_audit.py:24](../../../backend/app/repositories/admin_audit.py#L24) and SQL definers. Existing guard/constraint/default/column definitions are not changed. Later catalog comparison must confirm exact body and constraint/default/FK definitions, not merely counts/binding presence. A failed audit INSERT in existing SQL still aborts state mutation. This package does not make multi-request backend CRUD newly transactional.

## Preserved source workflows and separate security assessment

| Actual source call site | Retained access and reason |
| --- | --- |
| [supabase.py:20](../../../backend/app/db/supabase.py#L20) | Cached secret-backed admin client documents BYPASSRLS; actual target role/claims still B01. No end-user Authorization mutation. |
| [security.py:99](../../../backend/app/core/security.py#L99) | Verified JWT sub resolves public identity, active status, scoped roles/permissions server-side. Actor UUID is not independent human proof. |
| [phase81_rbac.py:203](../../../backend/app/services/phase81_rbac.py#L203) | Staff grant/revoke supplies internal actor and existing permission list; Phase 8.1 service assertion/scoped checks unchanged. |
| [platform_admin_invitations.py:730](../../../backend/app/services/platform_admin_invitations.py#L730) | One-time verified invitation claim precedes actor=target assignment; trusted self-acceptance preserved. |
| [tenancy.py:837](../../../backend/app/repositories/tenancy.py#L837) | Staff/faculty audited role assignment and scoped role cleanup deletes retained. |
| [platform_institutions.py:348](../../../backend/app/repositories/platform_institutions.py#L348) | Audited institution-admin assignment uses existing service-only RPC. |
| [auth_security.py:104](../../../backend/app/services/auth_security.py#L104) | Recovery fingerprints verified session before calling already client-denied consumer; no signature/body/default change. |
| [super_admin_registration.py:244](../../../backend/app/services/super_admin_registration.py#L244) | Existing super-admin assignment RPC and backend platform checks retained. |
| [faculty_attendance.py:538](../../../backend/app/services/faculty_attendance.py#L538) | Dynamic wrapper mark/stage/review/commit uses fixed internal fields; actor/tenant merge assumption retained. Reconciliation reads academic context and audits. |
| [faculty_tests.py:28](../../../backend/app/services/faculty_tests.py#L28) | Wrapper overwrites actor/tenant with user context; save/marks/transition/stage/review/commit stay service-executable. collegeai.test_write, roster/publication guards preserved. |
| [faculty_responsibilities.py:273](../../../backend/app/services/faculty_responsibilities.py#L273) | Scoped teaching/responsibility/validity/create-teaching calls keep existing service-only entry ACLs and helper nesting. |
| [academic_setup.py:103](../../../backend/app/services/academic_setup.py#L103) | Scoped master save supplies internal actor/tenant; source ancestry, calendar locks and atomic audit behavior retained. |
| [results.py:227](../../../backend/app/repositories/results.py#L227) | Summary/item inserts, item replacement/deletion and summary compensation need existing service DML. |
| [attendance.py:99](../../../backend/app/repositories/attendance.py#L99) | Scoped attendance CRUD and current tenant guard retained. |
| [student_notifications.py:119](../../../backend/app/repositories/student_notifications.py#L119) | Own/server-authorized read-mark UPDATE and INSERT/SELECT retained. |
| [vector_search.py:57](../../../backend/app/repositories/vector_search.py#L57) | Private knowledge retrieval retains existing eight-input invoker/service-only function grant; no unrelated revoke. |
| [public_knowledge.py:86](../../../backend/app/repositories/public_knowledge.py#L86) | Public HTTP retrieval retains backend five-input service-only SQL function; no direct client EXECUTE required. |

The renamed private `public.phase81_manage_faculty_section_assignment_original(uuid,uuid,uuid,uuid,boolean)` remains PUBLIC/client/service-denied, preserving owner-nested replacement use ([20261011000000_faculty_responsibilities_and_validity.sql:281](../../../supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql#L281)). [20261014000000_scoped_faculty_teaching_assignment_management.sql:54](../../../supabase/migrations/20261014000000_scoped_faculty_teaching_assignment_management.sql#L54) and [20261009000000_phase_7_24_immediate_staff_faculty_approval.sql:5](../../../supabase/migrations/20261009000000_phase_7_24_immediate_staff_faculty_approval.sql#L5) retain service/scoped assertions. Recovery [20261007000000_phase_9_auth_security_events.sql:56](../../../supabase/migrations/20261007000000_phase_9_auth_security_events.sql#L56), knowledge [20260905000002_phase_3_8_metadata_access_filtering.sql:76](../../../supabase/migrations/20260905000002_phase_3_8_metadata_access_filtering.sql#L76) and [20260928000000_phase_7_2_public_knowledge_policy.sql:96](../../../supabase/migrations/20260928000000_phase_7_2_public_knowledge_policy.sql#L96) retain their exact current ACLs.

SC-06/SC-07 command-context/schema/body hardening is separately reviewed stage 6; it may be a second candidate under the plan and is not implemented here. Its assessment/order remains required for full definer-security acceptance. Existing unsafe name lookup is not fixed by changing search_path on unqualified bodies. Trigger ancestry helpers are not human authorization gates. No actor/JWT/role membership change, bypass GUC, integrity trigger disablement or duplicate master guard is added.

Additional creators, schema CREATE, platform audit ledgers, `test_results`/`faculty_tests`/`test_types` table PUBLIC/column repair and assignment/responsibility table effective-denial assertion expansion remain outside this candidate. Unexpected exposure undermining listed authority blocks acceptance for a separately scoped repair. Future service helper default removal B02 is not authored until its explicit grant contract is accepted; client/global default repair does not imply new future helpers are service-private. New enrollment functions already plan transactional revoke-all/regrant-two, but no enrollment objects are bundled here.

## Statement inventory

Every row applies its profile above, exact object evidence and tests. The two ACL DO blocks are expanded per exact table/template in JSON. Pre/postflight read catalog metadata only; they do not dump payloads/credentials and have not run. Prior catalog/ACL/policy/trigger comparison evidence must be collected in a later explicitly authorized phase; these assertions are not a replacement for that collection.

| ID | Stage | Exact object / signature | Proposed purpose | Profile | Later tests |
| --- | ---: | --- | --- | --- | --- |
| C001 | 0 | `transaction` | begin | transaction | all |
| C002 | 0 | `transaction` | unconditional review stop | transaction | all |
| C003 | 0 | `transaction` | unresolved compatibility stop | transaction | all |
| C004 | 1 | `session` | catalog-only search path | transaction | all |
| C005 | 1 | `session` | lock timeout | transaction | all |
| C006 | 1 | `session` | statement timeout | transaction | all |
| C007 | 1 | `approved existing table/routine/role/ledger catalog` | fail-closed preflight | preflight | T01,T05-T12 |
| C008 | 2 | `postgres/global future functions` | remove global PUBLIC default | defaults | T05 |
| C009 | 2 | `postgres/public future functions` | remove direct client defaults | defaults | T05 |
| C010 | 3 | `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)` | exact client EXECUTE denial | rpc | T06-T08,T12 |
| C011 | 3 | `public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)` | retain explicit service EXECUTE | rpc | T06-T08,T12 |
| C012 | 3 | `public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)` | exact client EXECUTE denial | rpc | T06-T08,T12 |
| C013 | 3 | `public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)` | retain explicit service EXECUTE | rpc | T06-T08,T12 |
| C014 | 3 | `public.phase717_claim_email_outbox(integer,integer,integer)` | exact client EXECUTE denial | rpc | T06-T08,T12 |
| C015 | 3 | `public.phase717_claim_email_outbox(integer,integer,integer)` | retain explicit service EXECUTE | rpc | T06-T08,T12 |
| C016 | 3 | `public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)` | exact client EXECUTE denial | rpc | T06-T08,T12 |
| C017 | 3 | `public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)` | retain explicit service EXECUTE | rpc | T06-T08,T12 |
| C018 | 3 | `public.phase717_resolve_email_outbox_context(uuid,text)` | exact client EXECUTE denial | rpc | T06-T08,T12 |
| C019 | 3 | `public.phase717_resolve_email_outbox_context(uuid,text)` | retain explicit service EXECUTE | rpc | T06-T08,T12 |
| C020 | 3 | `public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)` | exact client EXECUTE denial | rpc | T06-T08,T12 |
| C021 | 3 | `public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)` | retain explicit service EXECUTE | rpc | T06-T08,T12 |
| C022 | 3 | `public.faculty_assignment_touch()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C023 | 3 | `public.faculty_attendance_context_guard()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C024 | 3 | `public.faculty_attendance_record_scope_guard()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C025 | 3 | `public.faculty_attendance_set_updated_at()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C026 | 3 | `public.faculty_responsibility_scope_guard()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C027 | 3 | `public.phase613_assert_child_organization()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C028 | 3 | `public.phase613_assert_role_scope()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C029 | 3 | `public.phase613_sync_institution_status()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C030 | 3 | `public.phase712_assert_super_admin_scope()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C031 | 3 | `public.phase714_assert_invitation_transition()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C032 | 3 | `public.phase715_assert_invitation_transition()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C033 | 3 | `public.phase717_cancel_terminal_invitation_email()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C034 | 3 | `public.phase81_prevent_audit_mutation()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C035 | 3 | `public.reconcile_faculty_attendance_roster_student()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C036 | 3 | `public.student_attendance_tenant_guard()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C037 | 3 | `public.student_results_tenant_guard()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C038 | 3 | `public.test_results_tenant_guard()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C039 | 3 | `public.trg_student_notifications_tenant_guard()` | exact client helper EXECUTE denial | helper | T07,T11-T12 |
| C040 | 4 | `public.admin_audit_log` | deny client table access | audit | T01-T04 |
| C041 | 4 | `public.admin_audit_log` | deny service destructive and utility privileges | audit | T01-T04 |
| C042 | 4 | `public.admin_audit_log` | remove service delegation options | audit | T01-T04 |
| C043 | 4 | `public.admin_audit_log.<each live column>` | deny independent column access/delegation | audit | T01-T04 |
| C044 | 4 | `public.admin_audit_log` | retain backend read/append | audit | T04,T12 |
| C045 | 4 | `public.admin_audit_log` | enable RLS conditional accepted BYPASSRLS branch | audit | T01,T04 |
| C046 | 4 | `public.security_containment_prevent_audit_truncate()` | create authorized owner-only rejecting helper | newguard | T03,T07 |
| C047 | 4 | `public.security_containment_prevent_audit_truncate()` | remove every client/service default EXECUTE grant | newguard | T03,T07 |
| C048 | 4 | `public.admin_audit_log.security_containment_admin_audit_no_truncate` | bind distinct rejecting statement TRUNCATE guard | newguard | T03,T07 |
| C049 | 5 | `20 explicitly listed authority/legacy/master tables and their live columns` | targeted table/column/RLS containment; master grants | table_acl | T09-T12 |
| C050 | 7 | `exact reviewed catalog allowlist` | effective ACL/default/guard postflight | postflight | T01-T12,T14 |
| C051 | 8 | `transaction` | final review rollback | transaction | all |

## Unresolved dependencies, recovery and next approval

- **B01:** Accept and validate actual service JWT/secret-key claims, BYPASSRLS/owner/membership contract and RLS policies. Non-BYPASSRLS needs a separate reviewed policy variant.
- **B02:** Removal of postgres/public automatic future service EXECUTE remains blocked on an explicit future command/helper/trigger grant contract. No removal statement included.
- **B03:** Accept global postgres PUBLIC default effects on other schemas/extensions; identify actual creators. Additional creators/global direct client/schema PUBLIC defaults need additional exact scope.
- **B04:** Current authorized catalog/ledger/applied-byte/ACL/column/inherited/settable/view/RPC comparison absent. Unknown variants fail rather than broaden scope.
- **B05:** SC-06/SC-07 body/context/schema-hardening assessment and acceptance ordering separate; adjacent ledgers and assignment/responsibility table assertion expansion excluded.
- **B06:** External direct consumers, audit retention/reset maintenance and concurrent revocation/in-flight command policy need acceptance.
- **B07:** Independent exact-byte approval, validated disposable engine/bootstrap/storage/cleanup and dedicated runner/fixtures absent. All PostgreSQL/catalog/role/transaction/concurrency tests pending.

Compatibility rollback must preserve client table/column/routine denial, safe PUBLIC/client defaults and audit destructive/utility denial. Restore only separately reviewed necessary service read/insert/command access or a safe RLS variant. Store prior definitions/ACLs as controlled evidence; do not automatically restore unsafe grants. Audit retention/reset requires a trusted owner procedure, not service mutation privileges or disabling guards to pass tests. Owners/superusers remain able to change protections.

No existing data is changed. ACL/RLS recovery cannot undo previously authorized actions/external deliveries. Concurrent revocation policy, historical ownership/calendar/publication/enrollment adapters remain unresolved outside this package. Containment does not authorize lifecycle cutover.

Next: independent exact-byte/hash review and B01-B07 acceptance, then explicit authorization for catalog collection and defined disposable full-chain/populated role/claim/transaction/concurrency validation after engine/bootstrap/storage/cleanup/harness readiness. An approved executable successor must deliberately resolve both exceptions and transaction behavior while retaining these review artifacts. Production-chain placement, deployment and removal of the enrollment stop require later approvals.

## Checks actually run and limits

Automated bounded source checks: local SHA-256 preservation/source comparison, exact table/signature/overload allowlists, statement ID/order/ACL scope and dynamic templates, immediate new-helper revocation, no blanket/adjacent/enrollment/application mutation, both exceptions/final rollback, Markdown target/line bounds and whitespace. JSON records results and statement hashes. `git diff --check` is recorded separately. The original prior scanner's results are not overwritten or treated as new-byte approval.

Manual review: source behavior/call dependencies; RLS/default/inheritance/security implications; service/owner nesting; guard separation; denial-preserving recovery. Manual reasoning is not automated engine proof. Source inventories are lexical and do not validate PostgreSQL or PL/pgSQL grammar, catalog/function/trigger/policy behavior, request claims or concurrency. T01-T14 remain NOT RUN, with conditional T13 and integration acceptance separately gated.

## Reproduce source-only verification

The Python block below belongs to this required review artifact so no fourth file is needed. From repository root run `python -B` on this block through stdin; it reads local source and rewrites only candidate-results JSON. It loads only definitions before `main()` from the existing bounded lexical scanner, not that scanner's main or any application. No database driver, SQL execution, network or Docker is used.

```python
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path.cwd()
HERE = ROOT / 'docs/reviews/student_enrollment_final_2026-10-11'
RESULT = HERE / 'SECURITY_CONTAINMENT_CANDIDATE_RESULTS.json'
SQL = HERE / 'SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql'
REVIEW = HERE / 'SECURITY_CONTAINMENT_MIGRATION_REVIEW.md'
OUTPUTS = {str(p.relative_to(ROOT)).replace('\\', '/') for p in (RESULT, SQL, REVIEW)}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
d = json.loads(RESULT.read_text(encoding='utf-8'))
prior = json.loads((HERE / 'SECURITY_CONTAINMENT_STATIC_RESULTS.json').read_text(encoding='utf-8'))
ns = {'__file__': str(HERE / 'verify_security_containment_static.py')}
exec((HERE / 'verify_security_containment_static.py').read_text(encoding='utf-8').split('def main():')[0], ns)
scan = ns['statements']
sql = SQL.read_text(encoding='utf-8')
review = REVIEW.read_text(encoding='utf-8')
statements = list(scan(sql))
checks = {}
def check(name, condition):
    checks[name] = bool(condition)

allow_tables = ['admin_audit_log','users','user_roles','roles','role_permissions','permissions','institutions','user_permission_grants','students','student_attendance','student_results','student_result_items','student_notifications','departments','programs','courses','academic_years','semesters','program_courses','course_offerings','sections']
six = ['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)']
source_inventory = {x['signature']: x for x in prior['source_function_inventory']}
helpers = [s for s,x in source_inventory.items() if x['unsafe_default_candidate'] and s not in six]
seven = 'public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)'
new = 'public.security_containment_prevent_audit_truncate()'
check('approved_table_list_exact', d['approved_table_allowlist'] == ['public.'+t for t in allow_tables])
plan = (HERE / 'SECURITY_CONTAINMENT_CHANGE_PLAN.md').read_text(encoding='utf-8')
check('table_list_named_in_approved_plan', all(re.search(r'(?<!\w)'+t+r'\b',plan) for t in allow_tables))
check('six_signature_list_exact', d['approved_sensitive_signatures'] == six)
check('helpers_match_reviewed_source_inventory', d['approved_client_helper_signatures'] == helpers and len(helpers)==18 and all(source_inventory[s]['returns_trigger'] for s in helpers))
check('new_helper_only_authorized_identity', d['authorized_new_helper']==new)
# Inspect underlying migration declarations again, not report summaries alone.
declaration = re.compile(r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([\w".]+)\s*\((.*?)\)\s*RETURNS\b',re.I|re.S)
names = {s.split('(')[0] for s in six+helpers+[seven]}
source_signatures = set()
source_declarations = []
for path in sorted((ROOT / 'supabase/migrations').glob('*.sql')):
    for line, statement in scan(path.read_text(encoding='utf-8')):
        m = declaration.match(statement)
        if m:
            name = m[1] if '.' in m[1] else 'public.'+m[1]
            sig = ns['signature'](name,m[2],True)
            if sig.split('(')[0] in names:
                source_signatures.add(sig)
                source_declarations.append({'source':str(path.relative_to(ROOT)).replace('\\','/'),'line':line,'signature':sig})
check('underlying_source_exact_signatures_and_overload_set',source_signatures==set(six+helpers+[seven]))
markers = list(re.finditer(r'^-- (C\d{3}) \| stage (\d+) \|',sql,re.M))
check('every_statement_has_one_unique_id',len(markers)==len(statements)==len(d['statement_contracts'])==51 and [m[1] for m in markers]==[x['id'] for x in d['statement_contracts']])
check('plan_operation_order', [int(m[2]) for m in markers]==sorted(int(m[2]) for m in markers) and set(int(m[2]) for m in markers)=={0,1,2,3,4,5,7,8})
check('both_unconditional_stops_before_any_privilege_change',statements[0][1]=='BEGIN;' and statements[1][1].startswith('DO $review_stop$ BEGIN RAISE EXCEPTION') and statements[2][1].startswith('DO $dependency_stop$ BEGIN RAISE EXCEPTION'))
check('final_rollback_no_commit',statements[-1][1]=='ROLLBACK;' and not any(re.match(r'COMMIT\b',s,re.I) for _,s in statements))
check('prominent_review_header',all(x in sql[:2000] for x in ['REVIEW-ONLY — NOT FOR EXECUTION','NOT PostgreSQL-validated','Must not be copied into the production migration chain without independent approval','B01-B07']))
acl=[]
for line,s in statements:
    m=re.match(r'(GRANT|REVOKE)\s+(.*?)\s+ON\s+FUNCTION\s+(.*?)\s+(TO|FROM)\s+([^;]+);',s,re.I|re.S)
    if m:
        signature=ns['canonical'](m[3]).replace(' ','')
        roles=[x.strip().lower() for x in re.sub(r'\s+RESTRICT\s*$','',m[5],flags=re.I).split(',')]
        acl.append({'line':line,'operation':m[1].upper(),'privileges':m[2].upper(),'signature':signature,'roles':roles})
check('function_acl_changes_within_exact_allowlist',all(x['signature'] in six+helpers+[new] for x in acl) and len(acl)==31)
check('six_exact_client_revokes_and_service_grants',all(sum(x['signature']==s and x['operation']=='REVOKE' and x['roles']==['public','anon','authenticated'] for x in acl)==1 and sum(x['signature']==s and x['operation']=='GRANT' and x['privileges']=='EXECUTE' and x['roles']==['service_role'] for x in acl)==1 for s in six))
check('helper_clients_only_no_service_mutation',all(sum(x['signature']==s and x['operation']=='REVOKE' and x['roles']==['public','anon','authenticated'] for x in acl)==1 and not any(x['signature']==s and x['operation']=='GRANT' for x in acl) for s in helpers))
new_positions=[i for i,(_,s) in enumerate(statements) if declaration.match(s)]
check('single_new_function_immediate_nonowner_revoke',len(new_positions)==1 and statements[new_positions[0]][1].startswith('CREATE FUNCTION public.security_containment_prevent_audit_truncate()') and statements[new_positions[0]+1][1]==f'REVOKE ALL PRIVILEGES ON FUNCTION {new} FROM PUBLIC, anon, authenticated, service_role RESTRICT;')
check('new_guard_invoker_empty_path_always_raises',"RETURNS pg_catalog.trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''" in sql and "RAISE EXCEPTION 'Audit records cannot be truncated' USING ERRCODE = '42501'" in sql)
check('distinct_statement_truncate_trigger',sum(s.startswith('CREATE TRIGGER security_containment_admin_audit_no_truncate BEFORE TRUNCATE ON public.admin_audit_log FOR EACH STATEMENT EXECUTE FUNCTION public.security_containment_prevent_audit_truncate();') for _,s in statements)==1)
defaults=[s for _,s in statements if s.startswith('ALTER DEFAULT PRIVILEGES')]
check('exact_global_schema_function_default_scope',defaults==['ALTER DEFAULT PRIVILEGES FOR ROLE postgres REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC RESTRICT;','ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM anon, authenticated RESTRICT;'])
check('audit_exact_table_acl_and_rls',all(x in [s for _,s in statements] for x in ['REVOKE ALL PRIVILEGES ON TABLE public.admin_audit_log FROM PUBLIC, anon, authenticated RESTRICT;','REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN ON TABLE public.admin_audit_log FROM service_role RESTRICT;','REVOKE GRANT OPTION FOR SELECT, INSERT ON TABLE public.admin_audit_log FROM service_role RESTRICT;','GRANT SELECT, INSERT ON TABLE public.admin_audit_log TO service_role;','ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;']))
templates=[]
for line,s in statements:
    for m in re.finditer(r"EXECUTE pg_catalog\.format\('([^']+)'",s):
        templates.append({'line':line,'template':m[1]})
expected_templates=[
'REVOKE SELECT (%1$I), INSERT (%1$I), UPDATE (%1$I), REFERENCES (%1$I) ON TABLE public.admin_audit_log FROM PUBLIC, anon, authenticated RESTRICT',
'REVOKE UPDATE (%1$I), REFERENCES (%1$I) ON TABLE public.admin_audit_log FROM service_role RESTRICT',
'REVOKE GRANT OPTION FOR SELECT (%1$I), INSERT (%1$I) ON TABLE public.admin_audit_log FROM service_role RESTRICT',
'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM PUBLIC, anon, authenticated RESTRICT',
'REVOKE SELECT (%1$I), INSERT (%1$I), UPDATE (%1$I), REFERENCES (%1$I) ON TABLE public.%2$I FROM PUBLIC, anon, authenticated RESTRICT',
'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',
'REVOKE DELETE, TRUNCATE ON TABLE public.%I FROM service_role RESTRICT',
'GRANT SELECT, INSERT, UPDATE ON TABLE public.%I TO service_role']
check('every_dynamic_mutation_template_exact', [x['template'] for x in templates]==expected_templates)
table_block=next(s for _,s in statements if s.startswith('DO $table_acl$'))
arrays=re.findall(r"ARRAY\[(.*?)\]::text\[\]",table_block,re.S)
listed=lambda s:re.findall(r"'([^']+)'",s)
check('dynamic_table_allowlist_and_master_branch_exact',len(arrays)==2 and listed(arrays[0])==allow_tables[1:] and listed(arrays[1])==d['master_tables'] and "IF t=ANY(" in table_block)
check('dynamic_columns_bounded_to_named_table_live_columns',all(x in table_block for x in ["attrelid=pg_catalog.to_regclass('public.'||t)",'attnum>0 AND NOT attisdropped','c.attname,t']))
normalized='\n'.join(s for _,s in statements)
check('no_blanket_cascade_body_drop_policy_role_or_data_mutation',not re.search(r'ON\s+ALL\s+(?:TABLES|FUNCTIONS)|\bCASCADE\b|CREATE\s+OR\s+REPLACE|DROP\s+(?:FUNCTION|TRIGGER|TABLE)|CREATE\s+POLICY|ALTER\s+ROLE|DISABLE\s+TRIGGER',normalized,re.I) and not any(re.match(r'(INSERT|UPDATE|DELETE|TRUNCATE|CREATE TABLE)\b',s,re.I) for _,s in statements))
check('all_direct_table_mutation_targets_allowlisted', set(re.findall(r'(?:ON TABLE|ALTER TABLE)\s+public\.([a-z]\w*)',normalized,re.I))=={'admin_audit_log'})
check('all_statements_have_reviewed_operation_shapes', all(re.match(r'(?:BEGIN;|ROLLBACK;|SET LOCAL |DO \$|ALTER DEFAULT PRIVILEGES |GRANT (?:EXECUTE ON FUNCTION|SELECT, INSERT ON TABLE)|REVOKE (?:ALL PRIVILEGES ON (?:FUNCTION|TABLE)|UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN ON TABLE|GRANT OPTION FOR SELECT, INSERT ON TABLE)|ALTER TABLE public\.admin_audit_log ENABLE ROW LEVEL SECURITY|CREATE FUNCTION public\.security_containment_prevent_audit_truncate|CREATE TRIGGER security_containment_admin_audit_no_truncate)',statement,re.I) for _,statement in statements))
check('enrollment_and_adjacent_objects_not_mutation_targets',not any(re.search(r'(?:ON TABLE|ALTER TABLE|CREATE TABLE)\s+public\.(?:student_enrollments|student_academic_placements|student_enrollment_events|student_institution_identifiers|platform_role_audit_log|platform_institution_audit_log|test_results|faculty_tests|test_types)\b',s,re.I) for _,s in statements))
check('service_nonbypass_policy_variant_fails_not_guessed',"Non-BYPASSRLS" in review and "RAISE EXCEPTION 'Unaccepted service RLS mode'" in sql and not re.search(r'CREATE POLICY',normalized,re.I))
check('all_retained_bindings_pre_and_post',len(d['retained_trigger_bindings'])==17 and all(sql.count("('%s','%s','%s',%s)"%(x['table'].split('.')[1],x['trigger'],x['signature'],x['tgtype']))==2 for x in d['retained_trigger_bindings']))
check('all_blockers_documented_and_service_default_removal_blocked',set(d['blockers'])=={'B01','B02','B03','B04','B05','B06','B07'} and all(b in sql and b in review for b in d['blockers']) and 'automatic future service EXECUTE' in review and not any('service_role' in s for s in defaults))
links=[]
prose=re.sub(r'```.*?```','',review,flags=re.S)
for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',prose):
    path,_,anchor=target.partition('#')
    resolved=(HERE/path).resolve()
    ok=resolved.is_file()
    if ok and anchor.startswith('L'):
        ok=anchor[1:].isdigit() and 1<=int(anchor[1:])<=len(resolved.read_text(encoding='utf-8').splitlines())
    links.append({'target':target,'valid':ok})
check('review_links_exist_and_line_bounds_valid',len(links)>30 and all(x['valid'] for x in links))
check('statement_inventory_documented',all('| '+x['id']+' |' in review for x in d['statement_contracts']))
check('new_artifact_no_trailing_whitespace',all(not re.search(r'[ \t]+$',line) for p in (SQL,REVIEW,RESULT) for line in p.read_text(encoding='utf-8').splitlines()))
changes=[p for p,v in d['preservation_baseline'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=v]
check('all_1150_preexisting_files_preserved',len(d['preservation_baseline'])==1150 and not changes)
check('all_39_source_migration_hashes_match',len(d['migration_hashes'])==39 and all(sha(ROOT/p)==v for p,v in d['migration_hashes'].items()))
enrollment=HERE/'student_enrollment_schema_review_draft.sql'
enrollment_text=enrollment.read_text(encoding='utf-8')
check('enrollment_hash_exception_final_rollback_unchanged',sha(enrollment)==d['enrollment_sql_sha256'] and "RAISE EXCEPTION 'REVIEW ONLY: execution requires explicit approval and a new reviewed migration'" in enrollment_text and enrollment_text.rstrip().endswith('ROLLBACK;'))
current=set(d['preservation_baseline'])
current.update(p.decode() for p in subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],stderr=subprocess.DEVNULL).split(b'\0') if p)
unexpected=sorted(p for p in current if p not in d['preservation_baseline'] and p not in OUTPUTS)
check('only_three_requested_new_files',not unexpected and all((ROOT/p).is_file() for p in OUTPUTS))
git_diff=subprocess.run(['git','diff','--check'],capture_output=True,text=True)
check('git_diff_check',git_diff.returncode==0)
d.update(status='review-only; bounded static checks passed' if all(checks.values()) else 'review-only; bounded static failures',automated_checks=checks,automated_checks_passed=all(checks.values()),changed_existing_files=changes,preservation_file_count=len(d['preservation_baseline']),unexpected_new_files=unexpected,source_declaration_checks=source_declarations,function_acl_inventory=acl,dynamic_statement_templates=templates,dynamic_table_statement_expansion=[{'table':'public.'+t,'operations':['client table deny','client independent column deny','enable RLS']+(['service DELETE/TRUNCATE deny','service SELECT/INSERT/UPDATE grant'] if t in d['master_tables'] else [])} for t in allow_tables[1:]],statement_inventory=[dict(c,line=line,sha256=hashlib.sha256(s.encode()).hexdigest(),text=s) for c,(line,s) in zip(d['statement_contracts'],statements)],link_checks=links,artifact_hashes={SQL.name:sha(SQL),REVIEW.name:sha(REVIEW)},results_self_hash='Not embedded: this file cannot contain its own SHA-256; hash externally when approving.',git_diff_check={'returncode':git_diff.returncode,'stdout':git_diff.stdout,'stderr':git_diff.stderr},manual_review={'status':'source reasoning documented; not automated proof','report':REVIEW.name,'areas':['consumer/service dependency trace','RLS/default/inherited/settable boundaries','audit statement guard versus row guard','atomic SQL audit behavior','denial-preserving recovery','B01-B07 unresolved decisions']},method='Comment/quote/dollar-aware lexical statement scanner plus bounded signature/template/order/link/hash assertions; no PostgreSQL parser or effective privilege simulator.',limitations=['No PostgreSQL/PLpgSQL grammar, trigger/function/policy/transaction/concurrency validation.','Source ACLs/defaults do not attest current effective privileges or role/request semantics.','Catalog-only candidate assertions have not run; approved external policy/body/FK/default/bridge comparison remains necessary.','Future automatic service EXECUTE default remains intentionally blocked for separate contract acceptance.'],runtime_validation={f'T{i:02}':'NOT RUN' for i in range(1,15)},reproduce='From repo root: execute the sole Python block in SECURITY_CONTAINMENT_MIGRATION_REVIEW.md with python -B via stdin; rewrites only candidate-results JSON.')
RESULT.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':d['automated_checks_passed'],'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'statements':len(statements),'templates':len(templates),'preserved_files':len(d['preservation_baseline']),'candidate_sha256':sha(SQL),'review_sha256':sha(REVIEW)},indent=2))
if not all(checks.values()): raise SystemExit(1)
```
