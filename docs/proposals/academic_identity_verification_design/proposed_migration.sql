-- DESIGN REVIEW ARTIFACT ONLY. NOT A MIGRATION TO APPLY.
-- No policies, mandates, accepted registers or assignments are seeded.
-- PostgreSQL syntax, security, concurrency and transaction behavior NOT validated.
-- REVIEW BLOCKERS (no implementation approval):
-- * Freshness, character/Unicode/collision rules and identifier reuse/reassignment
--   remain owner decisions. Approval-reference strings do not prove approval or
--   express the full policy. No fixture durations/rules are institution defaults.
-- * A trusted subject-to-user/Auth binding and independent review workflow is
--   absent. Positive commands additionally fail with
--   AV_SELF_APPROVAL_CONTROL_UNRESOLVED until that design is approved. A profile
--   user-id comparison alone cannot protect account-independent identities.
--   Normative invariant: rpc_contract.md "Exact subject-binding invariant".
--   Require an authenticated/proofed subject account and retained structured
--   evidence for the exact institution/person/source/entry/profile/user/Auth/
--   association revision; identifier agreement never overrides missing ownership.
--   No-accounts evidence cannot authorize any profile/account. Ordinary commands
--   cannot migrate any historical positive tuple, including NULL to account.
--   Current usability must recheck the exact recorded binding, evidence validity,
--   live directory/profile tuple and establishing/reviewing authority. Reapproval
--   or account recovery cannot silently refresh a positive; replay stays historical.
--   The oracle's evidence registry, method/mode policies, dedicated binding
--   mandates, directory revisions and approval records have NO SQL counterpart.
--   The current_policy reference checks and post-refusal body below do NOT
--   implement them. They require owner decisions and a reviewed writer/locking
--   design (all association writers participating, including change-and-return).
--   Keep BOTH unconditional refusals; no positive SQL path is enabled here.
-- * No-accounts receipts additionally require exact institution directory baseline
--   id/generation, explicit trusted completeness/history authority, consecutive
--   retained change snapshots/tombstones and a matching durable head/highwater.
--   Creation/removal/reassociation/recovery/replacement/inactivity and restoring
--   identical values must advance generation; never reset it when rows disappear.
--   Old absence evidence stays unusable after change-away-and-back or legacy-row
--   cleanup. Missing/unreliable directory continuity/authority fails closed.
--   A fresh receipt cannot authorize historically associated subjects pending an
--   owner-approved workflow. Explicit evidence revocation remains cumulative.
--   rpc_contract.md "Persistent no-accounts directory invariant" is normative.
--   DirectoryBaseline/DirectoryRevision, writer mandate, generation journal and
--   highwater exist ONLY as synthetic offline specifications, with NO SQL tables,
--   writer/resolver or owner-approved mechanism. External continuity/anti-rollback,
--   completeness coverage, all-writer coordination, retention and responsibility
--   for incidents/evidence invalidation/recovery remain approval blockers.
--   Require retained bootstrap receipts; latch observed continuity failures,
--   including untracked rows detected during reads. Row deletion or restored
--   checkpoints must not clear incidents. Durable read-side incident delivery is
--   unspecified; the oracle's security marker changes no decision/history/claims.
--   In-memory checks cannot prove durable history or detect coherent total rollback.
--   Independently require actual positive integer generations for the separate
--   head, journal, highwater, receipt and writer expectation; boolean/numeric
--   equality is not validation. A receipt cannot bless malformed directory state.
--   Ordinary restore must append history/advance generation, never rewind it.
--   Ordinary writer/bootstrap/cleanup cannot clear latched integrity incidents.
--   The offline total-state-restore test intentionally observes usable old proof
--   when EVERY trusted input (including audit/incident state) is rolled back.
--   This characterizes an undetectable trust boundary, NOT a durable protection.
--   External continuity authority/coverage, persistent tombstones/completeness,
--   backup/restore guarantees and authorized incident recovery remain unapproved.
--   No such external mechanism, SQL schema or PostgreSQL validation is supplied.
-- * Trusted custody writers must verify uploader mandate, original-byte hash,
--   institution-bound authenticity evidence and complete confirmed entries.
--   Nonempty evidence references/metadata CHECKs alone cannot establish trust.
-- * Owner bootstrap, restricted evidence/audit read APIs, custody/storage ACLs,
--   legal hold/deletion/backup/exceptional access and retention are not supplied.
-- * Historical reservation refuses reuse; it is a temporary fail-closed guard,
--   not an approved lifetime uniqueness or exceptional reassignment policy.
-- * Composite FKs/index/table locks and service-only SECURITY DEFINER boundaries
--   need independent review and later PostgreSQL validation, never assumed safe.
BEGIN;
DO $design_only$
BEGIN
    RAISE EXCEPTION 'DESIGN_ONLY_NOT_AUTHORIZED';
END;
$design_only$;
CREATE SCHEMA academic_verification;
REVOKE ALL ON SCHEMA academic_verification FROM PUBLIC,anon,authenticated,service_role;
INSERT INTO public.permissions(name,code,description,scope,is_active)
VALUES('academic_identity.verify','academic_identity.verify','Individually assigned register verification.','institution',true);

