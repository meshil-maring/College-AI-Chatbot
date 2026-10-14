-- SEPARATE POST-B05 SUCCESSOR DRAFT. NOT EXECUTED; not deployment approval.
-- Original SHA-256: 897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7
-- Source prerequisite: 20261017000000_b05_invitation_acceptance_security.sql.
-- Original candidate remains byte-for-byte intact, with its 11-column check.
-- Choose an approved pre-B05 containment sequence or independently approve this
-- successor after B05; neither candidate is assumed applied. B01-B07 remain open.
-- This successor adjusts the source-derived ledger preflight to 40 versions
-- including B05 and the audit preflight to the exact 12-column source contract
-- plus the named unique index/default/nullability checks. These are proposed
-- preconditions, not statements about any deployed ledger or applied source.
-- B05 private tables/RPCs and their owner/effective ACL/trigger behavior need
-- independent catalog review; this draft does not certify full B05 containment.
-- Both original unconditional stops and final ROLLBACK are retained.

-- REVIEW-ONLY — NOT FOR EXECUTION.
-- Prepared 2026-10-11 Asia/Calcutta. NOT PostgreSQL-validated. PostgreSQL 17 target.
-- Must not be copied into the production migration chain without independent approval.
-- Required preconditions / unresolved dependencies B01-B07:
-- Exact-byte approval; separately authorized fresh 40-file post-B05 replay/catalog comparison;
-- postgres ownership/creator and accepted service JWT/secret-key BYPASSRLS contract;
-- global postgres default effects across schemas/extensions and actual creators;
-- explicit future service helper/entry grants; external consumers/retention/revocation;
-- inherited/settable/view/RPC bridges and separate SC-06/SC-07 security assessment;
-- validated disposable engine/bootstrap/storage/cleanup/harness and role/concurrency tests.
-- This is the conditional BYPASSRLS form only; no service policy is guessed.
-- Future postgres/public service EXECUTE default removal remains BLOCKED B02.
-- One new helper was explicitly authorized by user: security_containment_prevent_audit_truncate().
-- No enrollment DDL/data/app change, role membership repair, adjacent ledger repair,
-- other creator/default scope, schema/body hardening or blanket function revoke.
-- B03: global cross-schema/extension/default creator acceptance remains unresolved.
-- B04: current catalog/byte/column/role/policy/view/RPC comparison remains unresolved.
-- B05: separate context/body/schema-hardening acceptance ordering remains unresolved.
-- B06: external consumers, retention/reset and revocation policy remain unresolved.
-- B07: exact-byte independent approval and disposable runtime prerequisites remain unresolved.
-- Both unconditional stops and final ROLLBACK remain. No SQL has been executed.
-- Statement/consumer/security review: SECURITY_CONTAINMENT_MIGRATION_REVIEW.md.

-- C001 | stage 0 | begin
BEGIN;

-- C002 | stage 0 | unconditional review stop
DO $review_stop$ BEGIN RAISE EXCEPTION 'REVIEW-ONLY: NOT FOR EXECUTION; independent exact-byte approval required'; END $review_stop$;

-- C003 | stage 0 | unresolved compatibility stop
DO $dependency_stop$ BEGIN RAISE EXCEPTION 'BLOCKED B01-B07: catalog/service/default/retention/security acceptance required for executable successor'; END $dependency_stop$;

-- C004 | stage 1 | catalog-only search path
SET LOCAL search_path = pg_catalog;

-- C005 | stage 1 | lock timeout
SET LOCAL lock_timeout = '5s';

-- C006 | stage 1 | statement timeout
SET LOCAL statement_timeout = '30s';

