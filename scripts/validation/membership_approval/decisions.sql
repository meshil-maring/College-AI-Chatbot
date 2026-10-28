SET request.jwt.claim.role = 'service_role';
CREATE SCHEMA membership_fixture;
CREATE TABLE membership_fixture.ids(name text PRIMARY KEY, value uuid NOT NULL);
CREATE FUNCTION membership_fixture.id(key text) RETURNS uuid LANGUAGE sql STABLE
AS $$ SELECT value FROM membership_fixture.ids WHERE name = key $$;
DO $$
DECLARE org uuid; tenant uuid; actor uuid; auth_id uuid; applicant uuid; req uuid; label text; item jsonb;
    before_decision timestamptz; audit_total bigint;
BEGIN
    SELECT organization_id INTO STRICT org FROM public.organizations
    WHERE organization_code = 'COLLEGE-AI-PLATFORM';
    tenant := gen_random_uuid(); actor := gen_random_uuid(); auth_id := gen_random_uuid();
    INSERT INTO public.institutions(institution_id, organization_id, name, code, status)
    VALUES(tenant, org, 'Fictional Approval Institute', 'APPROVAL-TEST', 'active');
    INSERT INTO auth.users(id, email) VALUES(auth_id, 'approval-admin@example.invalid');
    INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
    VALUES(actor, auth_id, 'approval-admin@example.invalid', 'Approval', 'Admin');
    INSERT INTO public.user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
    SELECT actor, id, 'institution', tenant, org FROM public.roles WHERE name = 'admin';
    INSERT INTO membership_fixture.ids VALUES('admin', actor), ('tenant', tenant), ('organization', org);

    FOREACH label IN ARRAY ARRAY['staff', 'faculty', 'rejected', 'audit_failure', 'cross_scope'] LOOP
        applicant := gen_random_uuid(); auth_id := gen_random_uuid(); req := gen_random_uuid();
        INSERT INTO auth.users(id, email) VALUES(auth_id, label || '@example.invalid');
        INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
        VALUES(applicant, auth_id, label || '@example.invalid', 'Approval', label);
        INSERT INTO public.institution_membership_requests
            (request_id, user_id, institution_id, organization_id, requested_role, official_email, full_name)
        VALUES(req, applicant, tenant, org, CASE WHEN label = 'faculty' THEN 'faculty' ELSE 'staff' END,
            label || '@example.invalid', 'Approval Applicant');
        INSERT INTO membership_fixture.ids VALUES(label, req), (label || '_user', applicant);
        IF label NOT IN ('staff', 'faculty') THEN CONTINUE; END IF;
        item := public.phase723_approve_membership_and_grant_role(req, tenant, actor, 'reviewed');
        IF item IS DISTINCT FROM jsonb_build_object('already_applied', false, 'role_granted', true, 'audit_persisted', true) THEN
            RAISE EXCEPTION 'Initial approval contract failed: %', item;
        END IF;
        SELECT decided_at INTO before_decision FROM public.institution_membership_requests WHERE request_id = req;
        item := public.phase723_approve_membership_and_grant_role(req, tenant, actor, NULL);
        IF item IS DISTINCT FROM jsonb_build_object('already_applied', true, 'role_granted', true, 'audit_persisted', true) THEN
            RAISE EXCEPTION 'Repeat approval contract failed: %', item;
        END IF;
        IF (SELECT decided_at FROM public.institution_membership_requests WHERE request_id = req) <> before_decision
            OR (SELECT decision_reason FROM public.institution_membership_requests WHERE request_id = req) <> 'reviewed' THEN
            RAISE EXCEPTION 'Repeat approval rewrote original attribution';
        END IF;
        SELECT count(*) INTO audit_total FROM public.admin_audit_log
        WHERE action = 'membership_request_approved' AND record_id = req::text;
        IF audit_total <> 1 THEN RAISE EXCEPTION 'Repeat approval duplicated audit'; END IF;
        IF public.b05_reject_membership(req, tenant, actor, NULL) IS NOT NULL THEN
            RAISE EXCEPTION 'Rejection overwrote approval';
        END IF;
    END LOOP;
    req := membership_fixture.id('rejected');
    item := public.b05_reject_membership(req, tenant, actor, 'reviewed');
    IF item->>'status' <> 'rejected' OR item->>'audit_persisted' <> 'true' THEN
        RAISE EXCEPTION 'Rejection contract failed: %', item;
    END IF;
    PERFORM public.b05_reject_membership(req, tenant, actor, NULL);
    IF (SELECT count(*) FROM public.admin_audit_log WHERE action = 'membership_request_rejected'
        AND record_id = req::text) <> 1 THEN RAISE EXCEPTION 'Repeat rejection duplicated audit'; END IF;
    IF EXISTS(SELECT 1 FROM public.user_roles WHERE user_id = membership_fixture.id('rejected_user')) THEN
        RAISE EXCEPTION 'Rejection granted a role';
    END IF;
    item := public.phase723_approve_membership_and_grant_role(req, tenant, actor, NULL);
    IF item IS DISTINCT FROM jsonb_build_object('conflict', true) THEN
        RAISE EXCEPTION 'Approval overwrote rejection';
    END IF;
END;
$$;
SELECT 'PASS: staff/faculty approval, repeat confirmation setup, rejection and audit idempotency';
