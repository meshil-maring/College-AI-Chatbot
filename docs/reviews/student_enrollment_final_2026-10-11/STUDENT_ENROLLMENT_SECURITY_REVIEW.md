# Student enrollment security review

2026-10-11 (Asia/Calcutta). Static repository review only. No catalog queried, database connected, SQL executed, credential inspected or remote Supabase contacted.

## Conflicting findings and provenance

| Evidence | What is established | What is not established |
| --- | --- | --- |
| `docs/security/PHASE_10_SECURITY_AUDIT.md` (2026-10-05) | Earlier architecture report claims sensitive migration access is withheld; records meaningful FastAPI identity/tenant checks | It is not a present catalog assertion that all legacy tables and all overloads deny clients. |
| `M1_PREFLIGHT_AUDIT_REPORT.md` (2026-10-10, local PostgreSQL 17.6) | Historical report records five student academic tables with RLS off/client CRUD and six exposed definer signatures; 39 ledger versions and empty audited populations | Not today's installed state or any remote state. Zero population does not validate populated backfill. |
| `SECURITY_REMEDIATION_PLANNING_REPORT.md` (2026-10-10, refreshed local snapshot) | Historical report corroborates defects, adds writable `users/user_roles/roles/role_permissions/permissions/institutions`, records exact ACLs/defaults/role memberships and embedded proposed fixes | Proposed REVOKE/default-ACL SQL is not proof a remediation migration ran. No standalone earlier security migration was recovered; proposals reside in this report. |
| Current exact migrations inspected | Baseline explicitly gives future client FUNCTION EXECUTE defaults. Outbox and Mailgun drafts revoke PUBLIC only on reported routines. Seven-argument invitation overload has explicit client revokes. Legacy student/attendance/consolidated result/notification creation lacks comprehensive client revocation. Faculty-test migration explicitly revokes anon/authenticated test_results access. Master data migration explicitly restricts clients and adds guards. | Current source text is not installed ACL truth; bootstrap/default/global/column/inherited grants and applied-byte differences need inspection. |

The findings are reconciled by evidence scope: the broad architecture statement does not disprove the later named-catalog observations. Neither historical snapshot is assumed to describe today's database. The candidate core schema requires security containment as a prerequisite, checks it without repairing existing objects, and fails if the expected denial is absent.

## Access matrix

| Resource | anon/authenticated/PUBLIC | Backend service_role | Function owner / maintenance |
| --- | --- | --- | --- |
| Four new tables | No table/column grants; explicit restrictive deny policy; RLS enabled | SELECT only, across tenants; all application reads must scope own/authorized records | Owns objects, mutations only through reviewed routines by convention; owner authority is a maintenance boundary |
| New command and handoff RPCs | No EXECUTE, including every overload | EXECUTE only on two entry points; active institution-admin + granular permission checked; service role claim required | Owner retains EXECUTE; functions use empty search_path and qualified application relations |
| New trigger/internal helpers | No EXECUTE | No EXECUTE; trigger invocation and definer nesting do not require exposing helper RPCs | Only owner; no clients can invoke arbitrary event writer |
| Legacy five academic tables | Recommend backend-only, no client allow policies; all table/column/utility privileges denied | Preserve required SELECT/INSERT/UPDATE/DELETE for current compensation/import/item/read-mark workflows until adapters migrate | Preserve existing integrity triggers pending reviewed replacements |
| Authority tables and direct grants | No client mutation; recommend backend-only reads too after consumer review | Existing server authority reads and controlled lifecycle routines | Scope shape guards do not authorize who can grant roles |
| Outbox/invitation routines | Deny all reported and subsequently discovered overloads | Keep worker/platform/onboarding behavior and required nested EXECUTE | Preserve signatures; do not change SECURITY mode solely to repair ACLs |

The client restrictive policies are defense in depth; no client grants are allowed. The new tables use a service-role SELECT policy so a backend without BYPASSRLS can still read, but no service INSERT/UPDATE/DELETE policy or direct privilege exists. FORCE RLS is not presented as a remedy for privileged service access. PostgreSQL states that BYPASSRLS bypasses row security and that TRUNCATE/REFERENCES are outside it; ACL denial remains essential. [PostgreSQL 17 row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)

## Required future catalog collection (do not run during this review)

Record target identity, local disposable container ownership/token/image, role/session, PostgreSQL version, UTC/IST timestamp, Git/DDL hash and exact collection queries. Do not dump credentials or record payloads. Inspect:

