# College AI Chatbot — Security Remediation Planning Audit

Audit date: **10 October 2026 (Asia/Calcutta / IST)**  
Status: **Planning report only; implementation is not authorized by this task.**  
Basis: M1_PREFLIGHT_AUDIT_REPORT.md, independently refreshed local catalogs, and the current working tree.  
Recommendation: **Approve a reviewed backend-only remediation design for subsequent local implementation; do not treat this report as implementation or deployment approval.**

## 1. Decision and verified findings

The two scoped critical findings remain present in the local database. All five academic tables have RLS disabled and direct client-role privileges. Six SECURITY DEFINER workflow signatures remain executable by both anon and authenticated, despite PUBLIC having no EXECUTE grant on those signatures. Restricting the seven-argument invitation overload has not restricted the older six-argument overload.

The recommended boundary is **FastAPI/backend access through service_role**, with application authorization enforced before privileged reads and writes. The five tables should deny all direct client access, have RLS enabled, and have no client allow policies. Every overload of the six workflow function names should allow EXECUTE only to the owner and service_role. Preserve the old invitation overload because current backend code uses it.

A related critical dependency was also verified: users, user_roles, roles, role_permissions, permissions, and institutions allow client writes and have RLS disabled. FastAPI reads these resources as authorization authority. Restricting only the five academic tables and six workflow RPCs would therefore leave authorization sources writable. A remediation release must address that dependency or explicitly remain a partial containment release with no claim of complete authorization repair.

| ID | Severity / classification | Finding | Exact evidence |
| --- | --- | --- | --- |
| T1 | Critical; verified permissions | students: RLS off, no policies, anon/authenticated have all eight inventoried table privileges | pg_class OID 19398; Appendix A; migration M1:41, M1:566; get_admin_client S1:20 |
| T2 | Critical; verified permissions | student_attendance: same exposure; its trigger validates relationships rather than caller authority | OID 19549; Appendix A; M1:327, M2:82; attendance S7:98 |
| T3 | Critical; verified permissions | student_results: same exposure, including access unconstrained by publication status | OID 19437; Appendix A; M1:109, M3:249; own-results S5:47 |
| T4 | Critical; verified permissions | student_result_items: same exposure; parent FK does not authorize the caller | OID 19475; Appendix A; M1:183; embedded items and explicit deletion S8:203, S8:256 |
| T5 | Critical; verified permissions | student_notifications: same exposure, allowing bypass of own-student/read-marking checks | OID 19735; Appendix A; M4:21, M4:133; S9:126, S9:151 |
| F1 | Critical; verified ACLs and definitions | Six owner-privileged signatures allow anon/authenticated EXECUTE; all six have PUBLIC EXECUTE=false | Appendix B gives exact signatures/OIDs/ACLs; M5:437, M6:193; Section 4 maps each definition and caller |
| F2 | Compatibility requirement; verified | Seven-argument create overload is restricted; six-argument overload remains installed and is used by the backend | OIDs 20107 and 20062; M7:20, M7:64; S10:249, S10:267 |
| D1 | High; verified defaults, inferred recurrence | public defaults for postgres and supabase_admin grant client table, sequence, and routine access | pg_default_acl: six scoped entries, no global entries; Appendix C; M0:1173 and M0:1174 explicitly add client routine defaults |
| A1 | Critical related dependency; verified permissions, inferred escalation | Client-writeable authorization sources can undermine server-derived role/tenant decisions | Appendix D; S1:52–71, S2:99–140, S3:175–220; scope triggers M8:764 and M9:23 validate shape, not caller entitlement |
| V1 | Audit limitation; verified counts | All five scoped tables, invitations, outbox, attempts, and delivery events are empty | Appendix E; no populated authorization or concurrency behavior was tested |

**Verified:** installed ACLs, effective privilege results, role memberships, RLS flags, policy counts, routine bodies, source behavior and counts.  
**Inferred:** unauthorized Data API access, queue interference, forged delivery events, or role escalation permitted by these configurations.  
**Untested:** credentialed HTTP access, actual exploitation, populated-data behavior, migration execution, real email delivery, and all remote state.

## 2. Read-only scope and provenance

| Item | Observed value |
| --- | --- |
| Workspace | F:/Git Project/CollegeAIChatbot |
| Git HEAD | e4cf26cc555f96991cc74d849b9747744ffefdb7 |
| Local Docker context | desktop-linux |
| Verified endpoint | npipe:////./pipe/dockerDesktopLinuxEngine |
| DOCKER_HOST | Absent; only existence was checked |
| Database container | supabase_db_CollegeAIChatbot |
| Image / PostgreSQL | public.ecr.aws/supabase/postgres:17.6.1.166 / server 17.6 |
| Connection | Container-local socket, database postgres, role postgres; no connection string or password obtained |
| First catalog inspection | 2026-10-10 07:13:52 UTC / 12:43:52 IST |
| Final catalog inspection | 2026-10-10 07:20:03 UTC / 12:50:03 IST |
| Every SQL connection | PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=30000 |
| psql | -X -q -A -t -v ON_ERROR_STOP=1; SELECT/catalog inspection only |
| Read-only verification | Initial and final transaction_read_only=on; default_transaction_read_only=on |
| Local API | public exposed at supabase/config.toml:13; gateway and PostgREST running |
| Local ledger | 39 versions; latest installed version 20261016010000 |
| Guidance | No applicable AGENTS.md found in the workspace or checked ancestors |

Docker access was blocked by the sandbox initially; an approved escalated read-only inspection verified the named local endpoint before querying the database. No Docker environment dump, Supabase status output, environment-file values, credentials, tokens, or record payloads were collected. Routine parameter names and schema field names in this report are metadata.

Static Python parsing/hashing used python -B and did not import application modules or run tests. A fingerprint inventory covers 528 application, test, migration, configuration, and preflight-report files. The original modified FacultyAttendance.tsx and FacultyAttendance.test.tsx and untracked useFacultyAttendanceData.ts and schemaV2_export.sql were preserved. This report is the only intended new artifact.

Queries used separate read-only sessions, not one repeatable-read snapshot. Final counts and the two scoped defect totals were rechecked. Large initial catalog output was replaced with bounded, complete snapshots; initial wildcard/search-path errors were resolved through explicit paths or rg glob filters.

### Exact source and migration key

References such as M5:437 or S1:20 below mean the following exact file and line in the audited working tree.

| Key | File |
| --- | --- |
| M0 | supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql |
| M1 | supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql |
| M2 | supabase/migrations/20260913000000_phase_6_7_attendance.sql |
| M3 | supabase/migrations/20260913010000_phase_6_8_results.sql |
| M4 | supabase/migrations/20260914000000_phase_6_11_student_notifications.sql |
| M5 | supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql |
| M6 | supabase/migrations/20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql |
| M7 | supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql |
| M8 | supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql |
| M9 | supabase/migrations/20261001000000_phase_7_12_super_admin_identity_authorization.sql |
| M10 | supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql |
| M11 | supabase/migrations/20261012000000_faculty_attendance_workflow.sql |
| M12 | supabase/migrations/20261013000000_faculty_tests_examination.sql |
| S1 | backend/app/db/supabase.py |
| S2 | backend/app/core/security.py |
| S3 | backend/app/services/authorization.py |
| S4 | backend/app/services/student_context.py |
| S5 | backend/app/services/student_data.py |
| S6 | backend/app/api/admin.py |
| S7 | backend/app/services/attendance.py |
| S8 | backend/app/repositories/results.py |
| S9 | backend/app/services/student_notifications.py |
| S10 | backend/app/repositories/platform_admin_invitations.py |
| S11 | backend/app/repositories/email_outbox.py |
| S12 | backend/app/services/email_outbox_worker.py |
| S13 | backend/app/services/mailgun_webhooks.py |
| S14 | backend/app/api/mailgun_webhooks.py |
| S15 | backend/app/api/platform.py |
| S16 | backend/app/services/platform_admin_invitations.py |
| S17 | backend/app/api/admin_invitations.py |
| S18 | backend/app/services/faculty_attendance.py |
| S19 | backend/app/services/faculty_tests.py |
| S20 | backend/app/services/student_results.py |

Migration ledger membership confirms installed versions, not equality between historical applied bytes and current files. Live catalogs are the installed-state authority. Do not use either schema export to determine these permissions.

## 3. Intended table access and reviewed table proposal

### Access matrix

The human/application actor and the PostgreSQL role are distinct. A student, faculty member, staff member, or administrator calling FastAPI remains an authenticated application actor; the backend performs permitted database work as service_role. An ordinary authenticated Supabase session is not thereby a trusted database backend.

| Resource | Intended human/backend access | Direct anon / authenticated access | Proposed service_role privileges |
| --- | --- | --- | --- |
| students | Own profile through /students/me; institution admin CRUD/archive; scoped admin/staff approval; validated registration backend may create a pending profile | None, including the caller's own row | SELECT, INSERT, UPDATE, DELETE retained for compatibility; observed normal deletion uses archive/update |
| student_attendance | Own attendance reads; institution admin management; authorized faculty section/roster workflows | None | SELECT, INSERT, UPDATE, DELETE |
| student_results | Own published results; institution admin management/import; draft and withheld data remain privileged | None | SELECT, INSERT, UPDATE, DELETE |
| student_result_items | Access follows the authorized parent result; backend creates items and explicitly deletes them when deleting a result | None; absence of institution_id does not make items public | SELECT, INSERT, UPDATE, DELETE retained; inspected code uses SELECT/INSERT/DELETE |
| student_notifications | Own list/detail/count; own mark-read; authoritative academic/backend events create notifications | None | SELECT, INSERT, UPDATE, DELETE retained; inspected code uses SELECT/INSERT/UPDATE |

Retaining service_role CRUD is a conservative compatibility proposal, not a finding that every CRUD privilege is necessary on every table. A later least-privilege pass can remove unused DELETE on students/notifications and UPDATE on items after checking external backend consumers. Remove service-role utility/DDL-related privileges now from these five resources; no inspected endpoint requires TRUNCATE, REFERENCES, TRIGGER, or MAINTAIN.

Existing identity keys, foreign keys, trigger definitions, publication semantics and API payloads should remain unchanged in this authorization patch. Preserve student registration compensation, conditional approval, archival behavior, result-item deletion, faculty reconciliation, and read-marking. Do not add enrollment architecture to this remediation.

### Proposed SQL — review text only, never executed

Apply the approved statements atomically in a new follow-up migration. Do not modify the historical migrations. At implementation time abort if unreviewed policies, column grants, memberships, or extra grantees are found.

~~~sql
-- PROPOSAL ONLY: direct clients must not access these backend-owned tables.
REVOKE ALL PRIVILEGES ON TABLE
    public.students,
    public.student_attendance,
    public.student_results,
    public.student_result_items,
    public.student_notifications
FROM PUBLIC, anon, authenticated;

ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_result_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_notifications ENABLE ROW LEVEL SECURITY;

REVOKE TRUNCATE, REFERENCES, TRIGGER, MAINTAIN ON TABLE
    public.students,
    public.student_attendance,
    public.student_results,
    public.student_result_items,
    public.student_notifications
FROM service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.students,
    public.student_attendance,
    public.student_results,
    public.student_result_items,
    public.student_notifications
TO service_role;
~~~

**Policy decision:** create no client allow policies on these five tables. With client grants removed and RLS enabled, the intended direct-client boundary is closed. No service_role allow policy is required because the installed role has BYPASSRLS. PostgreSQL documents default denial without policies and the bypass behavior; it also excludes TRUNCATE and REFERENCES from row security. Therefore RLS alone would leave material privileges unaddressed. [PostgreSQL 17 row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)

FORCE ROW LEVEL SECURITY is not required for this boundary and does not constrain a BYPASSRLS role. It should not be presented as protection against privileged backend mistakes. Do not add a permissive policy with USING(true) or WITH CHECK(true) to make endpoint tests pass.

No column ACLs currently exist on the five tables. Table revocation must be supplemented with column-level revocation if later inspection finds independent column grants. Similarly, inherited grants require repair at their granting parent role: direct-role REVOKE is not sufficient when a parent still confers access.

