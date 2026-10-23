CREATE EXTENSION IF NOT EXISTS plpgsql_check WITH SCHEMA extensions;
SET request.jwt.claim.role = 'service_role';
DO $$
DECLARE profile uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='profile');
    tenant uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='tenant');
    admin uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='admin');
    staff uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='staff');
    changed integer; diagnostic record;
BEGIN
    IF NOT EXISTS(SELECT 1 FROM public.students WHERE student_id=profile AND approval_status='approved'
        AND register_number='DC-PRESERVED' AND university_roll_number='DC-ROLL' AND is_active) THEN
        RAISE EXCEPTION 'Canonical student identity/lifecycle was not retained';
    END IF;
    IF EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='students'
        AND column_name IN('program_id','academic_year_id')) THEN
        RAISE EXCEPTION 'Student academic references remain';
    END IF;
    IF EXISTS(SELECT 1 FROM pg_proc WHERE pronamespace='public'::regnamespace AND proname LIKE 'academic_package_%') THEN
        RAISE EXCEPTION 'Package runtime functions remain';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM public.user_permission_grants g JOIN public.permissions p USING(permission_id)
        WHERE g.user_id=staff AND p.code='documents.read' AND g.revoked_at IS NULL) THEN
        RAISE EXCEPTION 'Nonacademic staff grant was lost';
    END IF;
    changed := public.phase81_manage_staff_permission_grants(admin,tenant,staff,ARRAY['documents.update'],true);
    IF changed <> 1 THEN RAISE EXCEPTION 'Retained authorized delegation failed'; END IF;
    BEGIN
        PERFORM public.phase81_manage_staff_permission_grants(admin,tenant,staff,ARRAY['attendance.read'],true);
        RAISE EXCEPTION 'Retired permission was accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    -- Trigger-based approval/account state changes must no longer touch any
    -- deleted academic tables. The same canonical profile remains usable.
    UPDATE public.students SET approval_status='pending' WHERE student_id=profile;
    UPDATE public.students SET approval_status='approved' WHERE student_id=profile;
    IF to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NOT NULL THEN
        PERFORM public.b05_approve_student(profile,tenant,admin,(SELECT auth_user_id FROM public.users WHERE id=admin));
    END IF;
    FOR diagnostic IN SELECT * FROM extensions.plpgsql_check_function_tb(
        'public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)'::regprocedure,fatal_errors:=false) LOOP
        IF diagnostic.level IN('error','fatal error') THEN RAISE EXCEPTION 'Delegation SQL lint failed: %',diagnostic.message; END IF;
    END LOOP;
END;
$$;
SELECT 'PASS: student approval/account identity and nonacademic permissions survive academic decommission' AS result;