1. `pg_class`, `pg_namespace`, `pg_attribute`: owner, table/partition/view exposure, relrowsecurity/relforcerowsecurity, dropped/generated columns, independent column ACLs and all non-internal triggers. Include parents/children and referenced authority tables, not just four new tables.
2. `aclexplode(COALESCE(acl,acldefault(...)))`: PUBLIC, direct roles, grant options and all unexpected grantees; `has_table_privilege` for SELECT/INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN, `has_column_privilege` for SELECT/INSERT/UPDATE/REFERENCES. A table REVOKE alone does not remove independent column grants. [PostgreSQL REVOKE](https://www.postgresql.org/docs/17/sql-revoke.html)
3. `pg_policy`: every policy, target role, command, permissive/restrictive flag, USING/WITH CHECK expression and policy OR-combination. No unreviewed PUBLIC/client permissive policy, view or security-definer bridge may expose these records. A role's grant and an RLS policy are separate requirements.
4. `pg_roles`, `pg_auth_members`, `pg_has_role(...,'MEMBER'/'USAGE'/'SET')`: direct/inherited/settable access, INHERIT, superuser/BYPASSRLS/owner access and grant options. Preserve intended PostgREST authenticator role switching. Direct REVOKE does not defeat an inherited privileged parent.
5. `pg_proc` and `pg_get_function_identity_arguments/pg_get_functiondef`: **all overloads**, default arguments, owner, SECURITY DEFINER, language, volatility and proconfig/search_path. Check PUBLIC using expanded default ACL, and effective client/backend EXECUTE individually. `CREATE OR REPLACE FUNCTION` preserves ACLs; body replacement is not an ACL fix. Harden definer lookup and revoke inside the creation transaction. [PostgreSQL CREATE FUNCTION](https://www.postgresql.org/docs/17/sql-createfunction.html)
6. `pg_default_acl`: global plus public-schema defaults for the actual creators, including postgres and supabase_admin if present. Current baseline client routine defaults can recreate exposure. Existing objects need explicit ACLs regardless. Changes to another creator's defaults need that creator or an authorized executor; do not alter role memberships to force it through. Schema-only defaults cannot subtract builtin/global PUBLIC routine EXECUTE.
7. Extension schema/opclasses (`btree_gist`), validated constraints, ready/valid partial indexes, exact trigger/function bindings and enabled state, sequences (new UUID/explicit event sequence uses no sequence object), publications, views, routines outside public and dependent PostgREST exposure. Inventory actual ledger and applied-source provenance separately.

The core postflight rejects unexpected core-table policies/grantees, effective column/client privileges, exposed helper overloads, missing RLS/deny policy, missing exclusive/unique protections and missing trigger bindings. It checks prerequisite object privilege denial, not every external view or function. Full prerequisite audit is therefore still required.

## Privileged workflow dependencies

The new draft reuses `phase81_assert_institution_admin(uuid,uuid)` from Phase 8.1 (requires service-role claim, active user/role/institution and institution scope) and `academic_master_tenant(text,uuid)` from master-data management. It also checks current DB permission rows (`permissions.permission_id`, `roles.id`, `role_permissions`, `user_permission_grants`) rather than treating a role name as full authority. Initial admission decisions use students.approve/reject; other mutations use students.create/update. Staff grant expansion is outside this design.

Review every overload of:

- `phase717_claim_email_outbox(integer,integer,integer)`;
- `phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)`;
- `phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)` and seven-argument overload ending in two text fields;
- `phase717_resolve_email_outbox_context(uuid,text)`;
- `phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)`;
- `phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)`.

Do not drop the six-argument invitation overload: current backend `repositories/platform_admin_invitations.py` uses it. Preserve worker queue leases, protected-token handling, webhook HMAC checks before database reconciliation, terminal invitation cancellation, and onboarding routines. Trigger-returning functions are not ordinary RPCs; restrict ACLs but retain legitimate trigger invocation.

Existing academic dependencies needing later coordinated replacement are enumerated in the migration plan. Some definer functions use `search_path=public` and unqualified names; review schema CREATE privileges and harden those bodies in a separately approved change. Do not add contradictory guards, disable `collegeai.test_write` protections, or drop roster/test marks security controls to pass tests.

## Service-role implications and audit

`backend/app/db/supabase.py` uses a cached secret-backed administrative client; its documentation explicitly says it bypasses RLS. Neither the SQL's service claim check nor an actor UUID proves the identity of the human caller if the backend is compromised. HTTP must derive actor from verified JWT and recheck active account, permission, tenant and target ownership before supplying internal arguments. Never forward caller-controlled Authorization into the cached privileged client. Database helper checks are a second boundary, not delegation of backend authority to a body field.

New direct service-role table writes are denied even if that role bypasses RLS. Definer routines use owner DML and explicit checks, deterministic operation/identity locks and before/after audit. Append-only triggers prevent ordinary UPDATE/DELETE/TRUNCATE, including accidental owner writes while triggers enabled; they cannot prevent an object owner/superuser from disabling or replacing protections. Restrictive actor FKs avoid FK-driven SET NULL updates to immutable events; retain/anonymize actors.

Events store bounded necessary provenance, not credentials, raw passwords, tokens, full imports or unnecessary student personal details. Human reasons/evidence references require backend validation/redaction. Students receive a separate safe projection, never raw internal request/result/event JSON. Audit failure is a mutation failure; never commit state while logging errors best-effort.

## Decision

No earlier security SQL is executed or approved here. Required containment includes trusted authority tables as well as student data and RPC overloads. A partial five-table fix is not sufficient to claim tenant authorization repaired. Live catalog verification and role-behavior tests require later explicit approval and an available validated disposable engine. Preserve security denials during rollback.