A future direct-browser feature would need separate approval and fully specified policies: identity through students.user_id → users.id → users.auth_user_id, validated institution/eligibility, own published result checks, and parent-result authorization for items. auth.uid() is an auth key, not students.user_id. A notification row-ownership policy alone would permit arbitrary owned-row field changes if UPDATE were granted broadly; approved direct read-marking would need constrained columns or a narrow authorized RPC. No such direct-access policy is proposed here.

## 4. Function findings, overloads, and reviewed proposal

Every listed target overload is owned by postgres, is SECURITY DEFINER, and has an empty search_path. postgres has BYPASSRLS. The installed definitions qualify application relations with public and retain their transactional business rules. An empty search_path limits name-resolution risk; it does not authorize the caller.

Appendix B records exact argument names, defaults, results and ACLs. Only complete_email_outbox has default arguments: the last three parameters default to NULL. These are alternative call arities of one seven-argument identity, not three additional functions.

| ID | Exact public signature | Definition / revoke / backend call | Verified body behavior and inferred misuse |
| --- | --- | --- | --- |
| F1a | phase717_claim_email_outbox(integer,integer,integer) | M5:260 / M5:441; S11:19; S12:182 | Claims and recovers jobs, writes attempts/invitation projection, returns SETOF email_outbox. No caller-role/actor authorization. Risk: unauthorized queue interference and return of protected-token ciphertext/metadata. Ciphertext is not evidence of plaintext recovery. |
| F1b | phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamp with time zone) | M5:344 / M5:443; S11:46; S12:62 | Validates outcome and current attempt, then settles outbox/attempt/invitation state. No caller authorization. Risk: forged settlements when valid job/attempt inputs are known. |
| F1c | phase717_create_invitation_with_outbox(uuid,text,text,timestamp with time zone,uuid,text) | M5:139 / M5:437; S10:249; S16:403 | Expires elapsed duplicates and inserts fixed-admin invitation plus outbox. Inputs include institution/creator; no caller authorization. Risk: bypass of the platform invitation API and its actor checks. |
| F2a | phase717_create_invitation_with_outbox(uuid,text,text,timestamp with time zone,uuid,text,text) | M7:20 / M7:64 | Role argument limited to admin/staff/faculty; client EXECUTE already false. Keep the boundary explicit and preserve seven-argument onboarding compatibility. Does not replace or revoke the six-argument overload. |
| F1d | phase717_resolve_email_outbox_context(uuid,text) | Original M5:410 / M5:445; installed replacement M7:71; S11:34 | Stable read function returns recipient/institution/role context only for a processing, current, unexpired invitation with matching token hash. No caller-role authorization. Risk is conditional information access, not unconditional dumping or a mutation. |
| F1e | phase717_rotate_invitation_with_outbox(uuid,text,timestamp with time zone,timestamp with time zone,text,integer) | M5:180 / M5:439; S10:289; S16:535 | Locks invitation, checks lifecycle/version and worker lease, supersedes pending jobs, rotates digest and queues new job. No caller authorization. Risk: unauthorized resend/token-state manipulation. |
| F1f | phase718_reconcile_mailgun_event(text,text,text,text,text,timestamp with time zone) | M6:55 / M6:193; S11:76; S14:38 | Validates event shape and deduplicates events; mutates delivery state and current-generation invitation projection. It does not verify Mailgun HMAC. Risk: direct RPC bypass of the verified HTTP webhook boundary. |

All six exposed signatures have the exact ACL:

~~~text
{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}
~~~

The seven-argument creation overload has:

~~~text
{postgres=X/postgres,service_role=X/postgres}
~~~

