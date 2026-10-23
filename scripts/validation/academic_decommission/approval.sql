SET request.jwt.claim.role = 'service_role';
CREATE FUNCTION academic_decommission_fixture.reject_approval() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.action='student.approve' AND NEW.record_id=current_setting('app.decommission_fail_approval',true) THEN
        RAISE EXCEPTION 'Disposable forced approval audit failure' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER decommission_approval_audit_probe BEFORE INSERT ON public.admin_audit_log
FOR EACH ROW EXECUTE FUNCTION academic_decommission_fixture.reject_approval();
DO $$
DECLARE tenant uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='tenant');
    admin uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='admin');
    actor_auth uuid; target uuid; target_user uuid; auth_id uuid; foreign_tenant uuid := gen_random_uuid();
    foreign_target uuid; selected_tenant uuid; item jsonb; label text; observed text; diagnostic record;
    adapter boolean := NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public'
        AND table_name='admin_audit_log' AND column_name='decision_key');
BEGIN
    IF to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NULL THEN
        RAISE EXCEPTION 'Identity-only approval RPC is required in both supported baselines';
    END IF;
    IF has_function_privilege('authenticated','public.b05_approve_student(uuid,uuid,uuid,uuid)','EXECUTE')
        OR NOT has_function_privilege('service_role','public.b05_approve_student(uuid,uuid,uuid,uuid)','EXECUTE') THEN
        RAISE EXCEPTION 'Approval transport ACL is invalid';
    END IF;
    SELECT auth_user_id INTO actor_auth FROM public.users WHERE id=admin;
    INSERT INTO public.institutions(institution_id,organization_id,name,code,status)
    SELECT foreign_tenant,organization_id,'Other approval tenant','DC-OTHER-' || foreign_tenant::text,'active'
    FROM public.institutions WHERE institution_id=tenant;
    FOREACH label IN ARRAY ARRAY['pending','foreign'] LOOP
        target_user:=gen_random_uuid(); auth_id:=gen_random_uuid();
        selected_tenant:=CASE WHEN label='pending' THEN tenant ELSE foreign_tenant END;
        INSERT INTO auth.users(id,email) VALUES(auth_id,target_user::text || '@example.invalid');
        INSERT INTO public.users(id,auth_user_id,email,first_name,last_name)
        VALUES(target_user,auth_id,target_user::text || '@example.invalid','Approval',label);
        INSERT INTO public.students(user_id,institution_id,student_number,email,enrollment_date,approval_status)
        VALUES(target_user,selected_tenant,'DC-APPROVE-' || target_user::text,
            target_user::text || '@example.invalid',current_date,'pending') RETURNING student_id INTO target;
        IF label='pending' THEN
            INSERT INTO academic_decommission_fixture.ids VALUES('approval_target',target),('approval_target_user',target_user);
        ELSE foreign_target:=target; END IF;
    END LOOP;
    SELECT value INTO target FROM academic_decommission_fixture.ids WHERE name='approval_target';
    SELECT value INTO target_user FROM academic_decommission_fixture.ids WHERE name='approval_target_user';
    BEGIN
        PERFORM public.b05_approve_student(target,tenant,admin,gen_random_uuid());
    EXCEPTION WHEN OTHERS THEN observed:=SQLSTATE;
    END;
    IF observed IS DISTINCT FROM '42501' THEN RAISE EXCEPTION 'Spoofed approval actor was accepted'; END IF;
    item:=public.b05_approve_student(foreign_target,tenant,admin,actor_auth);
    IF item IS DISTINCT FROM jsonb_build_object('not_found',true) THEN RAISE EXCEPTION 'Cross-tenant target disclosed or modified'; END IF;
    IF adapter THEN
        FOREACH label IN ARRAY ARRAY['suspended','rejected'] LOOP
            UPDATE public.organizations SET status=label WHERE organization_id=(
                SELECT organization_id FROM public.institutions WHERE institution_id=tenant);
            observed:=NULL;
            BEGIN
                PERFORM public.b05_approve_student(target,tenant,admin,actor_auth);
            EXCEPTION WHEN OTHERS THEN observed:=SQLSTATE;
            END;
            IF observed IS DISTINCT FROM '42501' THEN RAISE EXCEPTION 'Closed parent organization was accepted'; END IF;
        END LOOP;
        UPDATE public.organizations SET status='active' WHERE organization_id=(
            SELECT organization_id FROM public.institutions WHERE institution_id=tenant);
        UPDATE public.permissions SET is_active=false WHERE code='students.approve';
        observed:=NULL;
        BEGIN
            PERFORM public.b05_approve_student(target,tenant,admin,actor_auth);
        EXCEPTION WHEN OTHERS THEN observed:=SQLSTATE;
        END;
        IF observed IS DISTINCT FROM '42501' THEN RAISE EXCEPTION 'Missing authoritative approval permission was accepted'; END IF;
        UPDATE public.permissions SET is_active=true WHERE code='students.approve';
    END IF;
    PERFORM set_config('app.decommission_fail_approval',target::text,true);
    observed:=NULL;
    BEGIN
        PERFORM public.b05_approve_student(target,tenant,admin,actor_auth);
    EXCEPTION WHEN OTHERS THEN observed:=SQLSTATE;
    END;
    IF observed IS DISTINCT FROM '23514' OR NOT EXISTS(SELECT 1 FROM public.students
        WHERE student_id=target AND approval_status='pending') OR EXISTS(SELECT 1 FROM public.user_roles
        WHERE user_id=target_user) OR EXISTS(SELECT 1 FROM public.admin_audit_log
        WHERE action='student.approve' AND table_name='students' AND record_id=target::text) THEN
        RAISE EXCEPTION 'Failed audit did not roll back approval and role provisioning atomically';
    END IF;
    PERFORM set_config('app.decommission_fail_approval','',true);
    item:=public.b05_approve_student(target,tenant,admin,actor_auth);
    IF item->'student'->>'student_id' IS DISTINCT FROM target::text
        OR item->'student'->>'approval_status' IS DISTINCT FROM 'approved'
        OR item->>'role_granted' IS DISTINCT FROM 'true' OR item->>'audit_persisted' IS DISTINCT FROM 'true' THEN
        RAISE EXCEPTION 'Approval response does not confirm canonical profile, role and atomic audit';
    END IF;
    PERFORM public.b05_approve_student(target,tenant,admin,actor_auth);
    IF (SELECT count(*) FROM public.admin_audit_log WHERE institution_id=tenant AND action='student.approve'
        AND table_name='students' AND record_id=target::text) <> 1 OR (SELECT count(*) FROM public.user_roles ur
        JOIN public.roles r ON r.id=ur.role_id JOIN public.institutions i ON i.institution_id=tenant
        WHERE ur.user_id=target_user AND r.name='student' AND ur.scope_type='institution' AND ur.scope_id=tenant
          AND ur.scope_organization_id=i.organization_id) <> 1 THEN
        RAISE EXCEPTION 'Approval retry duplicates or mis-scopes account provisioning';
    END IF;
    UPDATE public.students SET approval_status='rejected' WHERE student_id=target;
    item:=public.b05_approve_student(target,tenant,admin,actor_auth);
    IF item IS DISTINCT FROM jsonb_build_object('conflict',true) THEN RAISE EXCEPTION 'Rejected lifecycle was reopened'; END IF;
    FOR diagnostic IN SELECT * FROM extensions.plpgsql_check_function_tb(
        'public.b05_approve_student(uuid,uuid,uuid,uuid)'::regprocedure,fatal_errors:=false) LOOP
        IF diagnostic.level IN('error','fatal error') THEN RAISE EXCEPTION 'Approval SQL lint: %',diagnostic.message; END IF;
    END LOOP;
END;
$$;
DROP TRIGGER decommission_approval_audit_probe ON public.admin_audit_log;
DROP FUNCTION academic_decommission_fixture.reject_approval();
SELECT 'PASS: actual approval RPC is atomic, tenant-bound, authenticated, retry-idempotent and independent of academics' AS result;