-- C007 | stage 1 | fail-closed preflight
DO $preflight$
DECLARE t text; r text; rel oid; sig text; b record; f record;
BEGIN
 IF current_user<>'postgres' OR session_user<>'postgres' OR
    pg_catalog.current_setting('server_version_num')::integer NOT BETWEEN 170000 AND 179999 THEN
  RAISE EXCEPTION 'Reviewed postgres executor and PostgreSQL 17 required'; END IF;
 FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=r AND NOT rolsuper) THEN
   RAISE EXCEPTION 'Missing/unexpected role: %',r; END IF;
 END LOOP;
 -- B01 acceptance required; a non-bypass variant needs separately reviewed policies.
 IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='service_role' AND rolbypassrls) THEN
  RAISE EXCEPTION 'Unaccepted service RLS mode'; END IF;
 FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_roles p WHERE
   (pg_catalog.pg_has_role(r,p.oid,'USAGE') OR pg_catalog.pg_has_role(r,p.oid,'SET'))
   AND (p.rolsuper OR p.rolbypassrls OR p.rolname IN ('postgres','service_role'))) THEN
   RAISE EXCEPTION 'Privileged inherited/settable role: %',r; END IF;
 END LOOP;
 IF pg_catalog.to_regclass('supabase_migrations.schema_migrations') IS NULL THEN
  RAISE EXCEPTION 'Approved full-chain replay/ledger evidence required'; END IF;
 -- Ledger versions alone do not attest applied bytes; external source/hash comparison required.
 IF (SELECT pg_catalog.array_agg(version::text ORDER BY version::text)
     FROM supabase_migrations.schema_migrations) IS DISTINCT FROM ARRAY['20250717000000','20250718000000','20260905000000','20260905000001','20260905000002','20260909000000','20260909000001','20260909000002','20260909000003','20260912000000','20260913000000','20260913010000','20260914000000','20260915000000','20260928000000','20260928010000','20260929000000','20261001000000','20261001010000','20261001020000','20261001030000','20261002000000','20261002010000','20261004000000','20261004010000','20261004235959','20261005000000','20261006000000','20261007000000','20261008000000','20261009000000','20261010000000','20261011000000','20261012000000','20261013000000','20261014000000','20261015000000','20261016000000','20261016010000','20261017000000']::text[] THEN
  RAISE EXCEPTION 'Expected exact 40-version source chain'; END IF;
 FOREACH t IN ARRAY ARRAY['admin_audit_log','users','user_roles','roles','role_permissions','permissions','institutions','user_permission_grants','students','student_attendance','student_results','student_result_items','student_notifications','departments','programs','courses','academic_years','semesters','program_courses','course_offerings','sections']::text[] LOOP
  rel:=pg_catalog.to_regclass('public.'||t);
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_class WHERE oid=rel AND relkind='r'
   AND NOT relispartition AND relowner='postgres'::regrole::oid)
   OR EXISTS(SELECT 1 FROM pg_catalog.pg_inherits WHERE inhrelid=rel OR inhparent=rel) THEN
   RAISE EXCEPTION 'Unreviewed table/type/owner/inheritance: %',t; END IF;
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_class c,
   LATERAL pg_catalog.aclexplode(COALESCE(c.relacl,pg_catalog.acldefault('r',c.relowner))) a
   WHERE c.oid=rel AND (a.grantee NOT IN (0,'postgres'::regrole::oid,'service_role'::regrole::oid,
    'anon'::regrole::oid,'authenticated'::regrole::oid) OR a.grantor<>'postgres'::regrole::oid))
   OR EXISTS(SELECT 1 FROM pg_catalog.pg_attribute c,LATERAL pg_catalog.aclexplode(c.attacl) a
   WHERE c.attrelid=rel AND c.attnum>0 AND NOT c.attisdropped AND
    (a.grantee NOT IN (0,'postgres'::regrole::oid,'service_role'::regrole::oid,
     'anon'::regrole::oid,'authenticated'::regrole::oid) OR a.grantor<>'postgres'::regrole::oid)) THEN
   RAISE EXCEPTION 'Unreviewed table/column grantee or grantor: %',t; END IF;
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_policy p WHERE p.polrelid=rel AND p.polpermissive AND
   (0=ANY(p.polroles) OR EXISTS(SELECT 1 FROM pg_catalog.pg_roles rr WHERE rr.oid=ANY(p.polroles) AND
    (pg_catalog.pg_has_role('anon',rr.oid,'USAGE') OR pg_catalog.pg_has_role('anon',rr.oid,'SET')
     OR pg_catalog.pg_has_role('authenticated',rr.oid,'USAGE') OR pg_catalog.pg_has_role('authenticated',rr.oid,'SET'))))) THEN
   RAISE EXCEPTION 'Unreviewed client permissive policy: %',t; END IF;
  IF NOT pg_catalog.has_table_privilege('service_role',rel,'SELECT') OR
     NOT pg_catalog.has_table_privilege('service_role',rel,'INSERT') OR
     (t<>'admin_audit_log' AND NOT pg_catalog.has_table_privilege('service_role',rel,'UPDATE')) OR
     (t=ANY(ARRAY['users','user_roles','roles','role_permissions','permissions','institutions','user_permission_grants','students','student_attendance','student_results','student_result_items','student_notifications']::text[]) AND NOT pg_catalog.has_table_privilege('service_role',rel,'DELETE')) THEN
   RAISE EXCEPTION 'Required service workflow grant missing: %',t; END IF;
 END LOOP;
 FOR b IN SELECT * FROM (VALUES ('student_attendance','trg_student_attendance_tenant_guard','public.student_attendance_tenant_guard()',23),
      ('student_results','trg_student_results_tenant_guard','public.student_results_tenant_guard()',23),
      ('student_notifications','trg_student_notifications_tenant_guard','public.trg_student_notifications_tenant_guard()',23),
      ('institutions','trg_phase613_institutions_status','public.phase613_sync_institution_status()',23),
      ('user_roles','trg_phase613_user_roles_scope','public.phase613_assert_role_scope()',23),
      ('user_roles','trg_phase712_super_admin_scope','public.phase712_assert_super_admin_scope()',23),
      ('admin_audit_log','phase81_admin_audit_append_only','public.phase81_prevent_audit_mutation()',27),
      ('students','trg_reconcile_faculty_attendance_roster','public.reconcile_faculty_attendance_roster_student()',21),
      ('students','test_student_visibility','public.refresh_student_test_visibility()',17),
      ('departments','academic_master_validate','public.validate_academic_master_record()',23),
      ('programs','academic_master_validate','public.validate_academic_master_record()',23),
      ('courses','academic_master_validate','public.validate_academic_master_record()',23),
      ('academic_years','academic_master_validate','public.validate_academic_master_record()',23),
      ('semesters','academic_master_validate','public.validate_academic_master_record()',23),
      ('program_courses','academic_master_validate','public.validate_academic_master_record()',23),
      ('course_offerings','academic_master_validate','public.validate_academic_master_record()',23),
      ('sections','academic_master_validate','public.validate_academic_master_record()',23)) x(tbl,trg,signature,trigger_type) LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_trigger WHERE tgrelid=pg_catalog.to_regclass('public.'||b.tbl)
   AND tgname=b.trg AND tgenabled='O' AND tgtype=b.trigger_type AND NOT tgisinternal
   AND tgfoid=pg_catalog.to_regprocedure(b.signature)) THEN RAISE EXCEPTION 'Guard changed: %.%',b.tbl,b.trg; END IF;
 END LOOP;
 FOREACH sig IN ARRAY ARRAY['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)','public.faculty_assignment_touch()','public.faculty_attendance_context_guard()','public.faculty_attendance_record_scope_guard()','public.faculty_attendance_set_updated_at()','public.faculty_responsibility_scope_guard()','public.phase613_assert_child_organization()','public.phase613_assert_role_scope()','public.phase613_sync_institution_status()','public.phase712_assert_super_admin_scope()','public.phase714_assert_invitation_transition()','public.phase715_assert_invitation_transition()','public.phase717_cancel_terminal_invitation_email()','public.phase81_prevent_audit_mutation()','public.reconcile_faculty_attendance_roster_student()','public.student_attendance_tenant_guard()','public.student_results_tenant_guard()','public.test_results_tenant_guard()','public.trg_student_notifications_tenant_guard()','public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)']::text[] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc WHERE oid=pg_catalog.to_regprocedure(sig)
   AND proowner='postgres'::regrole::oid AND prokind='f') THEN RAISE EXCEPTION 'Routine owner/identity changed: %',sig; END IF;
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_proc p,
   LATERAL pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
   WHERE p.oid=pg_catalog.to_regprocedure(sig) AND
    (a.grantee NOT IN (0,'postgres'::regrole::oid,'service_role'::regrole::oid,
     'anon'::regrole::oid,'authenticated'::regrole::oid) OR a.grantor<>'postgres'::regrole::oid)) THEN
   RAISE EXCEPTION 'Unreviewed routine grantee/grantor: %',sig; END IF;
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc p,
   LATERAL pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
   WHERE p.oid=pg_catalog.to_regprocedure(sig) AND a.grantee='service_role'::regrole::oid
   AND a.privilege_type='EXECUTE') THEN RAISE EXCEPTION 'Service helper/entry grant requires separate trace: %',sig; END IF;
 END LOOP;
 FOR f IN SELECT p.oid FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='public' AND p.proname=ANY(ARRAY['faculty_assignment_touch','faculty_attendance_context_guard','faculty_attendance_record_scope_guard','faculty_attendance_set_updated_at','faculty_responsibility_scope_guard','phase613_assert_child_organization','phase613_assert_role_scope','phase613_sync_institution_status','phase712_assert_super_admin_scope','phase714_assert_invitation_transition','phase715_assert_invitation_transition','phase717_cancel_terminal_invitation_email','phase717_claim_email_outbox','phase717_complete_email_outbox','phase717_create_invitation_with_outbox','phase717_resolve_email_outbox_context','phase717_rotate_invitation_with_outbox','phase718_reconcile_mailgun_event','phase81_prevent_audit_mutation','reconcile_faculty_attendance_roster_student','student_attendance_tenant_guard','student_results_tenant_guard','test_results_tenant_guard','trg_student_notifications_tenant_guard']::text[]) LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.unnest(ARRAY['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)','public.faculty_assignment_touch()','public.faculty_attendance_context_guard()','public.faculty_attendance_record_scope_guard()','public.faculty_attendance_set_updated_at()','public.faculty_responsibility_scope_guard()','public.phase613_assert_child_organization()','public.phase613_assert_role_scope()','public.phase613_sync_institution_status()','public.phase712_assert_super_admin_scope()','public.phase714_assert_invitation_transition()','public.phase715_assert_invitation_transition()','public.phase717_cancel_terminal_invitation_email()','public.phase81_prevent_audit_mutation()','public.reconcile_faculty_attendance_roster_student()','public.student_attendance_tenant_guard()','public.student_results_tenant_guard()','public.test_results_tenant_guard()','public.trg_student_notifications_tenant_guard()','public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)']::text[]) e(sig) WHERE f.oid=pg_catalog.to_regprocedure(e.sig)) THEN
   RAISE EXCEPTION 'Unexpected overload: %',f.oid::regprocedure; END IF;
 END LOOP;
 FOREACH sig IN ARRAY ARRAY['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)']::text[] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc WHERE oid=pg_catalog.to_regprocedure(sig)
   AND prosecdef AND 'search_path=""'=ANY(COALESCE(proconfig,ARRAY[]::text[]))) THEN
   RAISE EXCEPTION 'Sensitive routine mode/path changed: %',sig; END IF;
 END LOOP;
 FOREACH sig IN ARRAY ARRAY['public.faculty_assignment_touch()','public.faculty_attendance_context_guard()','public.faculty_attendance_record_scope_guard()','public.faculty_attendance_set_updated_at()','public.faculty_responsibility_scope_guard()','public.phase613_assert_child_organization()','public.phase613_assert_role_scope()','public.phase613_sync_institution_status()','public.phase712_assert_super_admin_scope()','public.phase714_assert_invitation_transition()','public.phase715_assert_invitation_transition()','public.phase717_cancel_terminal_invitation_email()','public.phase81_prevent_audit_mutation()','public.reconcile_faculty_attendance_roster_student()','public.student_attendance_tenant_guard()','public.student_results_tenant_guard()','public.test_results_tenant_guard()','public.trg_student_notifications_tenant_guard()']::text[] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc WHERE oid=pg_catalog.to_regprocedure(sig)
   AND prorettype='pg_catalog.trigger'::regtype::oid) THEN RAISE EXCEPTION 'Helper result changed: %',sig; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='public' AND p.proname='security_containment_prevent_audit_truncate') OR
  EXISTS(SELECT 1 FROM pg_catalog.pg_trigger WHERE tgrelid='public.admin_audit_log'::regclass
  AND (tgname='security_containment_admin_audit_no_truncate' OR (tgtype & 32)<>0)) THEN
  RAISE EXCEPTION 'Existing conflicting new helper/TRUNCATE guard'; END IF;
 -- Source-backed audit insert/constraint/default contract; definitions still need approved comparison.
 IF (SELECT count(*) FROM pg_catalog.pg_attribute WHERE attrelid='public.admin_audit_log'::regclass AND attnum>0 AND NOT attisdropped)<>12 THEN
  RAISE EXCEPTION 'Unexpected audit column layout'; END IF;
 FOR b IN SELECT * FROM (VALUES ('audit_id','uuid'),('actor_user_id','uuid'),('institution_id','uuid'),('action','text'),
  ('table_name','text'),('record_id','text'),('record_data','jsonb'),('ip_address','inet'),('user_agent','text'),
  ('status','text'),('performed_at','timestamptz'),('decision_key','text')) x(col,typ) LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_attribute WHERE attrelid='public.admin_audit_log'::regclass
   AND attname=b.col AND NOT attisdropped AND atttypid=pg_catalog.to_regtype(b.typ)) THEN RAISE EXCEPTION 'Audit column type changed: %',b.col; END IF;
 END LOOP;
 IF (SELECT count(*) FROM pg_catalog.pg_constraint WHERE conrelid='public.admin_audit_log'::regclass AND contype='p')<>1 OR
    (SELECT count(*) FROM pg_catalog.pg_constraint WHERE conrelid='public.admin_audit_log'::regclass AND contype='c')<>2 OR
    (SELECT count(*) FROM pg_catalog.pg_constraint WHERE conrelid='public.admin_audit_log'::regclass AND contype='f' AND confdeltype='r')<>2 OR
    EXISTS(SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid='public.admin_audit_log'::regclass AND NOT convalidated) THEN
  RAISE EXCEPTION 'Audit PK/check/restrictive FK contract changed'; END IF;
 FOREACH t IN ARRAY ARRAY['audit_id','actor_user_id','action','status','performed_at'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_attribute WHERE attrelid='public.admin_audit_log'::regclass
   AND attname=t AND attnotnull) THEN RAISE EXCEPTION 'Audit non-null contract changed: %',t; END IF;
 END LOOP;
 FOREACH t IN ARRAY ARRAY['audit_id','status','performed_at'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_attrdef ad
   ON ad.adrelid=a.attrelid AND ad.adnum=a.attnum WHERE a.attrelid='public.admin_audit_log'::regclass AND a.attname=t) THEN
   RAISE EXCEPTION 'Audit default missing: %',t; END IF;
 END LOOP;
 FOREACH sig IN ARRAY ARRAY['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)']::text[] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_language l ON l.oid=p.prolang
   WHERE p.oid=pg_catalog.to_regprocedure(sig) AND
   p.prorettype=CASE WHEN p.proname='phase717_claim_email_outbox' THEN 'public.email_outbox'::regtype::oid
    WHEN p.proname='phase717_complete_email_outbox' THEN 'pg_catalog.bool'::regtype::oid ELSE 'pg_catalog.jsonb'::regtype::oid END
   AND p.proretset=(p.proname='phase717_claim_email_outbox')
   AND p.pronargdefaults=CASE WHEN p.proname='phase717_complete_email_outbox' THEN 3 ELSE 0 END
   AND l.lanname=CASE WHEN p.proname='phase717_resolve_email_outbox_context' THEN 'sql' ELSE 'plpgsql' END) THEN
   RAISE EXCEPTION 'Sensitive return/default/language contract changed: %',sig; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM pg_catalog.pg_default_acl d,LATERAL pg_catalog.aclexplode(d.defaclacl) a
  WHERE d.defaclrole='postgres'::regrole::oid AND d.defaclobjtype='f' AND a.privilege_type='EXECUTE' AND
   ((d.defaclnamespace=0 AND a.grantee IN ('anon'::regrole::oid,'authenticated'::regrole::oid)) OR
    (d.defaclnamespace='public'::regnamespace::oid AND a.grantee=0))) THEN
  RAISE EXCEPTION 'Unexpected global client/schema PUBLIC defaults need extra approved scope'; END IF;