M5:437–456 and M6:193–196 revoke from PUBLIC only, then grant service_role. They do not revoke independent anon/authenticated entries. M7:64 explicitly revokes those roles on the seven-argument creation overload, but M7:71 replaces the two-argument resolver without an accompanying ACL repair. CREATE OR REPLACE preserves existing permissions, so changing the body is not an ACL fix. [PostgreSQL 17 CREATE FUNCTION](https://www.postgresql.org/docs/17/sql-createfunction.html)

### Intended function boundary

- Creation/rotation: service-role backend after the platform super-admin route or the appropriate approved institution-onboarding workflow has validated actor, tenant and requested resource.
- Claim/complete/resolve: trusted service-role worker, which intentionally processes jobs across institutions. Do not require a human student/admin JWT for scheduled worker execution.
- Mailgun reconciliation: service-role backend only after FastAPI verifies signature, time tolerance, configured domain and normalized event identity.
- Each corresponding anon/authenticated RPC call: denied, including callers who have a legitimate application admin/faculty role.
- Function owner: retains owner authority for execution and maintenance.

The service-role grant authorizes backend execution, not the human actor. Keep FastAPI scope checks. Do not change these to SECURITY INVOKER merely to address an ACL defect: that would alter the privilege contract and requires separate dependency review. Do not add current_user='service_role' inside a definer body as an assumed caller check; the effective current_user there is the function owner.

### Proposed SQL — all seven target identities

~~~sql
-- PROPOSAL ONLY: retain signatures and behavior, close every client entry.
REVOKE ALL PRIVILEGES ON FUNCTION
    public.phase717_claim_email_outbox(integer, integer, integer),
    public.phase717_complete_email_outbox(
        uuid, integer, text, text, text, text, timestamp with time zone),
    public.phase717_create_invitation_with_outbox(
        uuid, text, text, timestamp with time zone, uuid, text),
    public.phase717_create_invitation_with_outbox(
        uuid, text, text, timestamp with time zone, uuid, text, text),
    public.phase717_resolve_email_outbox_context(uuid, text),
    public.phase717_rotate_invitation_with_outbox(
        uuid, text, timestamp with time zone, timestamp with time zone, text, integer),
    public.phase718_reconcile_mailgun_event(
        text, text, text, text, text, timestamp with time zone)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION
    public.phase717_claim_email_outbox(integer, integer, integer),
    public.phase717_complete_email_outbox(
        uuid, integer, text, text, text, text, timestamp with time zone),
    public.phase717_create_invitation_with_outbox(
        uuid, text, text, timestamp with time zone, uuid, text),
    public.phase717_create_invitation_with_outbox(
        uuid, text, text, timestamp with time zone, uuid, text, text),
    public.phase717_resolve_email_outbox_context(uuid, text),
    public.phase717_rotate_invitation_with_outbox(
        uuid, text, timestamp with time zone, timestamp with time zone, text, integer),
    public.phase718_reconcile_mailgun_event(
        text, text, text, text, text, timestamp with time zone)
TO service_role;

-- Related hygiene; this is an invoker trigger helper, not an eighth target RPC.
REVOKE EXECUTE ON FUNCTION public.phase717_cancel_terminal_invitation_email()
FROM PUBLIC, anon, authenticated;
~~~

Keep the terminal-invitation cancellation trigger installed and validate it through its legitimate parent-table update. Its client EXECUTE entry is not equivalent to a callable ordinary RPC: it returns trigger and requires trigger context.

The related phase723_approve_membership_with_invitation(uuid,uuid,uuid,text,text,timestamp with time zone,text) is already owner/service_role-only, returns jsonb, and has no defaults. Preserve that ACL and its nested creation behavior. Current admin_memberships.py:92 instead calls phase723_approve_membership_and_grant_role; do not rewrite current onboarding to the older helper as part of this patch. This audit found exactly seven target overloads under the six reported names; re-enumerate names at implementation and deployment to catch additional remote or later overloads.

## 5. Default privileges and effective/inherited access

The catalog shows six public-scoped default ACLs: tables, sequences and functions for each of postgres and supabase_admin. Table ACLs grant all inventoried privileges to anon/authenticated/service_role; sequence ACLs grant SELECT/UPDATE/USAGE; function ACLs grant EXECUTE. No global pg_default_acl rows were present in this snapshot. The builtin function default obtained with acldefault is {=X/postgres,postgres=X/postgres}; absence of a global row does not mean default PUBLIC EXECUTE is absent.

M0:1173 and M0:1174 explicitly add client function defaults. M0:1182–1183 only state postgres/service_role table defaults; the additional installed client table/sequence defaults and supabase_admin defaults are catalog facts, not proven to originate in that file. Platform/bootstrap defaults may contribute; applied historical bytes were not reconstructed.

Default ACLs apply to future objects created by the actual creating role, not its inherited roles; schema-scoped defaults add to global defaults. A schema-only revoke cannot subtract builtin/global PUBLIC function EXECUTE. Existing objects require separate revocations. [PostgreSQL 17 ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html)

### Proposed SQL — future-object client defaults

**Executor requirement:** default privileges belong to their creator role. The inspected postgres role is not a superuser and is not a member of supabase_admin. Do not place the combined two-creator block into an ordinary postgres migration and assume it can run: use each authorized creator or a separately approved sufficiently privileged maintenance executor, and split the operations if necessary. The object ACL fix can run with object-owner authority. If supabase_admin defaults cannot be changed in a managed environment, keep that part open and require explicit same-transaction ACLs for its future objects; do not improvise platform-role membership changes.

~~~sql
-- PROPOSAL ONLY. Cover both observed object creators.
-- Global: remove builtin PUBLIC function EXECUTE and any global client grants.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

-- Public schema: remove independently added direct client function grants.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

-- Remove global and schema additions independently for tables and sequences.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin
    REVOKE ALL PRIVILEGES ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL PRIVILEGES ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin
    REVOKE ALL PRIVILEGES ON SEQUENCES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL PRIVILEGES ON SEQUENCES FROM PUBLIC, anon, authenticated;
~~~

This leaves existing service-role defaults intact for compatibility; future migrations must still explicitly narrow backend privileges and enable RLS where appropriate. A subsequent creator-default tightening can require object-specific service-role grants, but should be reviewed against every future backend object first. Never replace these scoped grants with GRANT ALL ON ALL TABLES/FUNCTIONS to clients.

Global default changes affect future objects in other schemas created by those two roles; they do not alter existing objects. Review extensions/internal-schema provisioning and all later migration consumers before adopting this part. If global default changes cannot be approved, object-level revocations in the same creation transaction plus catalog assertions can contain the immediate findings, but the recurring-default issue must remain explicitly open. No new client EXECUTE grant is needed for the six backend workflows.

anon and authenticated currently have INHERIT=true, no BYPASSRLS, no superuser status and no login. Full pg_auth_members inspection plus pg_has_role(MEMBER/USAGE/SET) found no reachable parent role for either client other than itself. The effective exposures are therefore direct grants, not inherited service-role access.

authenticator has NOINHERIT and membership entries permitting SET ROLE to anon/authenticated/service_role. That is the local API authentication machinery, not evidence that an ordinary client may assume service_role. Preserve those memberships; do not remove them as a substitute for object ACL repair.

At implementation/deployment inspect raw ACLs, PUBLIC entries, column ACLs, every inherited or settable parent role, grant options, owner/BYPASSRLS flags and effective has_*_privilege results. New extra grantees require explicit review. Do not use CASCADE revocation or blanket membership changes without identifying their downstream effects.

## 6. FastAPI, tenant isolation, and related security dependency

### Verified safeguards and compatibility

| Path / exact line | Verified behavior | Remediation compatibility requirement |
| --- | --- | --- |
| S1:8, S1:20, S1:32 | Separate publishable auth client and cached secret-backed service client | Preserve auth sign-in/signup flows; keep secret-backed database operations server-side |
| S1:52, S2:48, S2:99 | JWT verification precedes server account/role lookup using service client | RLS/client ACL repair must leave service SELECT and embedded students lookup available |
| S2:343, S3:175, S3:196, S3:213 | Institution authority resolved from active grants; missing/ambiguous/inactive scope fails closed | Preserve route dependency and lifecycle checks; client tenant UUID never becomes authority |
| S6:162, S6:185, S6:191, S6:199 | Router permission map plus institution admin dependency; scoped admin/staff approval exception | Preserve permission and role checks before any privileged operation |
| S6:843, S6:970, S6:1014, S6:1198 | Target/body/student scope checks precede academic writes | Cross-tenant requests must fail before repository mutation |
| S5:22, S5:47, S5:85; S20:77, S20:121 | Own identity resolved from public user; published-only result filtering; foreign/unpublished detail yields safe errors | Preserve own/student/publication semantics and nested result items |
| S4:52, S4:108 | Shared context requires approved and is_active student plus active institution | Preserve where currently used; do not silently impose it on legacy /me routes that use S5 directly |
| S9:126, S9:151; backend/app/api/student_notifications.py:55 | Notifications derive student server-side and check ownership before detail/read-marking | Preserve own-notification access and prevent writable content/tenant/identity through read-marking |
| S18:278, S18:314, S18:543; S19:28 | Faculty section checks, tenant-local identity candidates and server actor/tenant RPC inputs | Preserve assigned-section operations and reconciliation triggers |
| S15:289, S15:350; S2:373; S16:384, S16:498 | Platform invitation create/resend requires super_admin; service validates institution/lifecycle and invitation binding | Preserve six-argument creation, rotation and denial of cross-institution invitation IDs |
| S17:65, S17:86 | Public invitation token-holder inspect/accept routes call backend services | Public HTTP flow does not require anon database privileges; preserve token/expiry/replay safeguards |
| S12:182, S12:88, S11:19, S11:46 | Worker uses service client, decrypts protected payload in server memory, resolves current token and settles via RPC | Keep service EXECUTE, lease recovery, atomicity, retries and safe logging |
| S14:30, S14:38; S13:59, S13:119 | HMAC/timestamp/domain validation occurs before reconciliation | Webhook remains public HTTP but trusted reconciliation remains backend-only |

Frontend services use FastAPI fetch: frontend/src/services/studentApi.ts:56, :112 and frontend/src/services/adminApi.ts:48, :120. No Supabase import or Realtime client usage was found in frontend/src. Catalog inspection found zero public views/materialized views and no publication entry for these five tables. These observations reduce known compatibility concerns; they do not prove that uninspected external clients, other schemas, or future functions cannot expose the data.

Source comments claiming that a tenant trigger rejects cross-student callers should not be treated as security proof. The installed attendance/results/notification guards inspect NEW relationships and current student membership; they do not inspect authenticated caller ownership. students has reconciliation and visibility triggers, not a caller authorization trigger; student_result_items has no non-internal trigger. Keep those relationship checks, but use grants/RLS and application authority for access control.

The service client bypasses RLS and has cross-tenant database authority. A privileged FastAPI bug remains capable of accessing another tenant. Do not replace server-owned role/tenant checks with “RLS will handle it,” and do not forward a user-controlled Authorization header into the cached administrative client.

### Related authorization-source defect

The following installed tables each have RLS=false, policies=0, and the same direct all-privilege client ACL as the five academic tables: users, user_roles, roles, role_permissions, permissions, institutions. S1:52–71 reads users and embeds user_roles/roles/role_permissions/permissions; S3:213–220 trusts institution lifecycle. Thus writable authority tables undermine the premise that those values are server-owned.

M0 defines these identity/role tables at :346, :429, :439, :492 and :502 and grants service-role access at :1120, :1140, :1144, :1156 and :1160. Those service grants do not revoke client defaults. M8:764 and M9:23 define role-scope triggers. The installed guards validate institution→organization membership and super_admin platform-scope shape, respectively; neither establishes that the caller is permitted to assign a role.

**Proposed accompanying boundary:** revoke PUBLIC/anon/authenticated table and any independent column write privileges on these authorization sources, and review their client reads. The inspected frontend/server architecture supports backend-only access: recommend the same all-client revocation plus enabled RLS/no client allow policies, preserving service CRUD and controlled role-management functions. Approve that accompanying scope and its registration/platform/RBAC regressions before a complete security-remediation release. No blanket revocation on unrelated public content tables is proposed.

Actual role escalation was not attempted. This is a verified ability to write authority resources plus an inferred authorization-bypass path; it is not a demonstrated exploit. user_permission_grants is already RLS-enabled and owner/service_role-only. platform_admin_invitations has restricted client grants despite RLS=false; consider enabling its RLS as accompanying defense after lifecycle validation. email_outbox, email_delivery_attempts, and email_delivery_events already have RLS=true and no client grants/policies; preserve that state. Their table restrictions do not neutralize a client-executable definer RPC.

## 7. Migrations and tests to preserve or extend

Use a **new forward migration** after the highest existing version (20261016010000); the repository already contains applied filenames later than the user-facing audit date. Do not choose a timestamp that silently orders the fix before later migrations. Preserve all 39 historical files and their current hashes; re-enumerate/recheck chronology at implementation.

M0 supplies function defaults; M1/M4 create academic objects without removing client privileges assigned at creation; M5/M6 contain incomplete function revocations; M7 adds the restricted overload and replaces the resolver. M10:200 grants CRUD on every public table to service_role, so replay ordering also matters to service-role minimization. Preserve M8/M9 scope guards, M11 attendance reconciliation, M12 test visibility/workflow guards, and existing invitation transition/cancellation behavior.

No existing test was run in this task. The inspected suites contain mocked service/repository tests and SQL-text assertions; those are source expectations, not evidence that real client roles are denied by the installed database.

| Existing file and exact line | Contract to retain / coverage to add |
| --- | --- |
| backend/tests/test_auth.py:273, :311, :331 | Server role/tenant projection, spoofed client authority ignored, unauthenticated denial; add protected-authority-source assertions |
| backend/tests/test_students_api.py:113, :161; test_student_data_service.py:27, :49, :111 | Own/published results and own attendance; run against restricted service client as well as mocks |
| backend/tests/test_student_registration_phase_6_3.py:207, :460, :496 | Pending registration and compensation after account/student insertion failures |
| backend/tests/test_student_model_phase_6_2.py:273; test_student_approval_phase_6_4.py:322, :463 | Institution identity constraints, conditional approval/stale decision conflicts |
| backend/tests/test_attendance_phase_6_7.py:232, :334, :634, :696, :722 | Derived tenant, foreign section/student denial, authentication and authorized admin operations |
| backend/tests/test_results_phase_6_8.py:821, :883, :1111, :1138, :1291, :1310, :1346 | Academic/tenant guards, authorized admin management, own published detail/items, foreign/draft denial |
| backend/tests/test_student_notifications_phase_6_11.py:277, :333, :373, :723, :767 | Unauthorized denial, own notification list/read-marking and tenant relationships |
| backend/tests/test_phase_7_20_university_admin_tenant_isolation.py:177, :191, :285 | Forged tenant/body/resource IDs rejected before mutation |
| backend/tests/test_phase_7_12_super_admin_authorization.py:71, :102, :126 | Tenant-role denial, forged authority ignored, immediate revocation |
| backend/tests/test_phase_7_15_invitation_delivery_email_verification.py:755, :1274, :1284 | Cross-tenant resend/acceptance denial and credential-safe responses |
| backend/tests/test_phase_7_16_production_email_delivery.py:112, :122, :212 | Timeouts/idempotency/retry bounds and safe logging |
| backend/tests/test_phase_7_17_email_outbox_worker.py:77, :90, :129, :137, :145, :154, :163 | Worker success/failure/lease/cancellation contracts; replace reliance on generic SQL substrings with per-signature catalog denial checks |
| backend/tests/test_phase_7_18_mailgun_delivery_webhooks.py:181, :195, :264, :277, :302, :342 | Signature/time/replay/current-generation behavior and safe logging; add direct-RPC denial and valid backend RPC checks |
| backend/tests/test_phase_7_23_staff_faculty_onboarding_roster.py:100, :281, :324, :334 | Scoped role onboarding, deactivation, atomic approval/role granting and role vocabulary |
| backend/tests/test_faculty_attendance_workflow.py:68, :125, :242, :253; test_faculty_tests.py:174, :193 | Foreign identity exclusion, pending roster support, trusted actor/tenant and own published results |
| frontend/src/services/studentApi.test.ts:31, :54; features/auth/AuthProvider.test.tsx:95, :109 | Existing API/session contracts; no browser database grants should be required |
| frontend/src/features/faculty/FacultyAttendance.test.tsx:83 | Preserve current user edits and the existing attendance UI contract |

The current worker boundary test at test_phase_7_17_email_outbox_worker.py:163 checks for RLS and a generic FROM PUBLIC, anon, authenticated substring occurring in table revocations. It does not prove that every function overload has client EXECUTE revoked. The webhook migration test at :302 checks replay/business-rule text, not effective role ACLs. Add catalog-level assertions to close this coverage gap; do not merely add another substring assertion.

## 8. Proposed regression matrix — not executed

All write-based cases below require a separately authorized **disposable local database**. Use synthetic fixtures, two institutions, at least two same-tenant students plus a foreign-tenant student, approved/pending/inactive identities, published/draft results and parent items, owned/foreign notifications, and invitation/outbox generations. Use fake email transports and synthetic signing material; no real messages or production keys. Roll back transaction-scoped cases and verify that setup/teardown cannot target remote state. No such fixtures or tests were created here.

### Database authorization

| Test group | Required assertions |
| --- | --- |
| ACL/RLS inventory | Each scoped table RLS=true; no client policies; all eight has_table_privilege checks false for anon/authenticated; PUBLIC entries absent; independent column access denied; service CRUD true and utility privileges false |
| Own and foreign direct reads | Both client roles denied on each of five tables, including a caller's own student/attendance/result/items/notifications; filtering by guessed student or tenant does not bypass denial |
| Direct client writes | INSERT/UPDATE/DELETE/upsert denied on each table; verify row counts/state unchanged; wrong identity/tenant and existing valid own-row inputs both denied |
| Whole-table operations | TRUNCATE denied on nonempty disposable fixtures; REFERENCES/TRIGGER/MAINTAIN false in catalog; do not treat RLS as protecting whole-table privileges |
| HTTP Data API | Test anonymous and valid ordinary authenticated contexts, reads, embedded result→items reads, writes and exact counts; assert permission denial/no sensitive payload, accounting for gateway/PostgREST error mapping |
| Effective inheritance | Re-enumerate parent roles; no client can inherit or SET a role that grants target access; owner/superuser/BYPASSRLS is never used as the negative-test identity |
| Definer boundary | Each seven target overloads: PUBLIC absent, anon/authenticated EXECUTE=false, service_role=true; direct function and /rpc entry denied even for ordinary sessions representing application admins |
| Defaults | Under every approved creator role, create disposable public table/sequence/function, inspect client/PUBLIC ACLs; exercise global-versus-schema defaults and explicitly needed backend grants; roll back objects |
| Authorization sources | If accompanying scope approved, deny client writes to users/user_roles/roles/role_permissions/permissions/institutions and verify no forged grant can influence /auth/me or protected endpoints |
| Migration sequencing | Rehearse forward migration on current-schema and full-replay disposable local databases; assert all overloads, defaults, trigger bindings and intended effective privileges survive the final migration |

Negative mutations must be tested with otherwise valid data so a foreign-key/check failure cannot masquerade as authorization success. For RPCs, likewise ensure permission denial occurs before body validation, not merely an empty response because tables are empty. Record role-specific SQLSTATE/HTTP behavior and absence of side effects; do not pin all PostgREST versions to a guessed HTTP status.

### Every target function and legitimate caller

| Signature / call variants | Negative regression | Authorized backend regression |
| --- | --- | --- |
| claim(integer,integer,integer) | anon/authenticated cannot claim, recover leases or receive job rows | service worker claims only eligible jobs; bounded batch; concurrent SKIP LOCKED prevents double claims; attempts recorded; stale retry/dead-letter behavior retained |
| complete(uuid,integer,text,text,text,text,timestamptz) | Both clients denied for full seven arguments and valid four-, five-, six-argument defaulted SQL calls; named omitted-default /rpc forms denied | Current attempt succeeds; stale attempt returns false; sent/retry/dead-letter/cancelled behavior and protected-payload clearing preserved |
| create(uuid,text,text,timestamptz,uuid,text) | Both clients denied even with valid tenant/creator inputs | Existing S10 six-key payload selects this overload; invitation and outbox commit atomically; expired duplicate handling and live-duplicate conflict retained |
| create(uuid,text,text,timestamptz,uuid,text,text) | Both clients denied; verify this independently of the six-argument overload | service-role call allows admin/staff/faculty, rejects invalid role, remains compatible with authorized onboarding/older helper dependencies |
| resolve(uuid,text) | Both clients denied even with a matching synthetic token hash | Current processing/unexpired/matching digest returns permitted context/role; wrong digest, terminal/expired or superseded context returns null |
| rotate(uuid,text,timestamptz,timestamptz,text,integer) | Both clients denied; tenant administrator cannot resend another institution's invitation through FastAPI | Authorized platform resend retains pending/lifecycle/version checks; refuses nonstale worker lease; old digest invalidated; one new durable job |
| reconcile(text,text,text,text,text,timestamptz) | Direct client RPC denied with well-formed events; invalid HTTP signature/domain/time never reaches repository RPC | Valid signed local webhook reconciles via service_role; duplicate/replay/unknown/unsupported handled; old send generation cannot overwrite new invitation projection |
| Related cancellation trigger / onboarding helper | Trigger function is not counted as a callable ordinary RPC; existing restricted helper ACL stays restricted | Cancel/accept/expire parent updates still cancel queued messages; approved onboarding path still creates/assigns its authorized role |

The target overload count is seven, not six: six names, with two create identities. complete's defaulted arities still refer to its full seven-argument signature. Test PostgreSQL typed calls and actual PostgREST named-parameter dispatch rather than assuming how overloads are resolved.

### FastAPI and compatibility

- Unauthenticated requests and unauthorized application roles fail before privileged repository work.
- Admin A cannot read/write student, attendance, result or items owned by institution B; forged query/body/path tenants do not change authority.
- Student A cannot read Student B's records, same-tenant or foreign-tenant; own result summaries/details exclude unpublished rows and preserve the safe foreign/missing error contract.
- Registration can still insert a pending profile, compensate partial failures, and sign in through the public auth API without database client grants.
- Conditional approval/rejection and archival still work; reconciliation/visibility trigger chains continue after RLS/client revocations.
- Faculty operations require assigned section and trusted tenant/actor; linked/unregistered/pending rosters still behave as expected.
- Own notification list/detail/unread/read-marking work; forged identity/tenant/content fields cannot be supplied through the read-marking flow.
- Auth account→public user→students embedding still resolves using service_role; active role/lifecycle revocation immediately changes authorization.
- Platform creation and resend, token-holder inspect/accept, and the worker/webhook service path operate with the restricted RPC ACLs; credentials/ciphertext/token material are absent from unauthorized outputs and logs.
- Result creation rollback/compensation and explicit item deletion remain available under service CRUD; reducing item DELETE or parent SELECT would break inspected code.

## 9. Local implementation verification checklist — future approval required

- [ ] Obtain explicit approval for a concrete local implementation scope, including whether the authorization-source dependency is included; retain this report and the preflight report.
- [ ] Verify the same local Docker endpoint/container/database; independently reject remote URLs/targets before any write-capable harness starts.
- [ ] Recheck working-tree edits, migration ledger, all target overloads, owners/defaults/memberships, existing policies and column grants; preserve user changes.
- [ ] Prepare one additive, forward migration ordered after the current latest version; historical migration files remain byte-for-byte unchanged.
- [ ] Review exact object/signature revocations, RLS/no-client-policy decision, service-role grants, default creators/global effects, and accompanying authority-table protections.
- [ ] Apply only to the approved local/disposable target in an atomic transaction; abort on unexpected ACLs/policies/overloads instead of silently dropping unrelated security objects.
- [ ] Capture before/after metadata safely; expected academic state: five enabled RLS tables, zero client policies, zero client effective privileges, service CRUD only.
- [ ] Expected target routine state: seven identities, client EXECUTE=false for all, service_role=true, unchanged signatures/defaults/search_path/definitions except approved changes.
- [ ] Run the approved database/HTTP/FastAPI/function matrices on populated disposable fixtures with fake transports; negative tests use actual client roles.
- [ ] Retain and run the relevant existing tests; inspect failures for actual permission/dispatch regression rather than weakening guards.
- [ ] Validate registration, auth embedding, approved admin/faculty paths, result items, notification read-marking, cancellation triggers, worker leases and signed webhook reconciliation.
- [ ] Recheck future-object defaults for each creator and the final migration order; confirm no later grant or overload reopens client access.
- [ ] Recheck counts/history/identity keys preserved; no enrollment changes or unintended academic mapping changes.
- [ ] Refresh documentation/schema metadata from the verified local catalog; report exact tests and any limits.
- [ ] Design rollback to restore legitimate backend operation while keeping clients denied; do not automatically revert to the exposed grants.

## 10. Future remote deployment checklist — separate authorization and investigation

Nothing in this task inspected, connected to, or changed remote Supabase.

- [ ] Obtain explicit approval for the specific remote project/environment and approved migration artifact after local evidence is reviewable.
- [ ] Use secure project identification; never print connection strings, tokens, keys, environment dumps, or provider credentials.
- [ ] Perform a separately authorized remote read-only preflight: actual schema/API exposure, PostgreSQL version, ledger, owners/creator roles, all overloads/defaults, raw/effective/column ACLs, memberships, BYPASSRLS, policies, views and relevant publications.
- [ ] Treat remote counts and permissions as unknown until checked; account for populated data and external direct-Supabase consumers.
- [ ] Confirm matching reviewed signatures and migration ordering; adapt reviewed statements if remote creators or overloads differ; stop on unexplained drift.
- [ ] Resolve authorization-source exposure before claiming complete tenant/security repair; review dependencies and legitimate anonymous public-content flows.
- [ ] Review global default changes against managed-platform provisioning and other schemas; permission to change postgres defaults does not prove permission to change every other creator's defaults.
- [ ] Establish secure rollback/recovery and deployment coordination for API workers/webhooks; no return to unsafe client grants as an automatic rollback.
- [ ] Rehearse on separately approved staging with synthetic/sanitized fixtures and fake email provider; complete authorized negative/write tests there.
- [ ] Deploy only the reviewed artifact after approval. Database migration approval does not imply permission to run a production seed/reset or unauthorized mutation/exploit probes.
- [ ] Verify production metadata and safe read-only behavior after deployment; use approved normal/synthetic canary operations only where separately authorized.
- [ ] Verify worker/RPC dispatch and signed-webhook health without exposing invitation material or sending unapproved real emails.
- [ ] Monitor authorization failures and legitimate backend errors; record deployment evidence and remaining scoped/unscoped risks without sensitive payloads.

## 11. Limits and stop point

No source file or migration was edited, created, deleted, formatted or executed. No mutating SQL, role impersonation/session mutation, reset, seed, package installation, application endpoint, pytest/Vitest/build, worker/provider invocation or write-based test was run. No remote Supabase connection or modification occurred. SQL shown in proposed sections is documentation only.

Zero rows do not prove that denial, populated trigger behavior, atomicity, concurrency, or backend compatibility has passed. Catalog ACLs establish the defects; behavioral regression remains required after explicit local implementation/test authorization. This report is not a complete audit of every public object or remote service.

**STOP:** Report delivered. Wait for explicit approval before implementation. The original M1 migration remains unapproved.

---

## Appendix A — Exact table catalog evidence

Source: pg_class, pg_policy, pg_attribute and has_table_privilege. All five tables are owned by postgres. Policy and independent-column-ACL counts are zero. For each of anon, authenticated and service_role the effective privileges are DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE. ACL code X is EXECUTE for routines; table codes arwdDxtm represent INSERT, SELECT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN. No grant options occur in these ACLs.

~~~json
{"audit":"tables","name":"student_attendance","oid":"19549","owner":"postgres","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"column_acls":0,"effective":{"authenticated":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"anon":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"service_role":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"]}}
{"audit":"tables","name":"student_notifications","oid":"19735","owner":"postgres","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"column_acls":0,"effective":{"authenticated":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"anon":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"service_role":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"]}}
{"audit":"tables","name":"student_result_items","oid":"19475","owner":"postgres","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"column_acls":0,"effective":{"authenticated":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"anon":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"service_role":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"]}}
{"audit":"tables","name":"student_results","oid":"19437","owner":"postgres","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"column_acls":0,"effective":{"authenticated":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"anon":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"service_role":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"]}}
{"audit":"tables","name":"students","oid":"19398","owner":"postgres","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"column_acls":0,"effective":{"authenticated":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"anon":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"],"service_role":["DELETE","INSERT","MAINTAIN","REFERENCES","SELECT","TRIGGER","TRUNCATE","UPDATE"]}}
~~~