CREATE TABLE academic_verification.policies (
 policy_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
 policy_version integer NOT NULL CHECK(policy_version>0),
 required_kinds text[] NOT NULL DEFAULT ARRAY['official_person_key','register_number']::text[]
   CHECK(required_kinds=ARRAY['official_person_key','register_number']::text[]),
 identifier_rules jsonb NOT NULL CHECK(jsonb_typeof(identifier_rules)='object'),
 official_person_key_description text NOT NULL CHECK(length(btrim(official_person_key_description)) BETWEEN 1 AND 1000),
 freshness_mode text NOT NULL CHECK(freshness_mode IN ('bounded','no_expiry')),
 max_age interval,
 governance_approvals jsonb NOT NULL CHECK(jsonb_typeof(governance_approvals)='object'),
 owner_approval_reference text NOT NULL CHECK(length(btrim(owner_approval_reference)) BETWEEN 1 AND 1000),
 approved_by_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 approved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK((freshness_mode='bounded' AND max_age IS NOT NULL AND max_age>interval '0')
    OR (freshness_mode='no_expiry' AND max_age IS NULL)),
 UNIQUE(institution_id,policy_version), UNIQUE(policy_id,institution_id)
);
CREATE TABLE academic_verification.authority_mandates (
 mandate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
 user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 purpose text NOT NULL CHECK(purpose IN ('permission_grantor','register_custodian','register_uploader')),
 owner_approval_reference text NOT NULL CHECK(length(btrim(owner_approval_reference)) BETWEEN 1 AND 1000),
 approved_by_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 approved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 audit_id uuid NOT NULL UNIQUE REFERENCES public.admin_audit_log(audit_id) ON DELETE RESTRICT,
 UNIQUE(mandate_id,institution_id)
);
CREATE TABLE academic_verification.authority_revocations (
 mandate_id uuid PRIMARY KEY, institution_id uuid NOT NULL,
 reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 2000),
 owner_approval_reference text NOT NULL CHECK(btrim(owner_approval_reference)<>''),
 actor_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 revoked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 audit_id uuid NOT NULL UNIQUE REFERENCES public.admin_audit_log(audit_id) ON DELETE RESTRICT,
 FOREIGN KEY(mandate_id,institution_id) REFERENCES academic_verification.authority_mandates(mandate_id,institution_id) ON DELETE RESTRICT
);
CREATE TABLE academic_verification.permission_events (
 event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
 target_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 revision integer NOT NULL CHECK(revision>0),
 state text NOT NULL CHECK(state IN ('granted','revoked')),
 permission_code text NOT NULL DEFAULT 'academic_identity.verify' CHECK(permission_code='academic_identity.verify'),
 mandate_id uuid NOT NULL,
 actor_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 actor_auth_user_id uuid NOT NULL, target_role_snapshot text,
 reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 2000),
 recorded_at timestamptz NOT NULL,
 audit_id uuid NOT NULL UNIQUE REFERENCES public.admin_audit_log(audit_id) ON DELETE RESTRICT,
 CHECK(actor_user_id<>target_user_id), UNIQUE(institution_id,target_user_id,revision),
 FOREIGN KEY(mandate_id,institution_id) REFERENCES academic_verification.authority_mandates(mandate_id,institution_id) ON DELETE RESTRICT
);
CREATE TABLE academic_verification.register_versions (
 source_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
 source_reference text NOT NULL CHECK(length(btrim(source_reference)) BETWEEN 1 AND 1000),
 -- Issuer-supplied metadata when available; never invent a version/date/issuer.
 issuer_name text CHECK(issuer_name IS NULL OR length(btrim(issuer_name)) BETWEEN 1 AND 256),
 source_version text CHECK(source_version IS NULL OR length(btrim(source_version)) BETWEEN 1 AND 256),
 source_as_of date,
 missing_metadata_reason text CHECK(missing_metadata_reason IS NULL OR length(btrim(missing_metadata_reason)) BETWEEN 1 AND 2000),
 storage_bucket text NOT NULL CHECK(btrim(storage_bucket)<>''),
 storage_object_key text NOT NULL CHECK(btrim(storage_object_key)<>''),
 storage_version_id text NOT NULL CHECK(btrim(storage_version_id)<>''),
 sha256 text COLLATE "C" NOT NULL CHECK(sha256 ~ '^[0-9a-f]{64}$'),
 byte_length bigint NOT NULL CHECK(byte_length>0),
 uploaded_by_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 uploaded_by_auth_user_id uuid NOT NULL, uploaded_at timestamptz NOT NULL,
 uploader_mandate_id uuid NOT NULL,
 accepted_by_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 accepted_by_auth_user_id uuid NOT NULL, custodian_mandate_id uuid NOT NULL,
 authenticity_evidence_reference text NOT NULL CHECK(length(btrim(authenticity_evidence_reference)) BETWEEN 1 AND 2000),
 authenticity_method text NOT NULL CHECK(length(btrim(authenticity_method)) BETWEEN 1 AND 1000),
 provenance_description text NOT NULL CHECK(length(btrim(provenance_description)) BETWEEN 1 AND 2000),
 entry_import_evidence_reference text NOT NULL CHECK(length(btrim(entry_import_evidence_reference)) BETWEEN 1 AND 2000),
 accepted_entry_count integer NOT NULL CHECK(accepted_entry_count>0),
 accepted_at timestamptz NOT NULL,
 audit_id uuid NOT NULL UNIQUE REFERENCES public.admin_audit_log(audit_id) ON DELETE RESTRICT,
 CHECK(accepted_at>=uploaded_at), UNIQUE(source_version_id,institution_id),
 CHECK((issuer_name IS NOT NULL AND source_version IS NOT NULL AND source_as_of IS NOT NULL) OR missing_metadata_reason IS NOT NULL),
 UNIQUE(storage_bucket,storage_object_key,storage_version_id),
 FOREIGN KEY(custodian_mandate_id,institution_id) REFERENCES academic_verification.authority_mandates(mandate_id,institution_id) ON DELETE RESTRICT,
 FOREIGN KEY(uploader_mandate_id,institution_id) REFERENCES academic_verification.authority_mandates(mandate_id,institution_id) ON DELETE RESTRICT
);
CREATE TABLE academic_verification.register_entries (
 entry_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_version_id uuid NOT NULL, institution_id uuid NOT NULL,
 entry_locator text NOT NULL CHECK(length(btrim(entry_locator)) BETWEEN 1 AND 1000),
 raw_values jsonb NOT NULL CHECK(jsonb_typeof(raw_values)='object' AND raw_values ?& ARRAY['official_person_key','register_number']),
 import_confirmation_reference text NOT NULL CHECK(length(btrim(import_confirmation_reference)) BETWEEN 1 AND 2000),
 extraction_status text NOT NULL CHECK(extraction_status='confirmed_original_strings'),
 UNIQUE(source_version_id,entry_locator), UNIQUE(entry_id,source_version_id,institution_id),
 FOREIGN KEY(source_version_id,institution_id) REFERENCES academic_verification.register_versions(source_version_id,institution_id) ON DELETE RESTRICT
);
CREATE TABLE academic_verification.source_invalidations (
 source_version_id uuid PRIMARY KEY, institution_id uuid NOT NULL, custodian_mandate_id uuid NOT NULL,
 actor_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 actor_auth_user_id uuid NOT NULL, reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 2000),
 incident_evidence_reference text NOT NULL CHECK(length(btrim(incident_evidence_reference)) BETWEEN 1 AND 2000),
 invalidated_at timestamptz NOT NULL,
 audit_id uuid NOT NULL UNIQUE REFERENCES public.admin_audit_log(audit_id) ON DELETE RESTRICT,
 FOREIGN KEY(source_version_id,institution_id) REFERENCES academic_verification.register_versions(source_version_id,institution_id) ON DELETE RESTRICT,
 FOREIGN KEY(custodian_mandate_id,institution_id) REFERENCES academic_verification.authority_mandates(mandate_id,institution_id) ON DELETE RESTRICT
);
-- Source upload/acceptance/invalidation writers are NOT implemented application
-- features. Reviewed custody operations must check live user/Auth/tenant/mandate,
-- hash original bytes on the server, confirm ALL entries and append audit under
-- the institution lock. Owner policy/mandate operations use that lock as well.
-- Check uploader identity/Auth, active staff/admin institution scope and an exact
-- register_uploader mandate both on upload and at acceptance. Retain provenance
-- that binds the approved handoff/signature procedure to this institution/copy;
-- filename/reference/checksum alone is insufficient. NULL issuer metadata needs
-- an attested reason and may be unusable under a later approved freshness rule.
-- FK existence does not check mandate purpose, subject, revocation or policy.
-- No direct API/service-role writes, staging adoption or generic RAG ingestion.