END $preflight$;

-- C008 | stage 2 | remove global PUBLIC default
ALTER DEFAULT PRIVILEGES FOR ROLE postgres REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC RESTRICT;

-- C009 | stage 2 | remove direct client defaults
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM anon, authenticated RESTRICT;

-- B05 successor preflight: exact extra-column contract, never a wildcard.
DO $b05_successor_layout$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute
   WHERE attrelid='public.admin_audit_log'::regclass AND attname='decision_key'
     AND attnum=12 AND NOT attisdropped AND NOT attnotnull AND NOT atthasdef
     AND atttypid='pg_catalog.text'::regtype::oid) THEN
   RAISE EXCEPTION 'B05 decision_key layout/default/nullability mismatch'; END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid
   JOIN pg_catalog.pg_am a ON a.oid=c.relam
   WHERE c.oid=pg_catalog.to_regclass('public.b05_decision_audit_key')
     AND i.indrelid='public.admin_audit_log'::regclass AND i.indisunique
     AND i.indisvalid AND i.indisready AND i.indnkeyatts=1 AND i.indnatts=1
     AND i.indkey::text='12' AND i.indpred IS NULL AND i.indexprs IS NULL
     AND a.amname='btree') THEN
   RAISE EXCEPTION 'B05 decision-key uniqueness contract mismatch'; END IF;