## Appendix B — Every routine identity and installed definition

The first seven ordinary definer identities below are the complete inventory under the six scoped function names. The invoker cancellation trigger and restricted older onboarding helper are included separately for dependency review. These are catalog evidence; their CREATE/INSERT/UPDATE text was never executed by this audit.

~~~json
{"audit":"routine","oid":"20059","signature":"phase717_cancel_terminal_invitation_email()","owner":"postgres","kind":"f","definer":false,"volatility":"v","config":["search_path=\"\""],"arguments":"","default_args":0,"result":"trigger","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}","public_execute":false,"anon":true,"authenticated":true,"service_role":true}
{"audit":"routine","oid":"20064","signature":"phase717_claim_email_outbox(integer,integer,integer)","owner":"postgres","kind":"f","definer":true,"volatility":"v","config":["search_path=\"\""],"arguments":"p_batch_size integer, p_lock_seconds integer, p_retry_limit integer","default_args":0,"result":"SETOF email_outbox","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}","public_execute":false,"anon":true,"authenticated":true,"service_role":true}
{"audit":"routine","oid":"20065","signature":"phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamp with time zone)","owner":"postgres","kind":"f","definer":true,"volatility":"v","config":["search_path=\"\""],"arguments":"p_outbox_id uuid, p_attempt_number integer, p_outcome text, p_provider_name text, p_provider_message_id text DEFAULT NULL::text, p_failure_category text DEFAULT NULL::text, p_available_at timestamp with time zone DEFAULT NULL::timestamp with time zone","default_args":3,"result":"boolean","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}","public_execute":false,"anon":true,"authenticated":true,"service_role":true}
{"audit":"routine","oid":"20062","signature":"phase717_create_invitation_with_outbox(uuid,text,text,timestamp with time zone,uuid,text)","owner":"postgres","kind":"f","definer":true,"volatility":"v","config":["search_path=\"\""],"arguments":"p_institution_id uuid, p_email text, p_token_hash text, p_expires_at timestamp with time zone, p_created_by uuid, p_protected_token text","default_args":0,"result":"jsonb","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}","public_execute":false,"anon":true,"authenticated":true,"service_role":true}
{"audit":"routine","oid":"20107","signature":"phase717_create_invitation_with_outbox(uuid,text,text,timestamp with time zone,uuid,text,text)","owner":"postgres","kind":"f","definer":true,"volatility":"v","config":["search_path=\"\""],"arguments":"p_institution_id uuid, p_email text, p_token_hash text, p_expires_at timestamp with time zone, p_created_by uuid, p_protected_token text, p_role_name text","default_args":0,"result":"jsonb","acl":"{postgres=X/postgres,service_role=X/postgres}","public_execute":false,"anon":false,"authenticated":false,"service_role":true}
{"audit":"routine","oid":"20066","signature":"phase717_resolve_email_outbox_context(uuid,text)","owner":"postgres","kind":"f","definer":true,"volatility":"s","config":["search_path=\"\""],"arguments":"p_outbox_id uuid, p_token_hash text","default_args":0,"result":"jsonb","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}","public_execute":false,"anon":true,"authenticated":true,"service_role":true}
{"audit":"routine","oid":"20063","signature":"phase717_rotate_invitation_with_outbox(uuid,text,timestamp with time zone,timestamp with time zone,text,integer)","owner":"postgres","kind":"f","definer":true,"volatility":"v","config":["search_path=\"\""],"arguments":"p_invitation_id uuid, p_token_hash text, p_expires_at timestamp with time zone, p_expected_updated_at timestamp with time zone, p_protected_token text, p_lock_seconds integer","default_args":0,"result":"jsonb","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}","public_execute":false,"anon":true,"authenticated":true,"service_role":true}
{"audit":"routine","oid":"20104","signature":"phase718_reconcile_mailgun_event(text,text,text,text,text,timestamp with time zone)","owner":"postgres","kind":"f","definer":true,"volatility":"v","config":["search_path=\"\""],"arguments":"p_event_key text, p_replay_token_digest text, p_provider_event_id text, p_provider_message_id text, p_event_type text, p_event_timestamp timestamp with time zone","default_args":0,"result":"jsonb","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}","public_execute":false,"anon":true,"authenticated":true,"service_role":true}
{"audit":"routine","oid":"20108","signature":"phase723_approve_membership_with_invitation(uuid,uuid,uuid,text,text,timestamp with time zone,text)","owner":"postgres","kind":"f","definer":true,"volatility":"v","config":["search_path=\"\""],"arguments":"p_request_id uuid, p_institution_id uuid, p_decided_by uuid, p_reason text, p_token_hash text, p_expires_at timestamp with time zone, p_protected_token text","default_args":0,"result":"jsonb","acl":"{postgres=X/postgres,service_role=X/postgres}","public_execute":false,"anon":false,"authenticated":false,"service_role":true}
~~~

