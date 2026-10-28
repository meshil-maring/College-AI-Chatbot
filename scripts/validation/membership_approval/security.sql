SET request.jwt.claim.role = 'service_role';
CREATE FUNCTION membership_fixture.fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.record_id = membership_fixture.id('audit_failure')::text THEN
        RAISE EXCEPTION 'Forced audit failure' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER membership_audit_failure BEFORE INSERT ON public.admin_audit_log
FOR EACH ROW EXECUTE FUNCTION membership_fixture.fail_audit();
DO $$
DECLARE tenant uuid := membership_fixture.id('tenant'); actor uuid := membership_fixture.id('admin');
    req uuid := membership_fixture.id('audit_failure'); foreign_tenant uuid := gen_random_uuid(); item jsonb;
BEGIN
    BEGIN
        PERFORM public.phase723_approve_membership_and_grant_role(req, tenant, actor, NULL);
        RAISE EXCEPTION 'Audit failure did not abort approval';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    IF (SELECT status FROM public.institution_membership_requests WHERE request_id = req) <> 'pending'
        OR EXISTS(SELECT 1 FROM public.user_roles WHERE user_id = membership_fixture.id('audit_failure_user')) THEN
        RAISE EXCEPTION 'Audit failure committed a partial decision';
    END IF;
    BEGIN
        PERFORM public.b05_reject_membership(req, tenant, actor, NULL);
        RAISE EXCEPTION 'Audit failure did not abort rejection';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    IF (SELECT status FROM public.institution_membership_requests WHERE request_id = req) <> 'pending' THEN
        RAISE EXCEPTION 'Audit failure committed rejection';
    END IF;
    IF has_function_privilege('authenticated', 'public.phase723_approve_membership_and_grant_role(uuid,uuid,uuid,text)', 'EXECUTE')
        OR has_function_privilege('anon', 'public.b05_reject_membership(uuid,uuid,uuid,text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Client role can execute membership decisions';
    END IF;
    BEGIN
        PERFORM public.phase723_approve_membership_and_grant_role(membership_fixture.id('staff'), tenant,
            membership_fixture.id('staff_user'), NULL);
        RAISE EXCEPTION 'Non-admin repeat approval was accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    INSERT INTO public.institutions(institution_id, organization_id, name, code, status)
    VALUES(foreign_tenant, membership_fixture.id('organization'), 'Other Approval Institute', 'APPROVAL-OTHER', 'active');
    req := membership_fixture.id('cross_scope');
    INSERT INTO public.user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
    SELECT membership_fixture.id('cross_scope_user'), id, 'institution', foreign_tenant,
        membership_fixture.id('organization') FROM public.roles WHERE name = 'staff';
    BEGIN
        PERFORM public.phase723_approve_membership_and_grant_role(req, tenant, actor, NULL);
        RAISE EXCEPTION 'Approval moved an existing role to a different tenant';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    item := public.phase723_approve_membership_and_grant_role(gen_random_uuid(), tenant, actor, NULL);
    IF item IS DISTINCT FROM jsonb_build_object('not_found', true) THEN RAISE EXCEPTION 'Foreign request leaked'; END IF;
    DELETE FROM public.user_roles WHERE user_id = membership_fixture.id('staff_user');
    item := public.phase723_approve_membership_and_grant_role(membership_fixture.id('staff'), tenant, actor, NULL);
    IF item IS DISTINCT FROM jsonb_build_object('invalid_state', true) THEN
        RAISE EXCEPTION 'Repeat approval restored a revoked grant';
    END IF;
    UPDATE public.organizations SET status = 'suspended'
    WHERE organization_id = membership_fixture.id('organization');
    BEGIN
        PERFORM public.phase723_approve_membership_and_grant_role(membership_fixture.id('faculty'), tenant, actor, NULL);
        RAISE EXCEPTION 'Suspended parent allowed approval';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;
SELECT 'PASS: audit rollback, client ACLs, repeat authorization, scope preservation, revocation and tenant lifecycle';