END $b05_successor_layout$;

-- C010 | stage 3 | exact client EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text) FROM PUBLIC, anon, authenticated RESTRICT;

-- C011 | stage 3 | retain explicit service EXECUTE
GRANT EXECUTE ON FUNCTION public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text) TO service_role;

-- C012 | stage 3 | exact client EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer) FROM PUBLIC, anon, authenticated RESTRICT;

-- C013 | stage 3 | retain explicit service EXECUTE
GRANT EXECUTE ON FUNCTION public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer) TO service_role;

-- C014 | stage 3 | exact client EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase717_claim_email_outbox(integer,integer,integer) FROM PUBLIC, anon, authenticated RESTRICT;

-- C015 | stage 3 | retain explicit service EXECUTE
GRANT EXECUTE ON FUNCTION public.phase717_claim_email_outbox(integer,integer,integer) TO service_role;

-- C016 | stage 3 | exact client EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz) FROM PUBLIC, anon, authenticated RESTRICT;

-- C017 | stage 3 | retain explicit service EXECUTE
GRANT EXECUTE ON FUNCTION public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz) TO service_role;

-- C018 | stage 3 | exact client EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase717_resolve_email_outbox_context(uuid,text) FROM PUBLIC, anon, authenticated RESTRICT;

-- C019 | stage 3 | retain explicit service EXECUTE
GRANT EXECUTE ON FUNCTION public.phase717_resolve_email_outbox_context(uuid,text) TO service_role;

-- C020 | stage 3 | exact client EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz) FROM PUBLIC, anon, authenticated RESTRICT;

-- C021 | stage 3 | retain explicit service EXECUTE
GRANT EXECUTE ON FUNCTION public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz) TO service_role;

-- C022 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.faculty_assignment_touch() FROM PUBLIC, anon, authenticated RESTRICT;

-- C023 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.faculty_attendance_context_guard() FROM PUBLIC, anon, authenticated RESTRICT;

-- C024 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.faculty_attendance_record_scope_guard() FROM PUBLIC, anon, authenticated RESTRICT;

-- C025 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.faculty_attendance_set_updated_at() FROM PUBLIC, anon, authenticated RESTRICT;

-- C026 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.faculty_responsibility_scope_guard() FROM PUBLIC, anon, authenticated RESTRICT;

-- C027 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase613_assert_child_organization() FROM PUBLIC, anon, authenticated RESTRICT;

-- C028 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase613_assert_role_scope() FROM PUBLIC, anon, authenticated RESTRICT;