### public.phase717_claim_email_outbox(integer,integer,integer)

~~~sql
CREATE OR REPLACE FUNCTION public.phase717_claim_email_outbox(p_batch_size integer, p_lock_seconds integer, p_retry_limit integer)
 RETURNS SETOF email_outbox
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
BEGIN
    -- Jobs whose invitation is terminal or elapsed cannot produce a usable
    -- URL and must not remain pending forever.
    UPDATE "public"."email_outbox" AS o
    SET "status" = 'cancelled'::text, "protected_token" = NULL,
        "updated_at" = now(),
        "last_error_category" = 'INVITATION_NOT_DELIVERABLE'::text
    FROM "public"."platform_admin_invitations" AS i
    WHERE i."invitation_id" = o."aggregate_id"
      AND o."status" = 'pending'::text
      AND (i."status" <> 'invited'::text OR i."expires_at" <= now());

    UPDATE "public"."email_delivery_attempts" AS a
    SET "result" = CASE WHEN o."attempt_count" >= p_retry_limit
                        THEN 'dead_letter'::text ELSE 'retry'::text END,
        "completed_at" = now(), "failure_category" = 'WORKER_LEASE_EXPIRED'::text
    FROM "public"."email_outbox" AS o
    WHERE a."outbox_id" = o."id" AND a."attempt_number" = o."attempt_count"
      AND a."result" = 'processing'::text
      AND o."status" = 'processing'::text
      AND o."locked_at" <= now() - make_interval(secs => p_lock_seconds);

    UPDATE "public"."email_outbox"
    SET "status" = 'dead_letter'::text, "locked_at" = NULL,
        "protected_token" = NULL,
        "failed_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds)
      AND "attempt_count" >= p_retry_limit;

    UPDATE "public"."platform_admin_invitations" AS i
    SET "email_delivery_status" = 'failed'::text,
        "email_delivery_at" = now(), "updated_at" = now()
    FROM "public"."email_outbox" AS o
    WHERE o."aggregate_id" = i."invitation_id"
      AND o."status" = 'dead_letter'::text
      AND o."last_error_category" = 'WORKER_LEASE_EXPIRED'::text;

    UPDATE "public"."email_outbox"
    SET "status" = 'pending'::text, "locked_at" = NULL,
        "available_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds)
      AND "attempt_count" < p_retry_limit;

    RETURN QUERY
    WITH eligible AS (
        SELECT o."id"
        FROM "public"."email_outbox" AS o
        JOIN "public"."platform_admin_invitations" AS i
          ON i."invitation_id" = o."aggregate_id"
        WHERE o."status" = 'pending'::text
          AND o."available_at" <= now()
          AND o."attempt_count" < p_retry_limit
          AND i."status" = 'invited'::text
          AND i."expires_at" > now()
        ORDER BY o."available_at", o."created_at"
        FOR UPDATE OF o SKIP LOCKED
        LIMIT LEAST(GREATEST(p_batch_size, 1), 200)
    ), claimed AS (
        UPDATE "public"."email_outbox" AS o
        SET "status" = 'processing'::text, "locked_at" = now(),
            "attempt_count" = o."attempt_count" + 1, "updated_at" = now()
        FROM eligible AS e WHERE o."id" = e."id"
        RETURNING o.*
    ), attempts AS (
        INSERT INTO "public"."email_delivery_attempts"
            ("outbox_id", "attempt_number", "started_at", "result")
        SELECT c."id", c."attempt_count", now(), 'processing'::text FROM claimed AS c
        RETURNING "outbox_id"
    )
    SELECT c.* FROM claimed AS c JOIN attempts AS a ON a."outbox_id" = c."id";
END;
$function$

~~~

### public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamp with time zone)

~~~sql
CREATE OR REPLACE FUNCTION public.phase717_complete_email_outbox(p_outbox_id uuid, p_attempt_number integer, p_outcome text, p_provider_name text, p_provider_message_id text DEFAULT NULL::text, p_failure_category text DEFAULT NULL::text, p_available_at timestamp with time zone DEFAULT NULL::timestamp with time zone)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
    v_outbox "public"."email_outbox"%ROWTYPE;
    v_invitation_status text;
BEGIN
    IF p_outcome NOT IN ('sent'::text, 'retry'::text, 'dead_letter'::text, 'cancelled'::text) THEN
        RAISE EXCEPTION 'invalid email outbox outcome' USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO v_outbox FROM "public"."email_outbox"
    WHERE "id" = p_outbox_id FOR UPDATE;
    IF NOT FOUND OR v_outbox."status" <> 'processing'::text
       OR v_outbox."attempt_count" <> p_attempt_number THEN
        RETURN false;
    END IF;

    UPDATE "public"."email_delivery_attempts"
    SET "completed_at" = now(), "result" = p_outcome,
        "failure_category" = p_failure_category,
        "provider_message_id" = p_provider_message_id
    WHERE "outbox_id" = p_outbox_id AND "attempt_number" = p_attempt_number
      AND "result" = 'processing'::text;

    UPDATE "public"."email_outbox"
    SET "status" = CASE WHEN p_outcome = 'retry'::text THEN 'pending'::text
                        ELSE p_outcome END,
        "locked_at" = NULL,
        "available_at" = CASE WHEN p_outcome = 'retry'::text
                              THEN COALESCE(p_available_at, now())
                              ELSE "available_at" END,
        "sent_at" = CASE WHEN p_outcome = 'sent'::text THEN now() ELSE "sent_at" END,
        "failed_at" = CASE WHEN p_outcome = 'dead_letter'::text THEN now() ELSE "failed_at" END,
        "provider_name" = NULLIF(btrim(p_provider_name), ''),
        "provider_message_id" = p_provider_message_id,
        "last_error_category" = p_failure_category,
        "protected_token" = CASE WHEN p_outcome = 'retry'::text
                                 THEN "protected_token" ELSE NULL END,
        "delivery_updated_at" = now(), "updated_at" = now()
    WHERE "id" = p_outbox_id;

    v_invitation_status := CASE
        WHEN p_outcome = 'sent'::text THEN 'sent'::text
        WHEN p_outcome IN ('dead_letter'::text, 'cancelled'::text) THEN 'failed'::text
        ELSE 'pending'::text END;
    UPDATE "public"."platform_admin_invitations"
    SET "email_delivery_status" = v_invitation_status,
        "email_delivery_at" = now(),
        "email_delivery_attempts" = "email_delivery_attempts" + 1,
        "last_sent_at" = CASE WHEN p_outcome = 'sent'::text THEN now()
                              ELSE "last_sent_at" END,
        "updated_at" = now()
    WHERE "invitation_id" = v_outbox."aggregate_id";
    RETURN true;
END;
$function$

~~~

### public.phase717_create_invitation_with_outbox(uuid,text,text,timestamp with time zone,uuid,text)