ALTER TABLE public.students ADD CONSTRAINT av_students_id_institution_key UNIQUE(student_id,institution_id);
CREATE TABLE academic_verification.identities (
 identity_id uuid PRIMARY KEY,
 institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
 student_id uuid, head_revision integer NOT NULL DEFAULT 0 CHECK(head_revision>=0),
 created_by_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(identity_id,institution_id), UNIQUE(institution_id,student_id),
 FOREIGN KEY(student_id,institution_id) REFERENCES public.students(student_id,institution_id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE academic_verification.decisions (
 decision_id uuid PRIMARY KEY, identity_id uuid NOT NULL, institution_id uuid NOT NULL,
 revision integer NOT NULL CHECK(revision>0), supersedes_decision_id uuid,
 previous_revision integer GENERATED ALWAYS AS (CASE WHEN revision>1 THEN revision-1 ELSE NULL END) STORED,
 operation text NOT NULL CHECK(operation IN ('verify','reverify','correct','withdraw')),
 decision text NOT NULL CHECK(decision IN ('verified','withdrawn')),
 policy_id uuid NOT NULL, source_version_id uuid NOT NULL, entry_id uuid NOT NULL,
 verifier_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT, verifier_auth_user_id uuid NOT NULL,
 reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 2000),
 decided_at timestamptz NOT NULL, valid_until timestamptz,
 evidence jsonb NOT NULL CHECK(jsonb_typeof(evidence)='object'),
 canonical_values jsonb NOT NULL CHECK(jsonb_typeof(canonical_values)='object'),
 student_id_at_decision uuid,
 audit_id uuid NOT NULL UNIQUE REFERENCES public.admin_audit_log(audit_id) ON DELETE RESTRICT,
 CHECK((revision=1 AND supersedes_decision_id IS NULL AND operation='verify')
    OR (revision>1 AND supersedes_decision_id IS NOT NULL AND operation<>'verify')),
 CHECK((operation='withdraw' AND decision='withdrawn' AND valid_until IS NULL AND canonical_values='{}'::jsonb)
    OR (operation<>'withdraw' AND decision='verified' AND canonical_values ?& ARRAY['official_person_key','register_number'])),
 CHECK(valid_until IS NULL OR valid_until>decided_at),
 UNIQUE(identity_id,institution_id,revision), UNIQUE(decision_id,identity_id,institution_id,revision),
 FOREIGN KEY(identity_id,institution_id) REFERENCES academic_verification.identities(identity_id,institution_id) ON DELETE RESTRICT,
 FOREIGN KEY(policy_id,institution_id) REFERENCES academic_verification.policies(policy_id,institution_id) ON DELETE RESTRICT,
 FOREIGN KEY(entry_id,source_version_id,institution_id) REFERENCES academic_verification.register_entries(entry_id,source_version_id,institution_id) ON DELETE RESTRICT,
 FOREIGN KEY(student_id_at_decision,institution_id) REFERENCES public.students(student_id,institution_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 FOREIGN KEY(supersedes_decision_id,identity_id,institution_id,previous_revision) REFERENCES academic_verification.decisions(decision_id,identity_id,institution_id,revision) ON DELETE RESTRICT
);
ALTER TABLE academic_verification.identities ADD CONSTRAINT av_complete_head
 FOREIGN KEY(identity_id,institution_id,head_revision) REFERENCES academic_verification.decisions(identity_id,institution_id,revision) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE academic_verification.identifier_claims (
 institution_id uuid NOT NULL,
 identifier_kind text NOT NULL CHECK(identifier_kind IN ('official_person_key','register_number','university_roll_number')),
 canonical_value text COLLATE "C" NOT NULL CHECK(length(canonical_value) BETWEEN 1 AND 256),
 identity_id uuid NOT NULL, decision_id uuid NOT NULL, revision integer NOT NULL,
 PRIMARY KEY(institution_id,identifier_kind,canonical_value), UNIQUE(identity_id,identifier_kind),
 FOREIGN KEY(decision_id,identity_id,institution_id,revision) REFERENCES academic_verification.decisions(decision_id,identity_id,institution_id,revision) ON DELETE RESTRICT
);
CREATE TABLE academic_verification.candidate_findings (
 finding_id uuid PRIMARY KEY, institution_id uuid NOT NULL, source_version_id uuid NOT NULL, entry_id uuid,
 searched_locator text NOT NULL CHECK(length(btrim(searched_locator)) BETWEEN 1 AND 1000),
 candidate_student_id uuid, context_identity_id uuid,
 finding text NOT NULL CHECK(finding IN ('rejected_match','unresolved')),
 observed_values jsonb NOT NULL CHECK(jsonb_typeof(observed_values)='object'),
 reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 2000),
 verifier_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT, verifier_auth_user_id uuid NOT NULL,
 recorded_at timestamptz NOT NULL,
 audit_id uuid NOT NULL UNIQUE REFERENCES public.admin_audit_log(audit_id) ON DELETE RESTRICT,
 FOREIGN KEY(source_version_id,institution_id) REFERENCES academic_verification.register_versions(source_version_id,institution_id) ON DELETE RESTRICT,
 FOREIGN KEY(entry_id,source_version_id,institution_id) REFERENCES academic_verification.register_entries(entry_id,source_version_id,institution_id) ON DELETE RESTRICT,
 FOREIGN KEY(candidate_student_id,institution_id) REFERENCES public.students(student_id,institution_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 FOREIGN KEY(context_identity_id,institution_id) REFERENCES academic_verification.identities(identity_id,institution_id) ON DELETE RESTRICT
);
CREATE TABLE academic_verification.command_receipts (
 institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
 actor_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 command text NOT NULL CHECK(command IN ('permission','decision','finding')),
 request_id uuid NOT NULL, payload jsonb NOT NULL, result jsonb NOT NULL,
 PRIMARY KEY(institution_id,actor_user_id,command,request_id)
);
CREATE INDEX av_positive_history ON academic_verification.decisions(institution_id,identity_id) WHERE decision='verified';
CREATE INDEX av_canonical_history ON academic_verification.decisions USING gin(canonical_values jsonb_path_ops);
DO $guards$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY['policies','authority_mandates','authority_revocations','permission_events','register_versions','register_entries','source_invalidations','decisions','candidate_findings','command_receipts'] LOOP
  EXECUTE format('CREATE TRIGGER av_immutable BEFORE UPDATE OR DELETE ON academic_verification.%I FOR EACH ROW EXECUTE FUNCTION public.phase81_prevent_audit_mutation()',t);
 END LOOP;
 FOREACH t IN ARRAY ARRAY['policies','authority_mandates','authority_revocations','permission_events','register_versions','register_entries','source_invalidations','identities','decisions','identifier_claims','candidate_findings','command_receipts'] LOOP
  EXECUTE format('CREATE TRIGGER av_no_truncate BEFORE TRUNCATE ON academic_verification.%I FOR EACH STATEMENT EXECUTE FUNCTION public.phase81_prevent_audit_mutation()',t);
  EXECUTE format('ALTER TABLE academic_verification.%I ENABLE ROW LEVEL SECURITY',t);
 END LOOP;
END;
$guards$;
CREATE TRIGGER av_identity_no_delete BEFORE DELETE ON academic_verification.identities FOR EACH ROW EXECUTE FUNCTION public.phase81_prevent_audit_mutation();
CREATE FUNCTION academic_verification.guard_identity_update() RETURNS trigger LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
 IF NEW.identity_id IS DISTINCT FROM OLD.identity_id OR NEW.institution_id IS DISTINCT FROM OLD.institution_id
 OR NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id OR NEW.created_at IS DISTINCT FROM OLD.created_at
 OR (OLD.student_id IS NOT NULL AND NEW.student_id IS DISTINCT FROM OLD.student_id)
 OR NEW.head_revision<>OLD.head_revision+1 THEN RAISE EXCEPTION 'AV_IDENTITY_CHANGE_INVALID' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER av_identity_update BEFORE UPDATE ON academic_verification.identities FOR EACH ROW EXECUTE FUNCTION academic_verification.guard_identity_update();

CREATE FUNCTION academic_verification.normalize_identifier(p_value text,p_rule text)
RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path='' AS $$
DECLARE v text;
BEGIN
 IF p_value IS NULL OR p_rule IS NULL THEN RAISE EXCEPTION 'AV_POLICY_OR_IDENTIFIER_INVALID' USING ERRCODE='22023'; END IF;
 IF p_rule='exact' THEN v:=p_value;
 ELSIF p_rule IN ('ascii_trim','ascii_trim_upper') THEN
  v:=btrim(p_value,E' \t\r\n\f\013');
  IF p_rule='ascii_trim_upper' THEN v:=translate(v,'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'); END IF;
 ELSE RAISE EXCEPTION 'AV_POLICY_OR_IDENTIFIER_INVALID' USING ERRCODE='22023'; END IF;
 IF length(v) NOT BETWEEN 1 AND 256 OR length(btrim(v,E' \t\r\n\f\013'))=0 THEN RAISE EXCEPTION 'AV_POLICY_OR_IDENTIFIER_INVALID' USING ERRCODE='22023'; END IF;
 RETURN v;
END;
$$;
CREATE FUNCTION academic_verification.current_policy(p_tenant uuid,p_policy uuid)
RETURNS academic_verification.policies LANGUAGE plpgsql SET search_path='' AS $$
DECLARE v academic_verification.policies%ROWTYPE; k text; rule text;
BEGIN
 SELECT * INTO v FROM academic_verification.policies WHERE institution_id=p_tenant ORDER BY policy_version DESC LIMIT 1 FOR SHARE;
 IF NOT FOUND OR v.policy_id IS DISTINCT FROM p_policy THEN RAISE EXCEPTION 'AV_POLICY_UNCONFIGURED_OR_STALE' USING ERRCODE='22023'; END IF;
 IF NOT (v.identifier_rules ?& ARRAY['official_person_key','register_number','university_roll_number'])
 OR EXISTS(SELECT 1 FROM jsonb_object_keys(v.identifier_rules) x WHERE x NOT IN ('official_person_key','register_number','university_roll_number')) THEN RAISE EXCEPTION 'AV_POLICY_INVALID' USING ERRCODE='22023'; END IF;
 FOR k,rule IN SELECT key,value #>> '{}' FROM jsonb_each(v.identifier_rules) LOOP
  IF jsonb_typeof(v.identifier_rules->k)<>'string' THEN RAISE EXCEPTION 'AV_POLICY_INVALID' USING ERRCODE='22023'; END IF;
  PERFORM academic_verification.normalize_identifier('probe',rule);
 END LOOP;
 FOREACH k IN ARRAY ARRAY['normalization','freshness','identifier_reuse','authenticity','locator','retention','assignment','correction_review','source_change','legacy_missing_values','lock_budget'] LOOP
  IF jsonb_typeof(v.governance_approvals->k) IS DISTINCT FROM 'string'
  OR length(btrim(v.governance_approvals->>k)) NOT BETWEEN 1 AND 1000 THEN RAISE EXCEPTION 'AV_GOVERNANCE_UNDECIDED' USING ERRCODE='22023'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM academic_verification.policies WHERE institution_id=p_tenant AND
 (identifier_rules IS DISTINCT FROM v.identifier_rules OR official_person_key_description IS DISTINCT FROM v.official_person_key_description)) THEN RAISE EXCEPTION 'AV_POLICY_REQUIRES_COLLISION_REVIEW' USING ERRCODE='22023'; END IF;
 RETURN v;
END;
$$;
CREATE FUNCTION academic_verification.begin_command(p_tenant uuid,p_positive boolean)
RETURNS void LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
 IF coalesce(auth.role(),'')<>'service_role' THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
 IF current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'AV_ISOLATION_UNSUPPORTED' USING ERRCODE='25000'; END IF;
 IF p_tenant IS NULL THEN RAISE EXCEPTION 'AV_REQUEST_INVALID' USING ERRCODE='22023'; END IF;
 -- Draft ceiling, not final operational policy. Outer caller must set a statement
 -- and transaction deadline BEFORE calling; changing it inside cannot prove one.
 PERFORM set_config('lock_timeout','5s',true);
 PERFORM pg_advisory_xact_lock(hashtextextended('academic-verification:'||p_tenant::text,0));
 LOCK TABLE public.user_roles,public.roles IN SHARE MODE;
 IF p_positive THEN LOCK TABLE public.students,public.faculty_attendance_rosters IN SHARE MODE; END IF;
 PERFORM 1 FROM public.institutions WHERE institution_id=p_tenant AND is_active AND status='active' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
END;
$$;
CREATE FUNCTION academic_verification.assert_member(p_actor uuid,p_auth uuid,p_tenant uuid,p_roles text[])
RETURNS text LANGUAGE plpgsql SET search_path='' AS $$
DECLARE role_name text;
BEGIN
 IF p_actor IS NULL OR p_auth IS NULL THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
 PERFORM 1 FROM public.users WHERE id=p_actor AND auth_user_id=p_auth AND status='active' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
 IF (SELECT count(DISTINCT ur.scope_id) FROM public.user_roles ur JOIN public.roles r ON r.id=ur.role_id
 WHERE ur.user_id=p_actor AND r.is_active AND r.name IN ('staff','admin') AND ur.scope_type='institution')<>1 THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
 SELECT r.name INTO role_name FROM public.user_roles ur JOIN public.roles r ON r.id=ur.role_id
 JOIN public.institutions i ON i.institution_id=ur.scope_id
 WHERE ur.user_id=p_actor AND ur.scope_type='institution' AND ur.scope_id=p_tenant
 AND ur.scope_organization_id=i.organization_id AND r.is_active AND r.name=ANY(p_roles)
 ORDER BY r.name LIMIT 1 FOR SHARE OF ur,r;
 IF NOT FOUND THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
 RETURN role_name;
END;
$$;
CREATE FUNCTION academic_verification.assert_verifier(p_actor uuid,p_auth uuid,p_tenant uuid)
RETURNS void LANGUAGE plpgsql SET search_path='' AS $$
DECLARE state_now text;
BEGIN
 PERFORM academic_verification.assert_member(p_actor,p_auth,p_tenant,ARRAY['staff','admin']);
 PERFORM 1 FROM public.permissions WHERE code='academic_identity.verify' AND scope='institution' AND is_active FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
 SELECT state INTO state_now FROM academic_verification.permission_events
 WHERE institution_id=p_tenant AND target_user_id=p_actor ORDER BY revision DESC LIMIT 1 FOR SHARE;
 IF state_now IS DISTINCT FROM 'granted' THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
 -- No role_permissions, existing Staff direct grants or wildcard substitution.
END;
$$;
CREATE FUNCTION academic_verification.assert_mandate(p_actor uuid,p_tenant uuid,p_mandate uuid,p_purpose text)
RETURNS void LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
 PERFORM 1 FROM academic_verification.authority_mandates m
 WHERE m.mandate_id=p_mandate AND m.institution_id=p_tenant AND m.user_id=p_actor AND m.purpose=p_purpose
 AND NOT EXISTS(SELECT 1 FROM academic_verification.authority_revocations r WHERE r.mandate_id=m.mandate_id) FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
END;
$$;
CREATE FUNCTION academic_verification.replay(p_tenant uuid,p_actor uuid,p_command text,p_request uuid,p_payload jsonb)
RETURNS jsonb LANGUAGE plpgsql SET search_path='' AS $$
DECLARE v academic_verification.command_receipts%ROWTYPE; answer jsonb; head integer;
BEGIN
 IF p_request IS NULL THEN RAISE EXCEPTION 'AV_REQUEST_INVALID' USING ERRCODE='22023'; END IF;
 SELECT * INTO v FROM academic_verification.command_receipts WHERE institution_id=p_tenant AND actor_user_id=p_actor AND command=p_command AND request_id=p_request;
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF v.payload IS DISTINCT FROM p_payload THEN RAISE EXCEPTION 'AV_IDEMPOTENCY_CONFLICT' USING ERRCODE='22023'; END IF;
 answer:=v.result||jsonb_build_object('replayed',true);
 IF p_command='decision' THEN
  SELECT head_revision INTO head FROM academic_verification.identities WHERE identity_id=(answer->>'identity_id')::uuid AND institution_id=p_tenant FOR UPDATE;
  answer:=answer||jsonb_build_object('head_revision',head);
 ELSIF p_command='permission' THEN
  SELECT revision INTO head FROM academic_verification.permission_events WHERE institution_id=p_tenant AND target_user_id=(answer->>'target_user_id')::uuid ORDER BY revision DESC LIMIT 1;
  answer:=answer||jsonb_build_object('head_revision',head);
 END IF;
 RETURN answer;
END;
$$;
CREATE FUNCTION academic_verification.audit(p_actor uuid,p_tenant uuid,p_action text,p_table text,p_record uuid,p_data jsonb)
RETURNS uuid LANGUAGE plpgsql SET search_path='' AS $$
DECLARE v uuid:=gen_random_uuid();
BEGIN
 INSERT INTO public.admin_audit_log(audit_id,actor_user_id,institution_id,action,table_name,record_id,record_data,status,performed_at)
 VALUES(v,p_actor,p_tenant,p_action,p_table,p_record::text,p_data,'success',clock_timestamp());
 RETURN v;
END;
$$;

CREATE FUNCTION public.manage_academic_verifier_permission(
 p_actor_user_id uuid,p_actor_auth_user_id uuid,p_institution_id uuid,p_mandate_id uuid,
 p_target_user_id uuid,p_expected_revision integer,p_request_id uuid,p_grant boolean,p_reason text,p_policy_id uuid DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE prior academic_verification.permission_events%ROWTYPE; payload jsonb; answer jsonb; target_role text;
 target_auth uuid; event uuid:=gen_random_uuid(); audit_id uuid; rev integer;
BEGIN
 PERFORM academic_verification.begin_command(p_institution_id,false);
 PERFORM 1 FROM public.users WHERE id IN (p_actor_user_id,p_target_user_id) ORDER BY id FOR SHARE;
 PERFORM academic_verification.assert_member(p_actor_user_id,p_actor_auth_user_id,p_institution_id,ARRAY['admin']);
 PERFORM academic_verification.assert_mandate(p_actor_user_id,p_institution_id,p_mandate_id,'permission_grantor');
 IF p_target_user_id IS NULL OR p_target_user_id=p_actor_user_id THEN RAISE EXCEPTION 'AV_SELF_ASSIGNMENT_FORBIDDEN' USING ERRCODE='42501'; END IF;
 payload:=jsonb_build_object('target',p_target_user_id,'expected',p_expected_revision,'grant',p_grant,'reason',p_reason,'mandate',p_mandate_id,'policy',p_policy_id);
 answer:=academic_verification.replay(p_institution_id,p_actor_user_id,'permission',p_request_id,payload);
 IF answer IS NOT NULL THEN RETURN answer; END IF;
 IF p_expected_revision IS NULL OR p_expected_revision<0 OR p_grant IS NULL OR p_reason IS NULL OR length(btrim(p_reason)) NOT BETWEEN 1 AND 2000 THEN RAISE EXCEPTION 'AV_REQUEST_INVALID' USING ERRCODE='22023'; END IF;
 SELECT * INTO prior FROM academic_verification.permission_events WHERE institution_id=p_institution_id AND target_user_id=p_target_user_id ORDER BY revision DESC LIMIT 1 FOR SHARE;
 IF coalesce(prior.revision,0)<>p_expected_revision THEN RAISE EXCEPTION 'AV_PERMISSION_REVISION_CONFLICT' USING ERRCODE='40001'; END IF;
 IF p_grant THEN
  PERFORM academic_verification.current_policy(p_institution_id,p_policy_id);
  PERFORM 1 FROM public.permissions WHERE code='academic_identity.verify' AND scope='institution' AND is_active FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'AV_FORBIDDEN' USING ERRCODE='42501'; END IF;
  SELECT auth_user_id INTO target_auth FROM public.users WHERE id=p_target_user_id;
  target_role:=academic_verification.assert_member(p_target_user_id,target_auth,p_institution_id,ARRAY['staff','admin']);
  IF prior.state='granted' THEN RAISE EXCEPTION 'AV_ALREADY_GRANTED' USING ERRCODE='23514'; END IF;
 ELSIF prior.state IS DISTINCT FROM 'granted' THEN RAISE EXCEPTION 'AV_NOT_GRANTED' USING ERRCODE='23514'; END IF;
 -- Revocation requires neither current policy nor active target membership.
 rev:=p_expected_revision+1;
 audit_id:=academic_verification.audit(p_actor_user_id,p_institution_id,
 'academic_identity.permission.'||CASE WHEN p_grant THEN 'grant' ELSE 'revoke' END,
 'academic_verification.permission_events',event,jsonb_build_object('target_user_id',p_target_user_id,'revision',rev,'mandate_id',p_mandate_id));
 INSERT INTO academic_verification.permission_events(event_id,institution_id,target_user_id,revision,state,mandate_id,actor_user_id,actor_auth_user_id,target_role_snapshot,reason,recorded_at,audit_id)
 VALUES(event,p_institution_id,p_target_user_id,rev,CASE WHEN p_grant THEN 'granted' ELSE 'revoked' END,p_mandate_id,p_actor_user_id,p_actor_auth_user_id,target_role,p_reason,clock_timestamp(),audit_id);
 answer:=jsonb_build_object('event_id',event,'target_user_id',p_target_user_id,'recorded_revision',rev,'head_revision',rev,'replayed',false);
 INSERT INTO academic_verification.command_receipts VALUES(p_institution_id,p_actor_user_id,'permission',p_request_id,payload,answer);
 RETURN answer;
END;
$$;

CREATE FUNCTION public.record_academic_identity_verification(
 p_actor_user_id uuid,p_actor_auth_user_id uuid,p_institution_id uuid,p_identity_id uuid,
 p_expected_revision integer,p_request_id uuid,p_operation text,p_reason text,
 p_policy_id uuid DEFAULT NULL,p_source_version_id uuid DEFAULT NULL,p_entry_id uuid DEFAULT NULL,p_student_id uuid DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE ident academic_verification.identities%ROWTYPE; prior academic_verification.decisions%ROWTYPE;
 policy academic_verification.policies%ROWTYPE; src academic_verification.register_versions%ROWTYPE;
 entry academic_verification.register_entries%ROWTYPE; other_entry academic_verification.register_entries%ROWTYPE;
 student public.students%ROWTYPE; roster public.faculty_attendance_rosters%ROWTYPE;
 values_now jsonb:='{}'::jsonb; evidence_now jsonb; payload jsonb; answer jsonb;
 observed_students jsonb:='[]'::jsonb; observed_rosters jsonb:='[]'::jsonb;
 k text; raw jsonb; canon text; legacy text; matches uuid[]:=ARRAY[]::uuid[];
 target uuid; has_match boolean; bad boolean; now_db timestamptz; until_db timestamptz;
 new_decision_id uuid:=gen_random_uuid(); new_audit_id uuid; rev integer; effective_policy uuid; effective_source uuid; effective_entry uuid;
BEGIN
 PERFORM academic_verification.begin_command(p_institution_id,p_operation IN ('verify','reverify','correct'));
 PERFORM academic_verification.assert_verifier(p_actor_user_id,p_actor_auth_user_id,p_institution_id);
 payload:=jsonb_build_object('identity',p_identity_id,'expected',p_expected_revision,'operation',p_operation,'reason',p_reason,
 'policy',p_policy_id,'source',p_source_version_id,'entry',p_entry_id,'student',p_student_id);
 answer:=academic_verification.replay(p_institution_id,p_actor_user_id,'decision',p_request_id,payload);
 IF answer IS NOT NULL THEN RETURN answer; END IF;
 IF p_identity_id IS NULL OR p_expected_revision IS NULL OR p_expected_revision<0 OR p_operation IS NULL
 OR p_operation NOT IN ('verify','reverify','correct','withdraw') OR p_reason IS NULL OR length(btrim(p_reason)) NOT BETWEEN 1 AND 2000 THEN RAISE EXCEPTION 'AV_REQUEST_INVALID' USING ERRCODE='22023'; END IF;
 SELECT * INTO ident FROM academic_verification.identities WHERE identity_id=p_identity_id AND institution_id=p_institution_id FOR UPDATE;
 IF NOT FOUND THEN
  IF p_expected_revision<>0 OR p_operation<>'verify' OR EXISTS(SELECT 1 FROM academic_verification.identities WHERE identity_id=p_identity_id) THEN RAISE EXCEPTION 'AV_RESOURCE_OR_REVISION_CONFLICT' USING ERRCODE='40001'; END IF;
 ELSIF ident.head_revision<>p_expected_revision OR p_operation='verify' THEN RAISE EXCEPTION 'AV_RESOURCE_OR_REVISION_CONFLICT' USING ERRCODE='40001'; END IF;
 SELECT * INTO prior FROM academic_verification.decisions WHERE identity_id=p_identity_id AND institution_id=p_institution_id AND revision=ident.head_revision;
 target:=ident.student_id;
 IF p_operation='withdraw' THEN
  IF prior.decision IS DISTINCT FROM 'verified' THEN RAISE EXCEPTION 'AV_NOT_CURRENTLY_POSITIVE' USING ERRCODE='23514'; END IF;
  IF p_policy_id IS NOT NULL OR p_source_version_id IS NOT NULL OR p_entry_id IS NOT NULL OR p_student_id IS NOT NULL THEN RAISE EXCEPTION 'AV_WITHDRAWAL_INPUT_INVALID' USING ERRCODE='22023'; END IF;
  effective_policy:=prior.policy_id; effective_source:=prior.source_version_id; effective_entry:=prior.entry_id;
  evidence_now:=jsonb_build_object('withdraws_decision_id',prior.decision_id,'prior_evidence',prior.evidence);
  -- No newest policy, usable source or fresh register assertion required.
 ELSE
  -- Fail closed: no trusted independent subject-binding control is implemented.
  -- Required future check: actor user AND Auth must differ from subject accounts
  -- and independent binding reviewer; preserve checked evidence with the decision.
  -- Never accept a caller boolean/empty account list as proof of independence.
  -- The body below is an unreachable earlier matching sketch, not the corrected
  -- binding control. Before any future enablement it must implement the exact
  -- tuple/evidence/authority invariant, forbid NULL-to-account reassociation and
  -- recheck pinned evidence/association revisions atomically after lock waits.
  -- No schema/writer for those controls is supplied by this proposal revision.
  RAISE EXCEPTION 'AV_SELF_APPROVAL_CONTROL_UNRESOLVED' USING ERRCODE='42501';
  policy:=academic_verification.current_policy(p_institution_id,p_policy_id);
  SELECT * INTO src FROM academic_verification.register_versions WHERE source_version_id=p_source_version_id AND institution_id=p_institution_id FOR SHARE;
  IF NOT FOUND OR EXISTS(SELECT 1 FROM academic_verification.source_invalidations WHERE source_version_id=p_source_version_id) THEN RAISE EXCEPTION 'AV_SOURCE_UNAVAILABLE' USING ERRCODE='23514'; END IF;
  IF src.accepted_entry_count<>(SELECT count(*) FROM academic_verification.register_entries WHERE source_version_id=p_source_version_id) THEN RAISE EXCEPTION 'AV_SOURCE_INCOMPLETE' USING ERRCODE='23514'; END IF;
  SELECT * INTO entry FROM academic_verification.register_entries WHERE entry_id=p_entry_id AND source_version_id=p_source_version_id AND institution_id=p_institution_id FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'AV_ENTRY_INVALID' USING ERRCODE='22023'; END IF;
  IF entry.extraction_status IS DISTINCT FROM 'confirmed_original_strings' THEN RAISE EXCEPTION 'AV_AMBIGUOUS_EXTRACTION' USING ERRCODE='22023'; END IF;
  FOR k,raw IN SELECT key,value FROM jsonb_each(entry.raw_values) LOOP
   IF k NOT IN ('official_person_key','register_number','university_roll_number') OR jsonb_typeof(raw)<>'string' THEN RAISE EXCEPTION 'AV_SOURCE_ENTRY_INVALID' USING ERRCODE='22023'; END IF;
   canon:=academic_verification.normalize_identifier(raw #>> '{}',policy.identifier_rules->>k);
   values_now:=values_now||jsonb_build_object(k,canon);
  END LOOP;
  IF NOT (values_now ?& ARRAY['official_person_key','register_number']) THEN RAISE EXCEPTION 'AV_REGISTER_NUMBER_REQUIRED' USING ERRCODE='22023'; END IF;
  -- Trusted acceptance must validate the WHOLE register. Independently refuse
  -- another entry with ANY overlapping official key, never choose the first.
  FOR other_entry IN SELECT * FROM academic_verification.register_entries WHERE source_version_id=p_source_version_id AND entry_id<>p_entry_id LOOP
   IF NOT (other_entry.raw_values ?& ARRAY['official_person_key','register_number']) THEN RAISE EXCEPTION 'AV_SOURCE_ENTRY_INVALID' USING ERRCODE='22023'; END IF;
   FOR k,raw IN SELECT key,value FROM jsonb_each(other_entry.raw_values) LOOP
    IF k NOT IN ('official_person_key','register_number','university_roll_number') OR jsonb_typeof(raw)<>'string' THEN RAISE EXCEPTION 'AV_SOURCE_ENTRY_INVALID' USING ERRCODE='22023'; END IF;
    canon:=academic_verification.normalize_identifier(raw #>> '{}',policy.identifier_rules->>k);
    IF values_now->>k=canon COLLATE "C" THEN RAISE EXCEPTION 'AV_AMBIGUOUS_REGISTER_ENTRY' USING ERRCODE='23514'; END IF;
   END LOOP;
  END LOOP;
  IF EXISTS(SELECT 1 FROM academic_verification.decisions d WHERE d.identity_id=p_identity_id AND d.institution_id=p_institution_id AND d.decision='verified'
  AND d.canonical_values->>'official_person_key' IS DISTINCT FROM values_now->>'official_person_key') THEN RAISE EXCEPTION 'AV_REASSOCIATION_REQUIRES_REVIEW' USING ERRCODE='23514'; END IF;
  IF p_operation='reverify' AND (prior.decision IS DISTINCT FROM 'verified' OR prior.canonical_values IS DISTINCT FROM values_now
  OR (p_student_id IS NOT NULL AND p_student_id IS DISTINCT FROM target)) THEN RAISE EXCEPTION 'AV_CORRECTION_REQUIRED' USING ERRCODE='23514'; END IF;
  IF target IS NOT NULL AND p_student_id IS NOT NULL AND target<>p_student_id THEN RAISE EXCEPTION 'AV_REASSOCIATION_REQUIRES_REVIEW' USING ERRCODE='23514'; END IF;
  target:=coalesce(target,p_student_id);
  FOR k,canon IN SELECT key,value #>> '{}' FROM jsonb_each(values_now) LOOP
   IF EXISTS(SELECT 1 FROM academic_verification.identifier_claims c WHERE c.institution_id=p_institution_id AND c.identifier_kind=k AND c.canonical_value=canon COLLATE "C" AND c.identity_id<>p_identity_id)
   OR EXISTS(SELECT 1 FROM academic_verification.decisions d WHERE d.institution_id=p_institution_id AND d.identity_id<>p_identity_id AND d.decision='verified' AND d.canonical_values @> jsonb_build_object(k,canon)) THEN RAISE EXCEPTION 'AV_IDENTITY_CONFLICT' USING ERRCODE='23514'; END IF;
  END LOOP;
  -- Compare every available relevant field, not a client-selected subset.
  -- student_number deliberately excluded: it can be a roll-derived alias.
  FOR student IN SELECT * FROM public.students WHERE institution_id=p_institution_id LOOP
   has_match:=false; bad:=false;
   FOREACH k IN ARRAY ARRAY['register_number','university_roll_number'] LOOP
    legacy:=to_jsonb(student)->>k;
    IF legacy IS NOT NULL AND length(btrim(legacy,E' \t\r\n\f\013'))>0 THEN
     legacy:=academic_verification.normalize_identifier(legacy,policy.identifier_rules->>k);
     IF NOT (values_now ? k) THEN bad:=true;
     ELSIF legacy=values_now->>k COLLATE "C" THEN has_match:=true; ELSE bad:=true; END IF;
    END IF;
   END LOOP;
   IF has_match THEN
    IF bad OR student.register_number IS NULL OR length(btrim(student.register_number,E' \t\r\n\f\013'))=0
    OR academic_verification.normalize_identifier(student.register_number,policy.identifier_rules->>'register_number') IS DISTINCT FROM values_now->>'register_number' THEN RAISE EXCEPTION 'AV_IDENTITY_CONFLICT' USING ERRCODE='23514'; END IF;
    matches:=array_append(matches,student.student_id);
    observed_students:=observed_students||jsonb_build_array(jsonb_build_object(
      'student_id',student.student_id,'register_number',student.register_number,
      'university_roll_number',student.university_roll_number));
   END IF;
  END LOOP;
  IF cardinality(matches)>1 OR (target IS NOT NULL AND NOT (target=ANY(matches)))
  OR (cardinality(matches)=1 AND target IS DISTINCT FROM matches[1]) THEN RAISE EXCEPTION 'AV_LINK_OR_IDENTITY_CONFLICT' USING ERRCODE='23514'; END IF;
  FOR roster IN SELECT * FROM public.faculty_attendance_rosters WHERE institution_id=p_institution_id LOOP
   has_match:=false; bad:=false;
   FOREACH k IN ARRAY ARRAY['register_number','university_roll_number'] LOOP
    legacy:=to_jsonb(roster)->>k;
    IF legacy IS NOT NULL AND length(btrim(legacy,E' \t\r\n\f\013'))>0 THEN
     legacy:=academic_verification.normalize_identifier(legacy,policy.identifier_rules->>k);
     IF NOT (values_now ? k) THEN bad:=true;
     ELSIF legacy=values_now->>k COLLATE "C" THEN has_match:=true; ELSE bad:=true; END IF;
    END IF;
   END LOOP;
   IF has_match AND (bad OR academic_verification.normalize_identifier(roster.register_number,policy.identifier_rules->>'register_number') IS DISTINCT FROM values_now->>'register_number'
   OR (roster.linked_student_id IS NOT NULL AND roster.linked_student_id IS DISTINCT FROM target)) THEN RAISE EXCEPTION 'AV_LINK_OR_IDENTITY_CONFLICT' USING ERRCODE='23514'; END IF;
   IF has_match THEN
    observed_rosters:=observed_rosters||jsonb_build_array(jsonb_build_object(
      'roster_id',roster.roster_id,'section_id',roster.section_id,'register_number',roster.register_number,
      'university_roll_number',roster.university_roll_number,'linked_student_id',roster.linked_student_id));
   END IF;
  END LOOP;
  effective_policy:=policy.policy_id; effective_source:=src.source_version_id; effective_entry:=entry.entry_id;
  evidence_now:=jsonb_build_object('source_manifest',to_jsonb(src),'entry_locator',entry.entry_locator,
  'raw_values',entry.raw_values,'checked_identifiers',(SELECT jsonb_agg(key ORDER BY key) FROM jsonb_object_keys(entry.raw_values) key),
  'student_id',target,'observed_students',observed_students,'observed_rosters',observed_rosters,
  'comparison','all_available_register_and_roll_values; no legacy writes');
 END IF;
 evidence_now:=evidence_now||jsonb_build_object('verifier_permission_event',
  (SELECT to_jsonb(pe) FROM academic_verification.permission_events pe
   WHERE pe.institution_id=p_institution_id AND pe.target_user_id=p_actor_user_id
   ORDER BY pe.revision DESC LIMIT 1));
 now_db:=clock_timestamp();
 until_db:=CASE WHEN p_operation<>'withdraw' AND policy.freshness_mode='bounded' THEN now_db+policy.max_age ELSE NULL END;
 rev:=p_expected_revision+1;
 IF ident.identity_id IS NULL THEN INSERT INTO academic_verification.identities(identity_id,institution_id,created_by_user_id) VALUES(p_identity_id,p_institution_id,p_actor_user_id); END IF;
 new_audit_id:=academic_verification.audit(p_actor_user_id,p_institution_id,'academic_identity.'||p_operation,'academic_verification.identities',p_identity_id,
 jsonb_build_object('decision_id',new_decision_id,'revision',rev,'source_version_id',effective_source,'entry_id',effective_entry,'prior_decision',prior.decision_id));
 INSERT INTO academic_verification.decisions(decision_id,identity_id,institution_id,revision,supersedes_decision_id,operation,decision,policy_id,source_version_id,entry_id,
 verifier_user_id,verifier_auth_user_id,reason,decided_at,valid_until,evidence,canonical_values,student_id_at_decision,audit_id)
 VALUES(new_decision_id,p_identity_id,p_institution_id,rev,prior.decision_id,p_operation,CASE WHEN p_operation='withdraw' THEN 'withdrawn' ELSE 'verified' END,
 effective_policy,effective_source,effective_entry,p_actor_user_id,p_actor_auth_user_id,p_reason,now_db,until_db,evidence_now,values_now,target,new_audit_id);
 DELETE FROM academic_verification.identifier_claims WHERE identity_id=p_identity_id AND institution_id=p_institution_id;
 IF p_operation<>'withdraw' THEN
  INSERT INTO academic_verification.identifier_claims SELECT p_institution_id,key,value #>> '{}',p_identity_id,new_decision_id,rev FROM jsonb_each(values_now);
 END IF;
 UPDATE academic_verification.identities SET head_revision=rev,student_id=target WHERE identity_id=p_identity_id AND institution_id=p_institution_id;
 answer:=jsonb_build_object('identity_id',p_identity_id,'decision_id',new_decision_id,'recorded_revision',rev,'recorded_decision',CASE WHEN p_operation='withdraw' THEN 'withdrawn' ELSE 'verified' END,'head_revision',rev,'replayed',false);
 INSERT INTO academic_verification.command_receipts VALUES(p_institution_id,p_actor_user_id,'decision',p_request_id,payload,answer);
 RETURN answer;
END;
$$;

CREATE FUNCTION public.record_academic_candidate_finding(
 p_actor_user_id uuid,p_actor_auth_user_id uuid,p_institution_id uuid,p_request_id uuid,
 p_source_version_id uuid,p_searched_locator text,p_finding text,p_observed_values jsonb,p_reason text,
 p_entry_id uuid DEFAULT NULL,p_candidate_student_id uuid DEFAULT NULL,p_context_identity_id uuid DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE payload jsonb; answer jsonb; new_finding uuid:=gen_random_uuid(); new_audit uuid; k text; v jsonb;
BEGIN
 PERFORM academic_verification.begin_command(p_institution_id,false);
 PERFORM academic_verification.assert_verifier(p_actor_user_id,p_actor_auth_user_id,p_institution_id);
 payload:=jsonb_build_object('source',p_source_version_id,'locator',p_searched_locator,'finding',p_finding,'observed',p_observed_values,'reason',p_reason,'entry',p_entry_id,'student',p_candidate_student_id,'identity',p_context_identity_id);
 answer:=academic_verification.replay(p_institution_id,p_actor_user_id,'finding',p_request_id,payload);
 IF answer IS NOT NULL THEN RETURN answer; END IF;
 IF p_finding IS NULL OR p_finding NOT IN ('rejected_match','unresolved') OR p_reason IS NULL OR length(btrim(p_reason)) NOT BETWEEN 1 AND 2000
 OR p_searched_locator IS NULL OR length(btrim(p_searched_locator)) NOT BETWEEN 1 AND 1000
 OR p_observed_values IS NULL OR jsonb_typeof(p_observed_values)<>'object' OR pg_column_size(p_observed_values)>16384 THEN RAISE EXCEPTION 'AV_FINDING_INVALID' USING ERRCODE='22023'; END IF;
 FOR k,v IN SELECT key,value FROM jsonb_each(p_observed_values) LOOP
  IF k NOT IN ('register_number','university_roll_number') OR jsonb_typeof(v)<>'string' OR length(v #>> '{}') NOT BETWEEN 1 AND 256 THEN RAISE EXCEPTION 'AV_FINDING_INVALID' USING ERRCODE='22023'; END IF;
 END LOOP;
 PERFORM 1 FROM academic_verification.register_versions WHERE source_version_id=p_source_version_id AND institution_id=p_institution_id
 AND NOT EXISTS(SELECT 1 FROM academic_verification.source_invalidations WHERE source_version_id=p_source_version_id) FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'AV_SOURCE_UNAVAILABLE' USING ERRCODE='23514'; END IF;
 IF p_entry_id IS NOT NULL THEN
  PERFORM 1 FROM academic_verification.register_entries WHERE entry_id=p_entry_id AND source_version_id=p_source_version_id AND institution_id=p_institution_id AND entry_locator=p_searched_locator FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'AV_ENTRY_INVALID' USING ERRCODE='22023'; END IF;
 END IF;
 -- Composite FKs enforce same-tenant candidate/context references.
 -- Candidate observation is attestation, not ownership or an identity-head write.
 new_audit:=academic_verification.audit(p_actor_user_id,p_institution_id,'academic_identity.candidate.'||p_finding,'academic_verification.candidate_findings',new_finding,jsonb_build_object('source_version_id',p_source_version_id));
 INSERT INTO academic_verification.candidate_findings VALUES(new_finding,p_institution_id,p_source_version_id,p_entry_id,p_searched_locator,p_candidate_student_id,p_context_identity_id,p_finding,p_observed_values,p_reason,p_actor_user_id,p_actor_auth_user_id,clock_timestamp(),new_audit);
 answer:=jsonb_build_object('finding_id',new_finding,'finding',p_finding,'replayed',false);
 INSERT INTO academic_verification.command_receipts VALUES(p_institution_id,p_actor_user_id,'finding',p_request_id,payload,answer);
 RETURN answer;
END;
$$;
-- Trusted migration owner only; review ownership/default/inherited privileges.
-- RLS has no client policies and is not FORCE for the trusted definer owner.
REVOKE ALL ON ALL TABLES IN SCHEMA academic_verification FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA academic_verification FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.manage_academic_verifier_permission(uuid,uuid,uuid,uuid,uuid,integer,uuid,boolean,text,uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.record_academic_identity_verification(uuid,uuid,uuid,uuid,integer,uuid,text,text,uuid,uuid,uuid,uuid) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.record_academic_candidate_finding(uuid,uuid,uuid,uuid,uuid,text,text,jsonb,text,uuid,uuid,uuid) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.manage_academic_verifier_permission(uuid,uuid,uuid,uuid,uuid,integer,uuid,boolean,text,uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.record_academic_identity_verification(uuid,uuid,uuid,uuid,integer,uuid,text,text,uuid,uuid,uuid,uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.record_academic_candidate_finding(uuid,uuid,uuid,uuid,uuid,text,text,jsonb,text,uuid,uuid,uuid) TO service_role;
-- No source/mandate/policy management RPC or current-eligibility/read API.
-- Future current-state projections MUST join current positive head, source not
-- invalidated, complete policy/freshness and freshly rechecked legacy relations.
-- No role/account/approval/email/attendance/roster writes or invitation commands.
COMMIT;