-- C029 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase613_sync_institution_status() FROM PUBLIC, anon, authenticated RESTRICT;

-- C030 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase712_assert_super_admin_scope() FROM PUBLIC, anon, authenticated RESTRICT;

-- C031 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase714_assert_invitation_transition() FROM PUBLIC, anon, authenticated RESTRICT;

-- C032 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase715_assert_invitation_transition() FROM PUBLIC, anon, authenticated RESTRICT;

-- C033 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase717_cancel_terminal_invitation_email() FROM PUBLIC, anon, authenticated RESTRICT;

-- C034 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.phase81_prevent_audit_mutation() FROM PUBLIC, anon, authenticated RESTRICT;

-- C035 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.reconcile_faculty_attendance_roster_student() FROM PUBLIC, anon, authenticated RESTRICT;

-- C036 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.student_attendance_tenant_guard() FROM PUBLIC, anon, authenticated RESTRICT;

-- C037 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.student_results_tenant_guard() FROM PUBLIC, anon, authenticated RESTRICT;

-- C038 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.test_results_tenant_guard() FROM PUBLIC, anon, authenticated RESTRICT;

-- C039 | stage 3 | exact client helper EXECUTE denial
REVOKE ALL PRIVILEGES ON FUNCTION public.trg_student_notifications_tenant_guard() FROM PUBLIC, anon, authenticated RESTRICT;

-- C040 | stage 4 | deny client table access
REVOKE ALL PRIVILEGES ON TABLE public.admin_audit_log FROM PUBLIC, anon, authenticated RESTRICT;

-- C041 | stage 4 | deny service destructive and utility privileges
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN ON TABLE public.admin_audit_log FROM service_role RESTRICT;

-- C042 | stage 4 | remove service delegation options
REVOKE GRANT OPTION FOR SELECT, INSERT ON TABLE public.admin_audit_log FROM service_role RESTRICT;

-- C043 | stage 4 | deny independent column access/delegation
DO $audit_column_acl$
DECLARE c record;
BEGIN
 FOR c IN SELECT attname FROM pg_catalog.pg_attribute WHERE attrelid='public.admin_audit_log'::regclass
  AND attnum>0 AND NOT attisdropped LOOP
  EXECUTE pg_catalog.format('REVOKE SELECT (%1$I), INSERT (%1$I), UPDATE (%1$I), REFERENCES (%1$I) ON TABLE public.admin_audit_log FROM PUBLIC, anon, authenticated RESTRICT',c.attname);
  EXECUTE pg_catalog.format('REVOKE UPDATE (%1$I), REFERENCES (%1$I) ON TABLE public.admin_audit_log FROM service_role RESTRICT',c.attname);
  EXECUTE pg_catalog.format('REVOKE GRANT OPTION FOR SELECT (%1$I), INSERT (%1$I) ON TABLE public.admin_audit_log FROM service_role RESTRICT',c.attname);
 END LOOP;
END $audit_column_acl$;

-- C044 | stage 4 | retain backend read/append
GRANT SELECT, INSERT ON TABLE public.admin_audit_log TO service_role;

-- C045 | stage 4 | enable RLS conditional accepted BYPASSRLS branch
ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;

-- C046 | stage 4 | create authorized owner-only rejecting helper
CREATE FUNCTION public.security_containment_prevent_audit_truncate()
RETURNS pg_catalog.trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $guard$ BEGIN RAISE EXCEPTION 'Audit records cannot be truncated' USING ERRCODE = '42501'; END $guard$;

-- C047 | stage 4 | remove every client/service default EXECUTE grant
REVOKE ALL PRIVILEGES ON FUNCTION public.security_containment_prevent_audit_truncate() FROM PUBLIC, anon, authenticated, service_role RESTRICT;

-- C048 | stage 4 | bind distinct rejecting statement TRUNCATE guard
CREATE TRIGGER security_containment_admin_audit_no_truncate BEFORE TRUNCATE ON public.admin_audit_log FOR EACH STATEMENT EXECUTE FUNCTION public.security_containment_prevent_audit_truncate();

-- C049 | stage 5 | targeted table/column/RLS containment; master grants
DO $table_acl$
DECLARE t text; c record;
BEGIN
 FOREACH t IN ARRAY ARRAY['users','user_roles','roles','role_permissions','permissions','institutions','user_permission_grants','students','student_attendance','student_results','student_result_items','student_notifications','departments','programs','courses','academic_years','semesters','program_courses','course_offerings','sections']::text[] LOOP
  EXECUTE pg_catalog.format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM PUBLIC, anon, authenticated RESTRICT',t);
  FOR c IN SELECT attname FROM pg_catalog.pg_attribute WHERE attrelid=pg_catalog.to_regclass('public.'||t)
   AND attnum>0 AND NOT attisdropped LOOP
   EXECUTE pg_catalog.format('REVOKE SELECT (%1$I), INSERT (%1$I), UPDATE (%1$I), REFERENCES (%1$I) ON TABLE public.%2$I FROM PUBLIC, anon, authenticated RESTRICT',c.attname,t);
  END LOOP;
  EXECUTE pg_catalog.format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',t);
  IF t=ANY(ARRAY['departments','programs','courses','academic_years','semesters','program_courses','course_offerings','sections']::text[]) THEN
   EXECUTE pg_catalog.format('REVOKE DELETE, TRUNCATE ON TABLE public.%I FROM service_role RESTRICT',t);
   EXECUTE pg_catalog.format('GRANT SELECT, INSERT, UPDATE ON TABLE public.%I TO service_role',t);
  END IF;
 END LOOP;
END $table_acl$;