~~~sql
CREATE OR REPLACE FUNCTION public.phase717_create_invitation_with_outbox(p_institution_id uuid, p_email text, p_token_hash text, p_expires_at timestamp with time zone, p_created_by uuid, p_protected_token text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    -- Preserve the prior service behaviour: an elapsed row is terminalized
    -- before issuing a replacement, while a still-live duplicate is rejected
    -- by the partial unique index even under concurrent requests.
    UPDATE "public"."platform_admin_invitations"
    SET "status" = 'expired'::text, "updated_at" = now()
    WHERE "institution_id" = p_institution_id
      AND lower("email") = lower(btrim(p_email))
      AND "status" = 'invited'::text
      AND "expires_at" <= now();

    INSERT INTO "public"."platform_admin_invitations" (
        "institution_id", "email", "token_hash", "role_name", "status",
        "expires_at", "created_by", "email_delivery_status"
    ) VALUES (
        p_institution_id, lower(btrim(p_email)), p_token_hash, 'admin'::text,
        'invited'::text, p_expires_at, p_created_by, 'pending'::text
    ) RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (v_invitation."invitation_id", p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$function$

~~~

### public.phase717_create_invitation_with_outbox(uuid,text,text,timestamp with time zone,uuid,text,text)

~~~sql
CREATE OR REPLACE FUNCTION public.phase717_create_invitation_with_outbox(p_institution_id uuid, p_email text, p_token_hash text, p_expires_at timestamp with time zone, p_created_by uuid, p_protected_token text, p_role_name text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    IF p_role_name NOT IN ('admin', 'staff', 'faculty') THEN
        RAISE EXCEPTION 'unsupported institution invitation role'
            USING ERRCODE = '22023';
    END IF;

    UPDATE "public"."platform_admin_invitations"
    SET "status" = 'expired'::text, "updated_at" = now()
    WHERE "institution_id" = p_institution_id
      AND lower("email") = lower(btrim(p_email))
      AND "status" = 'invited'::text
      AND "expires_at" <= now();

    INSERT INTO "public"."platform_admin_invitations" (
        "institution_id", "email", "token_hash", "role_name", "status",
        "expires_at", "created_by", "email_delivery_status"
    ) VALUES (
        p_institution_id, lower(btrim(p_email)), p_token_hash, p_role_name,
        'invited'::text, p_expires_at, p_created_by, 'pending'::text
    ) RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (v_invitation."invitation_id", p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$function$

~~~

### public.phase717_resolve_email_outbox_context(uuid,text)

~~~sql
CREATE OR REPLACE FUNCTION public.phase717_resolve_email_outbox_context(p_outbox_id uuid, p_token_hash text)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
    SELECT CASE
        WHEN o."status" = 'processing'::text
         AND i."status" = 'invited'::text
         AND i."expires_at" > now()
         AND i."token_hash" = p_token_hash
        THEN jsonb_build_object(
            'invitation_id', i."invitation_id",
            'recipient', i."email",
            'institution_name', n."name",
            'expires_at', i."expires_at",
            'role_name', i."role_name"
        )
        ELSE NULL
    END
    FROM "public"."email_outbox" AS o
    JOIN "public"."platform_admin_invitations" AS i
      ON i."invitation_id" = o."aggregate_id"
    JOIN "public"."institutions" AS n
      ON n."institution_id" = i."institution_id"
    WHERE o."id" = p_outbox_id;
$function$

~~~

### public.phase717_rotate_invitation_with_outbox(uuid,text,timestamp with time zone,timestamp with time zone,text,integer)

~~~sql
CREATE OR REPLACE FUNCTION public.phase717_rotate_invitation_with_outbox(p_invitation_id uuid, p_token_hash text, p_expires_at timestamp with time zone, p_expected_updated_at timestamp with time zone, p_protected_token text, p_lock_seconds integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    SELECT * INTO v_invitation
    FROM "public"."platform_admin_invitations"
    WHERE "invitation_id" = p_invitation_id
    FOR UPDATE;

    IF NOT FOUND OR v_invitation."status" <> 'invited'::text
       OR v_invitation."expires_at" <= now()
       OR (p_expected_updated_at IS NOT NULL
           AND v_invitation."updated_at" IS DISTINCT FROM p_expected_updated_at) THEN
        RETURN NULL;
    END IF;

    -- Recover an abandoned lease before deciding whether resend can proceed.
    UPDATE "public"."email_delivery_attempts" AS a
    SET "result" = 'retry'::text, "completed_at" = now(),
        "failure_category" = 'WORKER_LEASE_EXPIRED'::text
    FROM "public"."email_outbox" AS o
    WHERE a."outbox_id" = o."id"
      AND a."attempt_number" = o."attempt_count"
      AND a."result" = 'processing'::text
      AND o."aggregate_id" = p_invitation_id
      AND o."status" = 'processing'::text
      AND o."locked_at" <= now() - make_interval(secs => p_lock_seconds);

    UPDATE "public"."email_outbox"
    SET "status" = 'pending'::text, "locked_at" = NULL,
        "available_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds);

    -- A non-stale worker may already be inside provider I/O. Refuse the resend
    -- rather than rotate the token underneath that delivery.
    IF EXISTS (
        SELECT 1 FROM "public"."email_outbox"
        WHERE "aggregate_id" = p_invitation_id
          AND "status" = 'processing'::text
    ) THEN
        RETURN NULL;
    END IF;

    UPDATE "public"."email_outbox"
    SET "status" = 'cancelled'::text, "locked_at" = NULL,
        "protected_token" = NULL, "updated_at" = now(),
        "last_error_category" = 'INVITATION_SUPERSEDED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'pending'::text;

    UPDATE "public"."platform_admin_invitations"
    SET "token_hash" = p_token_hash, "expires_at" = p_expires_at,
        "resend_count" = "resend_count" + 1,
        "email_delivery_status" = 'pending'::text,
        "email_delivery_at" = NULL, "updated_at" = now()
    WHERE "invitation_id" = p_invitation_id
    RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (p_invitation_id, p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$function$

~~~

### public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamp with time zone)

~~~sql
CREATE OR REPLACE FUNCTION public.phase718_reconcile_mailgun_event(p_event_key text, p_replay_token_digest text, p_provider_event_id text, p_provider_message_id text, p_event_type text, p_event_timestamp timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
    v_event_id uuid;
    v_outbox "public"."email_outbox"%ROWTYPE;
    v_new_status text;
    v_result text;
    v_changed boolean := false;
    v_is_latest boolean := false;
BEGIN
    IF length(p_event_key) <> 64 OR length(p_replay_token_digest) <> 64
       OR NULLIF(btrim(p_provider_event_id), '') IS NULL
       OR p_event_timestamp IS NULL THEN
        RAISE EXCEPTION 'invalid verified email event' USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO "public"."email_delivery_events" (
        "provider_name", "event_key", "replay_token_digest",
        "provider_event_id", "provider_message_id", "event_type",
        "event_timestamp"
    ) VALUES (
        'mailgun'::text, p_event_key, p_replay_token_digest,
        p_provider_event_id, NULLIF(btrim(p_provider_message_id), ''),
        p_event_type, p_event_timestamp
    ) ON CONFLICT DO NOTHING
    RETURNING "id" INTO v_event_id;

    IF v_event_id IS NULL THEN
        RETURN jsonb_build_object(
            'result', 'duplicate', 'state_changed', false
        );
    END IF;

    IF p_event_type = 'unsupported'::text THEN
        UPDATE "public"."email_delivery_events"
        SET "processing_result" = 'unsupported'::text, "processed_at" = now()
        WHERE "id" = v_event_id;
        RETURN jsonb_build_object(
            'result', 'unsupported', 'state_changed', false
        );
    END IF;

    SELECT * INTO v_outbox
    FROM "public"."email_outbox"
    WHERE "provider_name" = 'mailgun'::text
      AND "provider_message_id" = NULLIF(btrim(p_provider_message_id), '')
    FOR UPDATE;

    IF NOT FOUND THEN
        UPDATE "public"."email_delivery_events"
        SET "processing_result" = 'unknown_message'::text, "processed_at" = now()
        WHERE "id" = v_event_id;
        RETURN jsonb_build_object(
            'result', 'unknown_message', 'state_changed', false
        );
    END IF;

    UPDATE "public"."email_delivery_events"
    SET "outbox_id" = v_outbox."id"
    WHERE "id" = v_event_id;

    SELECT NOT EXISTS (
        SELECT 1 FROM "public"."email_outbox" AS newer
        WHERE newer."aggregate_id" = v_outbox."aggregate_id"
          AND newer."delivery_sequence" > v_outbox."delivery_sequence"
    ) INTO v_is_latest;

    v_new_status := v_outbox."status";
    IF p_event_type = 'delivered'::text AND v_outbox."status" = 'sent'::text THEN
        v_new_status := 'delivered'::text;
    ELSIF p_event_type IN ('permanent_failure'::text, 'rejected'::text)
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        v_new_status := 'bounced'::text;
    ELSIF p_event_type = 'complained'::text
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        v_new_status := 'complained'::text;
    END IF;

    v_changed := v_new_status IS DISTINCT FROM v_outbox."status";
    IF v_changed THEN
        UPDATE "public"."email_outbox"
        SET "status" = v_new_status,
            "last_error_category" = CASE
                WHEN p_event_type = 'temporary_failure'::text
                    THEN 'MAILGUN_TEMPORARY_FAILURE'::text
                WHEN p_event_type IN ('permanent_failure'::text, 'rejected'::text)
                    THEN 'MAILGUN_PERMANENT_FAILURE'::text
                WHEN p_event_type = 'complained'::text
                    THEN 'MAILGUN_COMPLAINT'::text
                ELSE "last_error_category" END,
            "delivery_updated_at" = p_event_timestamp,
            "updated_at" = now()
        WHERE "id" = v_outbox."id";
    ELSIF p_event_type = 'temporary_failure'::text
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        UPDATE "public"."email_outbox"
        SET "last_error_category" = 'MAILGUN_TEMPORARY_FAILURE'::text,
            "delivery_updated_at" = p_event_timestamp, "updated_at" = now()
        WHERE "id" = v_outbox."id";
    END IF;

    -- An event for an older send is retained on that outbox row but cannot
    -- overwrite the invitation projection for a newer resend generation.
    IF v_is_latest AND v_changed THEN
        UPDATE "public"."platform_admin_invitations"
        SET "email_delivery_status" = CASE
                WHEN v_new_status = 'delivered'::text THEN 'delivered'::text
                ELSE 'failed'::text END,
            "email_delivery_at" = p_event_timestamp,
            "updated_at" = now()
        WHERE "invitation_id" = v_outbox."aggregate_id";
    END IF;

    v_result := CASE
        WHEN NOT v_is_latest THEN 'stale_generation'::text
        WHEN v_changed THEN 'applied'::text
        ELSE 'no_state_change'::text END;
    UPDATE "public"."email_delivery_events"
    SET "processing_result" = v_result, "state_changed" = v_changed,
        "processed_at" = now()
    WHERE "id" = v_event_id;

    RETURN jsonb_build_object(
        'result', v_result,
        'state_changed', v_changed,
        'outbox_id', v_outbox."id"
    );
END;
$function$

~~~

## Appendix C — Defaults, role flags, and effective membership

r = table; f = routine; S = sequence. No global default ACL row was found. These schema additions must be assessed together with builtin/global defaults. The authenticator membership direction is role → member; it does not make anon or authenticated members of authenticator.

~~~json
{"audit":"role","role":"anon","inherit":true,"superuser":false,"bypass_rls":false,"login":false}
{"audit":"role","role":"authenticated","inherit":true,"superuser":false,"bypass_rls":false,"login":false}
{"audit":"role","role":"authenticator","inherit":false,"superuser":false,"bypass_rls":false,"login":true}
{"audit":"role","role":"postgres","inherit":true,"superuser":false,"bypass_rls":true,"login":true}
{"audit":"role","role":"service_role","inherit":true,"superuser":false,"bypass_rls":true,"login":false}
{"audit":"role","role":"supabase_admin","inherit":true,"superuser":true,"bypass_rls":true,"login":true}
{"audit":"memberships","role":"anon","member":"authenticator","grantor":"supabase_admin","admin_option":false,"inherit_option":false,"set_option":true}
{"audit":"memberships","role":"authenticated","member":"authenticator","grantor":"supabase_admin","admin_option":false,"inherit_option":false,"set_option":true}
{"audit":"memberships","role":"service_role","member":"authenticator","grantor":"supabase_admin","admin_option":false,"inherit_option":false,"set_option":true}
{"audit":"client_reachable_roles","client":"anon","role":"anon","member":true,"inherited":true,"settable":true}
{"audit":"client_reachable_roles","client":"authenticated","role":"authenticated","member":true,"inherited":true,"settable":true}
{"audit":"defaults","creator":"supabase_admin","schema":"public","object_type":"S","acl":"{postgres=rwU/supabase_admin,anon=rwU/supabase_admin,authenticated=rwU/supabase_admin,service_role=rwU/supabase_admin}"}
{"audit":"defaults","creator":"supabase_admin","schema":"public","object_type":"f","acl":"{postgres=X/supabase_admin,anon=X/supabase_admin,authenticated=X/supabase_admin,service_role=X/supabase_admin}"}
{"audit":"defaults","creator":"supabase_admin","schema":"public","object_type":"r","acl":"{postgres=arwdDxtm/supabase_admin,anon=arwdDxtm/supabase_admin,authenticated=arwdDxtm/supabase_admin,service_role=arwdDxtm/supabase_admin}"}
{"audit":"defaults","creator":"postgres","schema":"public","object_type":"S","acl":"{postgres=rwU/postgres,anon=rwU/postgres,authenticated=rwU/postgres,service_role=rwU/postgres}"}
{"audit":"defaults","creator":"postgres","schema":"public","object_type":"f","acl":"{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}"}
{"audit":"defaults","creator":"postgres","schema":"public","object_type":"r","acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}"}
~~~

## Appendix D — Related resource and trigger evidence

No selected publication rows were returned. The public view/materialized-view count was zero. Metadata below verifies the authorization-source exposure, existing email table boundary and installed trigger bindings.

~~~json
{"audit":"related_table","name":"email_delivery_attempts","rls":true,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":false,"client_insert":false,"client_update":false,"client_delete":false,"authenticated_update":false}
{"audit":"related_table","name":"email_delivery_events","rls":true,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":false,"client_insert":false,"client_update":false,"client_delete":false,"authenticated_update":false}
{"audit":"related_table","name":"email_outbox","rls":true,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":false,"client_insert":false,"client_update":false,"client_delete":false,"authenticated_update":false}
{"audit":"related_table","name":"institutions","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":true,"client_insert":true,"client_update":true,"client_delete":true,"authenticated_update":true}
{"audit":"related_table","name":"permissions","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":true,"client_insert":true,"client_update":true,"client_delete":true,"authenticated_update":true}
{"audit":"related_table","name":"platform_admin_invitations","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":false,"client_insert":false,"client_update":false,"client_delete":false,"authenticated_update":false}
{"audit":"related_table","name":"role_permissions","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":true,"client_insert":true,"client_update":true,"client_delete":true,"authenticated_update":true}
{"audit":"related_table","name":"roles","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":true,"client_insert":true,"client_update":true,"client_delete":true,"authenticated_update":true}
{"audit":"related_table","name":"user_permission_grants","rls":true,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":false,"client_insert":false,"client_update":false,"client_delete":false,"authenticated_update":false}
{"audit":"related_table","name":"user_roles","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":true,"client_insert":true,"client_update":true,"client_delete":true,"authenticated_update":true}
{"audit":"related_table","name":"users","rls":false,"force_rls":false,"acl":"{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}","policies":0,"client_select":true,"client_insert":true,"client_update":true,"client_delete":true,"authenticated_update":true}
{"audit":"triggers","table":"platform_admin_invitations","name":"trg_phase715_invitation_transition","enabled":"O","definition":"CREATE TRIGGER trg_phase715_invitation_transition BEFORE UPDATE ON public.platform_admin_invitations FOR EACH ROW EXECUTE FUNCTION phase715_assert_invitation_transition()","function":"phase715_assert_invitation_transition()"}
{"audit":"triggers","table":"platform_admin_invitations","name":"trg_phase717_cancel_terminal_invitation_email","enabled":"O","definition":"CREATE TRIGGER trg_phase717_cancel_terminal_invitation_email AFTER UPDATE OF status ON public.platform_admin_invitations FOR EACH ROW EXECUTE FUNCTION phase717_cancel_terminal_invitation_email()","function":"phase717_cancel_terminal_invitation_email()"}
{"audit":"triggers","table":"student_attendance","name":"trg_student_attendance_tenant_guard","enabled":"O","definition":"CREATE TRIGGER trg_student_attendance_tenant_guard BEFORE INSERT OR UPDATE ON public.student_attendance FOR EACH ROW EXECUTE FUNCTION student_attendance_tenant_guard()","function":"student_attendance_tenant_guard()"}
{"audit":"triggers","table":"student_notifications","name":"trg_student_notifications_tenant_guard","enabled":"O","definition":"CREATE TRIGGER trg_student_notifications_tenant_guard BEFORE INSERT OR UPDATE ON public.student_notifications FOR EACH ROW EXECUTE FUNCTION trg_student_notifications_tenant_guard()","function":"trg_student_notifications_tenant_guard()"}
{"audit":"triggers","table":"student_results","name":"trg_student_results_tenant_guard","enabled":"O","definition":"CREATE TRIGGER trg_student_results_tenant_guard BEFORE INSERT OR UPDATE ON public.student_results FOR EACH ROW EXECUTE FUNCTION student_results_tenant_guard()","function":"student_results_tenant_guard()"}
{"audit":"triggers","table":"students","name":"test_student_visibility","enabled":"O","definition":"CREATE TRIGGER test_student_visibility AFTER UPDATE OF approval_status, is_active, status, program_id, academic_year_id ON public.students FOR EACH ROW EXECUTE FUNCTION refresh_student_test_visibility()","function":"refresh_student_test_visibility()"}
{"audit":"triggers","table":"students","name":"trg_reconcile_faculty_attendance_roster","enabled":"O","definition":"CREATE TRIGGER trg_reconcile_faculty_attendance_roster AFTER INSERT OR UPDATE OF register_number, university_roll_number, approval_status, status, is_active ON public.students FOR EACH ROW EXECUTE FUNCTION reconcile_faculty_attendance_roster_student()","function":"reconcile_faculty_attendance_roster_student()"}
{"audit":"triggers","table":"user_roles","name":"trg_phase613_user_roles_scope","enabled":"O","definition":"CREATE TRIGGER trg_phase613_user_roles_scope BEFORE INSERT OR UPDATE OF scope_type, scope_id, scope_organization_id ON public.user_roles FOR EACH ROW EXECUTE FUNCTION phase613_assert_role_scope()","function":"phase613_assert_role_scope()"}
{"audit":"triggers","table":"user_roles","name":"trg_phase712_super_admin_scope","enabled":"O","definition":"CREATE TRIGGER trg_phase712_super_admin_scope BEFORE INSERT OR UPDATE OF role_id, scope_type, scope_id, scope_organization_id ON public.user_roles FOR EACH ROW EXECUTE FUNCTION phase712_assert_super_admin_scope()","function":"phase712_assert_super_admin_scope()"}
{"audit":"public_views","count":0}
~~~

### Installed authority-scope guards

These guards check relationship/scope shape; they do not authenticate a caller or authorize a role assignment. Full definitions were inspected; the catalog text is preserved here.


~~~sql
CREATE OR REPLACE FUNCTION public.phase613_assert_role_scope()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    institution_organization_id uuid;
BEGIN
    IF NEW."scope_type" <> 'institution'::text THEN
        RETURN NEW;
    END IF;

    SELECT "i"."organization_id"
        INTO institution_organization_id
        FROM "public"."institutions" AS "i"
        WHERE "i"."institution_id" = NEW."scope_id";

    IF institution_organization_id IS NULL
       OR institution_organization_id IS DISTINCT FROM NEW."scope_organization_id" THEN
        RAISE EXCEPTION
            'Phase 6.13: institution scope % is not inside organization scope %',
            NEW."scope_id", NEW."scope_organization_id"
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$function$

~~~

~~~sql
CREATE OR REPLACE FUNCTION public.phase712_assert_super_admin_scope()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
DECLARE
    role_name text;
BEGIN
    SELECT "r"."name"
      INTO role_name
      FROM "public"."roles" AS "r"
     WHERE "r"."id" = NEW."role_id";

    IF role_name = 'super_admin'
       AND (
           NEW."scope_type" <> 'platform'
           OR NEW."scope_id" IS NOT NULL
           OR NEW."scope_organization_id" IS NOT NULL
       ) THEN
        RAISE EXCEPTION 'Phase 7.12: super_admin requires platform scope'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$function$

~~~

## Appendix E — Environment, population and final verification

~~~json
{"audit":"environment","utc":"2026-10-10T07:19:14.174122+00:00","database":"postgres","role":"postgres","server_version":"17.6","transaction_read_only":"on","default_transaction_read_only":"on","schema_acl":"{pg_database_owner=UC/pg_database_owner,=U/pg_database_owner,postgres=U/pg_database_owner,anon=U/pg_database_owner,authenticated=U/pg_database_owner,service_role=U/pg_database_owner}","builtin_function_acl":"{=X/postgres,postgres=X/postgres}"}
{"audit":"counts","students":0,"attendance":0,"results":0,"items":0,"notifications":0,"outbox":0,"invitations":0,"delivery_attempts":0,"delivery_events":0}
~~~
~~~json
{"audit":"final_environment","utc":"2026-10-10T07:20:03.816731+00:00","transaction_read_only":"on","default_transaction_read_only":"on","tables_rls_disabled":5,"exposed_definer_overloads":6,"student_rows":0,"outbox_rows":0}
~~~

## Appendix F — Exact read-only collection queries

All statements below were sent through container-local psql with read-only PGOPTIONS. Definition SELECTs read text without invoking the target functions. Queries of role catalogs intentionally exclude credential-bearing fields.

### catalogSql

~~~sql
SELECT json_build_object('audit','tables','name',c.relname,'oid',c.oid,'owner',pg_get_userbyid(c.relowner),'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,'acl',c.relacl::text,'policies',(SELECT count(*) FROM pg_policy WHERE polrelid=c.oid),'column_acls',(SELECT count(*) FROM pg_attribute WHERE attrelid=c.oid AND attnum>0 AND NOT attisdropped AND attacl IS NOT NULL),'effective',(SELECT json_object_agg(r.rolname,(SELECT json_agg(p ORDER BY p) FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN']) p WHERE has_table_privilege(r.oid,c.oid,p))) FROM pg_roles r WHERE r.rolname IN ('anon','authenticated','service_role'))) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN ('students','student_attendance','student_results','student_result_items','student_notifications') ORDER BY c.relname;
SELECT json_build_object('audit','role','role',rolname,'inherit',rolinherit,'superuser',rolsuper,'bypass_rls',rolbypassrls,'login',rolcanlogin) FROM pg_roles WHERE rolname IN ('postgres','supabase_admin','anon','authenticated','service_role','authenticator') ORDER BY rolname;
SELECT json_build_object('audit','memberships','role',pg_get_userbyid(roleid),'member',pg_get_userbyid(member),'grantor',pg_get_userbyid(grantor),'admin_option',admin_option,'inherit_option',inherit_option,'set_option',set_option) FROM pg_auth_members ORDER BY roleid,member;
SELECT json_build_object('audit','client_reachable_roles','client',c.rolname,'role',r.rolname,'member',pg_has_role(c.oid,r.oid,'MEMBER'),'inherited',pg_has_role(c.oid,r.oid,'USAGE'),'settable',pg_has_role(c.oid,r.oid,'SET')) FROM pg_roles c CROSS JOIN pg_roles r WHERE c.rolname IN ('anon','authenticated') AND (pg_has_role(c.oid,r.oid,'MEMBER') OR pg_has_role(c.oid,r.oid,'USAGE') OR pg_has_role(c.oid,r.oid,'SET')) ORDER BY c.rolname,r.rolname;
SELECT json_build_object('audit','defaults','creator',pg_get_userbyid(d.defaclrole),'schema',CASE WHEN d.defaclnamespace=0 THEN '(global)' ELSE n.nspname END,'object_type',d.defaclobjtype,'acl',d.defaclacl::text) FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace WHERE d.defaclnamespace=0 OR n.nspname='public' ORDER BY d.defaclrole,d.defaclnamespace,d.defaclobjtype;
~~~

### routineSql

~~~sql
SELECT json_build_object('audit','routine','oid',p.oid,'signature',p.oid::regprocedure::text,'owner',pg_get_userbyid(p.proowner),'kind',p.prokind,'definer',p.prosecdef,'volatility',p.provolatile,'config',p.proconfig,'arguments',pg_get_function_arguments(p.oid),'default_args',p.pronargdefaults,'result',pg_get_function_result(p.oid),'acl',p.proacl::text,'public_execute',EXISTS(SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0 AND a.privilege_type='EXECUTE'),'anon',has_function_privilege('anon',p.oid,'EXECUTE'),'authenticated',has_function_privilege('authenticated',p.oid,'EXECUTE'),'service_role',has_function_privilege('service_role',p.oid,'EXECUTE')) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname IN ('phase717_claim_email_outbox','phase717_complete_email_outbox','phase717_create_invitation_with_outbox','phase717_resolve_email_outbox_context','phase717_rotate_invitation_with_outbox','phase718_reconcile_mailgun_event','phase717_cancel_terminal_invitation_email','phase723_approve_membership_with_invitation') ORDER BY p.proname,p.oid;
SELECT json_build_object('audit','definition','signature',p.oid::regprocedure::text,'definition',pg_get_functiondef(p.oid)) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname IN ('phase717_claim_email_outbox','phase717_complete_email_outbox','phase717_create_invitation_with_outbox','phase717_resolve_email_outbox_context','phase717_rotate_invitation_with_outbox','phase718_reconcile_mailgun_event') ORDER BY p.proname,p.oid;
~~~

### relatedSql

~~~sql
SELECT json_build_object('audit','related_table','name',c.relname,'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,'acl',c.relacl::text,'policies',(SELECT count(*) FROM pg_policy WHERE polrelid=c.oid),'client_select',has_table_privilege('anon',c.oid,'SELECT'),'client_insert',has_table_privilege('anon',c.oid,'INSERT'),'client_update',has_table_privilege('anon',c.oid,'UPDATE'),'client_delete',has_table_privilege('anon',c.oid,'DELETE'),'authenticated_update',has_table_privilege('authenticated',c.oid,'UPDATE')) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN ('users','user_roles','roles','role_permissions','permissions','user_permission_grants','institutions','platform_admin_invitations','email_outbox','email_delivery_attempts','email_delivery_events') ORDER BY c.relname;
SELECT json_build_object('audit','triggers','table',c.relname,'name',t.tgname,'enabled',t.tgenabled,'definition',pg_get_triggerdef(t.oid),'function',t.tgfoid::regprocedure::text) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN ('students','student_attendance','student_results','student_result_items','student_notifications','user_roles','platform_admin_invitations') AND NOT t.tgisinternal ORDER BY c.relname,t.tgname;
SELECT json_build_object('audit','publication','publication',pubname,'schema',schemaname,'table',tablename) FROM pg_publication_tables WHERE schemaname='public' AND tablename IN ('students','student_attendance','student_results','student_result_items','student_notifications');
SELECT json_build_object('audit','public_views','count',count(*)) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('v','m');
SELECT json_build_object('audit','migration_ledger','versions',json_agg(version ORDER BY version)) FROM supabase_migrations.schema_migrations;
~~~

### guardSql

~~~sql
SELECT json_build_object('audit','environment','utc',clock_timestamp(),'database',current_database(),'role',current_user,'server_version',current_setting('server_version'),'transaction_read_only',current_setting('transaction_read_only'),'default_transaction_read_only',current_setting('default_transaction_read_only'),'schema_acl',(SELECT nspacl::text FROM pg_namespace WHERE nspname='public'),'builtin_function_acl',acldefault('f',(SELECT oid FROM pg_roles WHERE rolname='postgres'))::text);
SELECT json_build_object('audit','counts','students',(SELECT count(*) FROM public.students),'attendance',(SELECT count(*) FROM public.student_attendance),'results',(SELECT count(*) FROM public.student_results),'items',(SELECT count(*) FROM public.student_result_items),'notifications',(SELECT count(*) FROM public.student_notifications),'outbox',(SELECT count(*) FROM public.email_outbox),'invitations',(SELECT count(*) FROM public.platform_admin_invitations),'delivery_attempts',(SELECT count(*) FROM public.email_delivery_attempts),'delivery_events',(SELECT count(*) FROM public.email_delivery_events));
SELECT json_build_object('audit','guard_definition','signature',p.oid::regprocedure::text,'definition',pg_get_functiondef(p.oid)) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname IN ('phase613_assert_role_scope','phase712_assert_super_admin_scope','student_attendance_tenant_guard','student_results_tenant_guard','trg_student_notifications_tenant_guard');
~~~

### finalSql

~~~sql
SELECT json_build_object('audit','final_environment','utc',clock_timestamp(),'transaction_read_only',current_setting('transaction_read_only'),'default_transaction_read_only',current_setting('default_transaction_read_only'),'tables_rls_disabled',(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN ('students','student_attendance','student_results','student_result_items','student_notifications') AND NOT c.relrowsecurity),'exposed_definer_overloads',(SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname IN ('phase717_claim_email_outbox','phase717_complete_email_outbox','phase717_create_invitation_with_outbox','phase717_resolve_email_outbox_context','phase717_rotate_invitation_with_outbox','phase718_reconcile_mailgun_event') AND p.prosecdef AND has_function_privilege('anon',p.oid,'EXECUTE') AND has_function_privilege('authenticated',p.oid,'EXECUTE')),'student_rows',(SELECT count(*) FROM public.students),'outbox_rows',(SELECT count(*) FROM public.email_outbox));
~~~

## Appendix G — Current source fingerprints

SHA-256 hashes below describe current source bytes, not historical applied statements. All 528 inventoried files were rehashed after report creation: zero changed, zero added within the inventoried source directories, and zero removed. This bounded table records all migrations and the principal inspected sources/configuration/preflight report. Git status confirms that this report is the sole additional working-tree artifact relative to the initial status.

| File | SHA-256 |
| --- | --- |
| backend/app/api/admin_invitations.py | cea4896e4d327605dffe77cc1af51b3824e09e244e90e7253087220f9de7f1bd |
| backend/app/api/admin.py | 2f9d472433447bdde6d8bfbef9b16b6b07d6152a3bfc4c870d1fc080e68b5895 |
| backend/app/api/mailgun_webhooks.py | 80b65630c40388ed61ff4a2e7268f869148ea486584c4d01866c8398b95bd8ca |
| backend/app/api/platform.py | ea9ebd2e00454ee68314f471433fcabd1c821580cf433955fbd8ba25b92df4b9 |
| backend/app/core/security.py | 78c74d4996e311153fee7b0412642abccb8add9232639a5d6fe2f0dd95f2f6eb |
| backend/app/db/supabase.py | c5c36679afd0c071e494083617da48f0bbab8c2e469139411799f2428a40fbe6 |
| backend/app/repositories/email_outbox.py | 78f714270cf9801dd580ac7cc8d924eabcbcd01ba3387fc075b12e47d820328a |
| backend/app/repositories/platform_admin_invitations.py | ab4fc683d5dee7dcdf84d8ec3ac6d6ced10334a665252c0ea5af3431bd88569a |
| backend/app/repositories/results.py | 8b8a8ca2884828ab64f0d3110255263e100797c45e57a01041543f2b7e5e1312 |
| backend/app/services/attendance.py | 630cc0aa0c742d66b1191e1af53acbb07a8427a23f512f8223c7c142dd00c65c |
| backend/app/services/authorization.py | 565f519fd20160a3b23f83b5cf977a88824c063e2a83ab892abc9e7c108f7587 |
| backend/app/services/email_outbox_worker.py | 477268b917979e23fcea84855b23658427bef2b69b0df324e917839d37bdd004 |
| backend/app/services/faculty_attendance.py | b512769c4f3bf380ca032e6cfad3a24509d1ab8cbabd5ff5e37dd7042fca51e5 |
| backend/app/services/faculty_tests.py | aa6f441ea6a7c4300053712c88f3b6383643b1cf9f8ba29cc5604136203e605c |
| backend/app/services/mailgun_webhooks.py | 867f0463813a42cb36adf36ae33be02d2bfbb633df0cfc494f581d63a7ed81b3 |
| backend/app/services/platform_admin_invitations.py | e07be0f6824fe66bc9f8b22f092e244cdb5a4ac0d0be6fabca8f91486590987c |
| backend/app/services/student_context.py | 6cdcb67ee82d6a76f3ec84ce84230a77c7b00289b3da391d5dc8e272a7fa6cb1 |
| backend/app/services/student_data.py | 19d45db180b1fae9f03f8f9bc96de395ce06b05475b1e649cdb1311ece623efe |
| backend/app/services/student_notifications.py | b4354bc846f332cdca4a152b2dd104cd232f02bad10ec473444a847dbe3434b0 |
| backend/app/services/student_results.py | 347041bb16ec0abbd986cdbd287b6e5634071f45ef2629a4c76462b5d27182ae |
| backend/tests/test_phase_7_17_email_outbox_worker.py | bf8f2bdfc01ae3017bc8d513aadf9ab3ba0923ea2a007e103141349ae399310d |
| backend/tests/test_phase_7_18_mailgun_delivery_webhooks.py | bbec980603b40cc6b90a4295457acee2a871021d22795abae9a30b8a246dd6dc |
| M1_PREFLIGHT_AUDIT_REPORT.md | 7e65631d9e6d6d5badc942858285b5f517cb5f196d9c342fce918b677cabc6a7 |
| supabase/config.toml | a5509eb9cf974e9e1cfc5d39b4a5814f9e573e0ef18678a745ab1d7d1a82f500 |
| supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql | 7fd1ea5c096eb47667a2ba55cc1bf4a872c959e12300c2110a69a698ca6e6429 |
| supabase/migrations/20250718000000_phase_3_6_embeddings.sql | 21230835555e0353b124c8314c72948c97ece834beafccdb7e89f9fe6412f2aa |
| supabase/migrations/20260905000000_phase_3_7_1_vector_search_index.sql | da5e2f8a7c35c3ebee708bd977b9ebfc048f3666e06d26bf3c9edc7d7729df80 |
| supabase/migrations/20260905000001_phase_3_7_2_vector_similarity_search.sql | c1dc20ecfba849522dba9c26e0393ce9060044c2ce8363d93846d205835240e4 |
| supabase/migrations/20260905000002_phase_3_8_metadata_access_filtering.sql | fa6e41711c7485ee373306ca2cd3a1d37ff5e7489d56ff8d0e24f167e6fd0fa7 |
| supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql | 0e70348067cf8096adff2bcef47587de70c889e55d55b43907fc9b069091009f |
| supabase/migrations/20260909000001_phase_admin_2_extracted_text_column.sql | 986f739f0506e5b3f1dce55f9b69a41b31a21fe66553bce006b251a51d6008e3 |
| supabase/migrations/20260909000002_phase_admin_2_faq_published_column.sql | 9641a4c31bc7a58e4440d2a966b2fe61ea0b1ff9ccd68f5dfa03a3cc007656d4 |
| supabase/migrations/20260909000003_phase_admin_2_notice_published_column.sql | d70ebfc843866f85129944d9630ec52e4f515ed9e528936ed589662c22336e28 |
| supabase/migrations/20260912000000_phase_6_2_student_identity_model.sql | a2b8793d3073bf7130497a828ff2f33c101f6db7788110c5adafe5dd46c67e57 |
| supabase/migrations/20260913000000_phase_6_7_attendance.sql | 365de679d8ce9edf278cfe117ae5496b2e2996ce2f0975e0d35c8542f343a423 |
| supabase/migrations/20260913010000_phase_6_8_results.sql | c9b3d84ee8f3cfb8b94943a3eb8f9b8006315f79ffb8c32ef63eceae73925fd9 |
| supabase/migrations/20260914000000_phase_6_11_student_notifications.sql | f105032d0a821755a0c13a79462907d3f58b983797a21e338aa97e6879c07f47 |
| supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql | e74e4fe768ec9c2cb0dd452bbf5c42617797574ba18daa9a7fcab8fdd633b637 |
| supabase/migrations/20260928000000_phase_7_2_public_knowledge_policy.sql | 2a43a3c2c3093a3405c809ccd26a4da8689440c5fbd8eb3264500eccf66600a5 |
| supabase/migrations/20260928010000_phase_7_4_public_rag_hardening.sql | d52fe69d7e1037f7cdecf1af1a2ca4e840164e0042f17afc3250dd1ff4076092 |
| supabase/migrations/20260929000000_phase_7_10_legacy_primary_key_convergence.sql | 5be4401f19629449017963db2084e3ac90b2b54dad4c0406b78b828ae6bd3c5c |
| supabase/migrations/20261001000000_phase_7_12_super_admin_identity_authorization.sql | 4aa88e05e5e893ec393a95941ad581fa902e4992aa49a47287a5f1f3676aa27d |
| supabase/migrations/20261001010000_phase_7_13_super_admin_institution_management.sql | bbc87fb76863894a68744396151c24c1bf8eca64bbfb30955b5693681bf72e7c |
| supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql | 1d59c03c1535c8328d153b31c77c082372a65acdaf75bf3f914b8710acecbef8 |
| supabase/migrations/20261001030000_phase_7_15_invitation_delivery_email_verification.sql | 27d2aaa03f376748a8f640e6841d9506b8b77a527b425a2864c68c804a244892 |
| supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql | 0a52abea3da21e8a1763e19e167572549ce3434296afb4654913d71c9394a7f2 |
| supabase/migrations/20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql | 77e8b695e3b512907e04b66548fa533d5a76af644b288d4c9249eb713b0e045e |
| supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql | 30a51b837e5b988b64b4f41decf15386c0e531e0ee5b3036ee91be16ba3d3f2e |
| supabase/migrations/20261004010000_admin_published_flags_schema_convergence.sql | 92d25a5fa3b1a2658068ed1bd240a78376bdbc64b7aea1fe4952442129fc6c19 |
| supabase/migrations/20261004235959_permission_primary_key_convergence.sql | 813d843c8ff0e24f9950b92134a69c75bdd6bcfa465194df100f63f522c0c25b |
| supabase/migrations/20261005000000_phase_8_granular_permissions.sql | 48a16106676dcd225479f3582b5a2036f5da0f736176037fe1cbf043c9a55a42 |
| supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql | 764489c42aa6542fa08c4a3c415b16be63bc42c6efbe481c3346e12798c4c716 |
| supabase/migrations/20261007000000_phase_9_auth_security_events.sql | fa7747315c474b5684a45fe584a76a7594b36cf81043ec8badd24d8cd6f71270 |
| supabase/migrations/20261008000000_phase_9_super_admin_invitations.sql | 88e6b4a9bb314a47fbcf1879d521653c279fb9d3224200d050f271f65ef7f606 |
| supabase/migrations/20261009000000_phase_7_24_immediate_staff_faculty_approval.sql | 71a58d4e62dd4902bc0de489f9d9db66cccc6eae563fd50636b6f2465ce2fd2e |
| supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql | 2f93ece8b89e006b61e46fe25f62ef79fec8c58e81b9fe7a835270069321c49b |
| supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql | 5938051c99abecc3d582e213341d39e62d4430f5a90655091d42fe59c2f7c94c |
| supabase/migrations/20261012000000_faculty_attendance_workflow.sql | 287e93f20bf6c5d1e91ac49b32c05d3468ea3ece549b84d789a295113402119f |
| supabase/migrations/20261013000000_faculty_tests_examination.sql | 74186837ca7289041ffb88cc80d23d5a7dbc5194369849d8a098a7ba974c231e |
| supabase/migrations/20261014000000_scoped_faculty_teaching_assignment_management.sql | ff4d27a703c7d572579560f280c99e049be7f35a279c7d616229e513d5b62519 |
| supabase/migrations/20261015000000_student_academic_experience_read_indexes.sql | b5ccc9f28e354303136e665777e531524ae8bd15e62e6fa676440cddbc4ffcea |
| supabase/migrations/20261016000000_academic_master_data_management.sql | a4d7ca4814b126d4322d66c6ae71fcd7a4d68407223506fe52d82bdc5a07004b |
| supabase/migrations/20261016010000_academic_curriculum_semester_convergence.sql | 3c98b7aa8207176a1c60195ba2bf11ca709afe1a297c0dac71d589fd0d024c33 |