-- Stage 6: SC-06/SC-07 body/context/schema hardening is separately gated; no body replacement.
-- B02: future service default removal is blocked until explicit grant contract acceptance.
-- C050 | stage 7 | effective ACL/default/guard postflight
DO $postflight$
DECLARE t text; r text; priv text; rel oid; c record; f record; b record; sig text;
BEGIN
 FOREACH t IN ARRAY ARRAY['admin_audit_log','users','user_roles','roles','role_permissions','permissions','institutions','user_permission_grants','students','student_attendance','student_results','student_result_items','student_notifications','departments','programs','courses','academic_years','semesters','program_courses','course_offerings','sections']::text[] LOOP
  rel:=pg_catalog.to_regclass('public.'||t);
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_class WHERE oid=rel AND relrowsecurity AND relowner='postgres'::regrole::oid) THEN RAISE EXCEPTION 'RLS/owner missing: %',t; END IF;
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_class cc,LATERAL pg_catalog.aclexplode(COALESCE(cc.relacl,pg_catalog.acldefault('r',cc.relowner))) a
   WHERE cc.oid=rel AND a.grantee NOT IN ('postgres'::regrole::oid,'service_role'::regrole::oid)) OR
   EXISTS(SELECT 1 FROM pg_catalog.pg_attribute cc,LATERAL pg_catalog.aclexplode(cc.attacl) a
   WHERE cc.attrelid=rel AND cc.attnum>0 AND NOT cc.attisdropped AND a.grantee NOT IN ('postgres'::regrole::oid,'service_role'::regrole::oid)) THEN
   RAISE EXCEPTION 'PUBLIC/client/unreviewed table/column grant: %',t; END IF;
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
   FOR f IN SELECT oid,rolsuper,rolbypassrls FROM pg_catalog.pg_roles
    WHERE pg_catalog.pg_has_role(r,oid,'USAGE') OR pg_catalog.pg_has_role(r,oid,'SET') LOOP
    IF f.rolsuper OR f.rolbypassrls THEN RAISE EXCEPTION 'Privileged role bridge: %',r; END IF;
    FOREACH priv IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'] LOOP
     IF pg_catalog.has_table_privilege(f.oid,rel,priv) THEN RAISE EXCEPTION 'Effective table bridge: %.% %',r,t,priv; END IF;
    END LOOP;
    FOR c IN SELECT attnum FROM pg_catalog.pg_attribute WHERE attrelid=rel AND attnum>0 AND NOT attisdropped LOOP
     FOREACH priv IN ARRAY ARRAY['SELECT','INSERT','UPDATE','REFERENCES'] LOOP
      IF pg_catalog.has_column_privilege(f.oid,rel,c.attnum,priv) THEN RAISE EXCEPTION 'Effective column bridge: %.% %',r,t,priv; END IF;
     END LOOP;
    END LOOP;
   END LOOP;
  END LOOP;
  FOREACH priv IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE'] LOOP
   IF t='admin_audit_log' AND priv IN ('UPDATE','DELETE') OR t=ANY(ARRAY['departments','programs','courses','academic_years','semesters','program_courses','course_offerings','sections']::text[]) AND priv='DELETE' THEN CONTINUE; END IF;
   IF NOT pg_catalog.has_table_privilege('service_role',rel,priv) THEN RAISE EXCEPTION 'Service workflow grant missing: %.%',t,priv; END IF;
  END LOOP;
  IF t=ANY(ARRAY['departments','programs','courses','academic_years','semesters','program_courses','course_offerings','sections']::text[]) AND (pg_catalog.has_table_privilege('service_role',rel,'DELETE') OR pg_catalog.has_table_privilege('service_role',rel,'TRUNCATE')) THEN
   RAISE EXCEPTION 'Master destructive service grant: %',t; END IF;
 END LOOP;
 FOREACH priv IN ARRAY ARRAY['UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'] LOOP
  IF pg_catalog.has_table_privilege('service_role','public.admin_audit_log',priv) THEN RAISE EXCEPTION 'Audit destructive/utility service privilege: %',priv; END IF;
 END LOOP;
 FOR c IN SELECT attnum FROM pg_catalog.pg_attribute WHERE attrelid='public.admin_audit_log'::regclass AND attnum>0 AND NOT attisdropped LOOP
  IF pg_catalog.has_column_privilege('service_role','public.admin_audit_log'::regclass,c.attnum,'UPDATE') OR
     pg_catalog.has_column_privilege('service_role','public.admin_audit_log'::regclass,c.attnum,'REFERENCES') THEN RAISE EXCEPTION 'Audit column mutability'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM pg_catalog.pg_class cc,LATERAL pg_catalog.aclexplode(COALESCE(cc.relacl,pg_catalog.acldefault('r',cc.relowner))) a
  WHERE cc.oid='public.admin_audit_log'::regclass AND a.grantee='service_role'::regrole::oid AND a.is_grantable) OR
  EXISTS(SELECT 1 FROM pg_catalog.pg_attribute cc,LATERAL pg_catalog.aclexplode(cc.attacl) a
  WHERE cc.attrelid='public.admin_audit_log'::regclass AND cc.attnum>0 AND NOT cc.attisdropped
  AND a.grantee='service_role'::regrole::oid AND a.is_grantable) THEN RAISE EXCEPTION 'Audit service grant option'; END IF;
 FOR b IN SELECT * FROM (VALUES ('student_attendance','trg_student_attendance_tenant_guard','public.student_attendance_tenant_guard()',23),
      ('student_results','trg_student_results_tenant_guard','public.student_results_tenant_guard()',23),
      ('student_notifications','trg_student_notifications_tenant_guard','public.trg_student_notifications_tenant_guard()',23),
      ('institutions','trg_phase613_institutions_status','public.phase613_sync_institution_status()',23),
      ('user_roles','trg_phase613_user_roles_scope','public.phase613_assert_role_scope()',23),
      ('user_roles','trg_phase712_super_admin_scope','public.phase712_assert_super_admin_scope()',23),
      ('admin_audit_log','phase81_admin_audit_append_only','public.phase81_prevent_audit_mutation()',27),
      ('students','trg_reconcile_faculty_attendance_roster','public.reconcile_faculty_attendance_roster_student()',21),
      ('students','test_student_visibility','public.refresh_student_test_visibility()',17),
      ('departments','academic_master_validate','public.validate_academic_master_record()',23),
      ('programs','academic_master_validate','public.validate_academic_master_record()',23),
      ('courses','academic_master_validate','public.validate_academic_master_record()',23),
      ('academic_years','academic_master_validate','public.validate_academic_master_record()',23),
      ('semesters','academic_master_validate','public.validate_academic_master_record()',23),
      ('program_courses','academic_master_validate','public.validate_academic_master_record()',23),
      ('course_offerings','academic_master_validate','public.validate_academic_master_record()',23),
      ('sections','academic_master_validate','public.validate_academic_master_record()',23),
  ('admin_audit_log','security_containment_admin_audit_no_truncate','public.security_containment_prevent_audit_truncate()',34)) x(tbl,trg,signature,trigger_type) LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_trigger WHERE tgrelid=pg_catalog.to_regclass('public.'||b.tbl)
   AND tgname=b.trg AND tgenabled='O' AND tgtype=b.trigger_type AND NOT tgisinternal AND tgfoid=pg_catalog.to_regprocedure(b.signature)) THEN
   RAISE EXCEPTION 'Guard changed: %.%',b.tbl,b.trg; END IF;
 END LOOP;
 FOR f IN SELECT p.oid FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname=ANY(ARRAY['faculty_assignment_touch','faculty_attendance_context_guard','faculty_attendance_record_scope_guard','faculty_attendance_set_updated_at','faculty_responsibility_scope_guard','phase613_assert_child_organization','phase613_assert_role_scope','phase613_sync_institution_status','phase712_assert_super_admin_scope','phase714_assert_invitation_transition','phase715_assert_invitation_transition','phase717_cancel_terminal_invitation_email','phase717_claim_email_outbox','phase717_complete_email_outbox','phase717_create_invitation_with_outbox','phase717_resolve_email_outbox_context','phase717_rotate_invitation_with_outbox','phase718_reconcile_mailgun_event','phase81_prevent_audit_mutation','reconcile_faculty_attendance_roster_student','student_attendance_tenant_guard','student_results_tenant_guard','test_results_tenant_guard','trg_student_notifications_tenant_guard']::text[]) LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.unnest(ARRAY['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)','public.faculty_assignment_touch()','public.faculty_attendance_context_guard()','public.faculty_attendance_record_scope_guard()','public.faculty_attendance_set_updated_at()','public.faculty_responsibility_scope_guard()','public.phase613_assert_child_organization()','public.phase613_assert_role_scope()','public.phase613_sync_institution_status()','public.phase712_assert_super_admin_scope()','public.phase714_assert_invitation_transition()','public.phase715_assert_invitation_transition()','public.phase717_cancel_terminal_invitation_email()','public.phase81_prevent_audit_mutation()','public.reconcile_faculty_attendance_roster_student()','public.student_attendance_tenant_guard()','public.student_results_tenant_guard()','public.test_results_tenant_guard()','public.trg_student_notifications_tenant_guard()','public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)']::text[]) e(sig) WHERE f.oid=pg_catalog.to_regprocedure(e.sig)) THEN RAISE EXCEPTION 'Unexpected overload: %',f.oid::regprocedure; END IF;
 END LOOP;
 FOREACH sig IN ARRAY ARRAY['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)','public.faculty_assignment_touch()','public.faculty_attendance_context_guard()','public.faculty_attendance_record_scope_guard()','public.faculty_attendance_set_updated_at()','public.faculty_responsibility_scope_guard()','public.phase613_assert_child_organization()','public.phase613_assert_role_scope()','public.phase613_sync_institution_status()','public.phase712_assert_super_admin_scope()','public.phase714_assert_invitation_transition()','public.phase715_assert_invitation_transition()','public.phase717_cancel_terminal_invitation_email()','public.phase81_prevent_audit_mutation()','public.reconcile_faculty_attendance_roster_student()','public.student_attendance_tenant_guard()','public.student_results_tenant_guard()','public.test_results_tenant_guard()','public.trg_student_notifications_tenant_guard()','public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)']::text[] LOOP
  IF NOT pg_catalog.has_function_privilege('service_role',sig,'EXECUTE') THEN RAISE EXCEPTION 'Service helper/entry grant lost: %',sig; END IF;
 END LOOP;
 FOREACH sig IN ARRAY ARRAY['public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)','public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)','public.phase717_claim_email_outbox(integer,integer,integer)','public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)','public.phase717_resolve_email_outbox_context(uuid,text)','public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)','public.faculty_assignment_touch()','public.faculty_attendance_context_guard()','public.faculty_attendance_record_scope_guard()','public.faculty_attendance_set_updated_at()','public.faculty_responsibility_scope_guard()','public.phase613_assert_child_organization()','public.phase613_assert_role_scope()','public.phase613_sync_institution_status()','public.phase712_assert_super_admin_scope()','public.phase714_assert_invitation_transition()','public.phase715_assert_invitation_transition()','public.phase717_cancel_terminal_invitation_email()','public.phase81_prevent_audit_mutation()','public.reconcile_faculty_attendance_roster_student()','public.student_attendance_tenant_guard()','public.student_results_tenant_guard()','public.test_results_tenant_guard()','public.trg_student_notifications_tenant_guard()','public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)','public.security_containment_prevent_audit_truncate()','public.academic_master_tenant(text,uuid)','public.commit_faculty_attendance_import(uuid,uuid,uuid,timestamptz,jsonb)','public.commit_faculty_test_import(uuid,uuid,uuid,timestamptz,bigint)','public.consume_auth_password_recovery_session(text,uuid,timestamptz)','public.create_faculty_teaching_assignment(uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean)','public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb)','public.manage_faculty_responsibility(uuid,uuid,uuid,text,text,uuid,timestamptz,timestamptz,boolean,uuid,boolean,uuid)','public.manage_scoped_faculty_teaching_assignment(uuid,uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean,boolean)','public.mark_faculty_attendance(uuid,uuid,uuid,date,jsonb,text)','public.phase712_assign_super_admin(text,text)','public.phase712_revoke_super_admin(text,text)','public.phase723_approve_membership_and_grant_role(uuid,uuid,uuid,text)','public.phase723_approve_membership_with_invitation(uuid,uuid,uuid,text,text,timestamptz,text)','public.phase81_assert_institution_admin(uuid,uuid)','public.phase81_assign_institution_role_audited(uuid,uuid,uuid,text)','public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean)','public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)','public.review_faculty_attendance_import(uuid,uuid,uuid,jsonb,jsonb,timestamptz)','public.review_faculty_test_import(uuid,uuid,uuid,timestamptz,jsonb,jsonb)','public.save_faculty_test(uuid,uuid,uuid,jsonb,uuid,bigint)','public.save_faculty_test_marks(uuid,uuid,uuid,bigint,jsonb,text)','public.search_public_knowledge_chunks(extensions.vector,integer,uuid,uuid,text)','public.search_similar_chunks(extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text)','public.stage_faculty_attendance_import(uuid,uuid,uuid,uuid,text,text,text,boolean,jsonb,jsonb)','public.stage_faculty_test_import(uuid,uuid,uuid,text,text,jsonb,jsonb)','public.transition_faculty_test(uuid,uuid,uuid,bigint,text)','public.update_faculty_teaching_validity(uuid,uuid,uuid,timestamptz,timestamptz,boolean)','public.validate_academic_master_record()','public.phase81_manage_faculty_section_assignment_original(uuid,uuid,uuid,uuid,boolean)']::text[] LOOP
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_proc p,LATERAL pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
   WHERE p.oid=pg_catalog.to_regprocedure(sig) AND a.grantee=0 AND a.privilege_type='EXECUTE') THEN RAISE EXCEPTION 'PUBLIC function grant: %',sig; END IF;
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
   FOR f IN SELECT oid FROM pg_catalog.pg_roles WHERE pg_catalog.pg_has_role(r,oid,'USAGE') OR pg_catalog.pg_has_role(r,oid,'SET') LOOP
    IF pg_catalog.has_function_privilege(f.oid,pg_catalog.to_regprocedure(sig),'EXECUTE') THEN RAISE EXCEPTION 'Effective routine bridge: % %',r,sig; END IF;
   END LOOP;
  END LOOP;
 END LOOP;
 FOREACH sig IN ARRAY ARRAY['public.academic_master_tenant(text,uuid)','public.commit_faculty_attendance_import(uuid,uuid,uuid,timestamptz,jsonb)','public.commit_faculty_test_import(uuid,uuid,uuid,timestamptz,bigint)','public.consume_auth_password_recovery_session(text,uuid,timestamptz)','public.create_faculty_teaching_assignment(uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean)','public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb)','public.manage_faculty_responsibility(uuid,uuid,uuid,text,text,uuid,timestamptz,timestamptz,boolean,uuid,boolean,uuid)','public.manage_scoped_faculty_teaching_assignment(uuid,uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean,boolean)','public.mark_faculty_attendance(uuid,uuid,uuid,date,jsonb,text)','public.phase712_assign_super_admin(text,text)','public.phase712_revoke_super_admin(text,text)','public.phase723_approve_membership_and_grant_role(uuid,uuid,uuid,text)','public.phase723_approve_membership_with_invitation(uuid,uuid,uuid,text,text,timestamptz,text)','public.phase81_assert_institution_admin(uuid,uuid)','public.phase81_assign_institution_role_audited(uuid,uuid,uuid,text)','public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean)','public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)','public.review_faculty_attendance_import(uuid,uuid,uuid,jsonb,jsonb,timestamptz)','public.review_faculty_test_import(uuid,uuid,uuid,timestamptz,jsonb,jsonb)','public.save_faculty_test(uuid,uuid,uuid,jsonb,uuid,bigint)','public.save_faculty_test_marks(uuid,uuid,uuid,bigint,jsonb,text)','public.search_public_knowledge_chunks(extensions.vector,integer,uuid,uuid,text)','public.search_similar_chunks(extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text)','public.stage_faculty_attendance_import(uuid,uuid,uuid,uuid,text,text,text,boolean,jsonb,jsonb)','public.stage_faculty_test_import(uuid,uuid,uuid,text,text,jsonb,jsonb)','public.transition_faculty_test(uuid,uuid,uuid,bigint,text)','public.update_faculty_teaching_validity(uuid,uuid,uuid,timestamptz,timestamptz,boolean)','public.validate_academic_master_record()']::text[] LOOP
  IF NOT pg_catalog.has_function_privilege('service_role',sig,'EXECUTE') THEN RAISE EXCEPTION 'Preserved command grant missing: %',sig; END IF;
 END LOOP;
 IF pg_catalog.has_function_privilege('service_role','public.phase81_manage_faculty_section_assignment_original(uuid,uuid,uuid,uuid,boolean)','EXECUTE') THEN RAISE EXCEPTION 'Renamed original must remain private'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc WHERE oid='public.security_containment_prevent_audit_truncate()'::regprocedure AND proowner='postgres'::regrole::oid
  AND NOT prosecdef AND prorettype='pg_catalog.trigger'::regtype::oid AND 'search_path=""'=ANY(COALESCE(proconfig,ARRAY[]::text[]))) OR
  EXISTS(SELECT 1 FROM pg_catalog.pg_proc p,LATERAL pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
  WHERE p.oid='public.security_containment_prevent_audit_truncate()'::regprocedure AND a.grantee<>'postgres'::regrole::oid) OR
  pg_catalog.has_function_privilege('service_role','public.security_containment_prevent_audit_truncate()','EXECUTE') THEN RAISE EXCEPTION 'New helper must remain owner-only'; END IF;
 -- An absent global row means builtin PUBLIC EXECUTE; require the repaired global row.
 IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_default_acl WHERE defaclrole='postgres'::regrole::oid AND defaclnamespace=0 AND defaclobjtype='f') OR
  EXISTS(SELECT 1 FROM pg_catalog.pg_default_acl d,LATERAL pg_catalog.aclexplode(d.defaclacl) a
  WHERE d.defaclrole='postgres'::regrole::oid AND d.defaclobjtype='f' AND d.defaclnamespace IN (0,'public'::regnamespace::oid)
  AND a.privilege_type='EXECUTE' AND a.grantee IN (0,'anon'::regrole::oid,'authenticated'::regrole::oid)) THEN RAISE EXCEPTION 'Future PUBLIC/client function default remains'; END IF;
 -- B02 future public service default intentionally retained, not declared safe.
 -- External approved catalog/policy/body/view/RPC/claim comparison still required.
END $postflight$;

-- C051 | stage 8 | final review rollback
ROLLBACK;
