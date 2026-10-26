-- Prepared database-role probes; JWT claims never substitute for SET LOCAL ROLE.
BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
CREATE FUNCTION academic_setup_check.as_role(role_name text, command text, expected_state text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE actual_state text; response jsonb;
BEGIN
    IF session_user<>'postgres' OR current_user<>'postgres'
        OR role_name NOT IN ('anon','authenticated','service_role') OR role_name IS NULL THEN
        RAISE EXCEPTION 'Invalid privilege probe caller or role';
    END IF;
    EXECUTE format('SET LOCAL ROLE %I',role_name);
    IF current_user<>role_name THEN RAISE EXCEPTION 'Database role switch failed'; END IF;
    -- No call into the private harness schema occurs while assuming an API role.
    -- Otherwise a harness-schema denial could masquerade as an application denial.
    BEGIN
        IF expected_state IS NULL THEN
            -- Only the three approved RPC controls return jsonb, exactly one row.
            EXECUTE command INTO STRICT response;
        ELSE
            -- Private actor/trigger helpers return void/trigger, not jsonb.
            -- An unexpected successful call still fails the required denial.
            EXECUTE command;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE;
    END;
    RESET ROLE;
    IF current_user<>'postgres' THEN RAISE EXCEPTION 'Database role was not restored'; END IF;
    IF actual_state IS DISTINCT FROM expected_state THEN
        RAISE EXCEPTION 'Database-role probe produced an unexpected result';
    END IF;
    RETURN response;
EXCEPTION WHEN OTHERS THEN
    RESET ROLE;
    RAISE;
END $$;
REVOKE ALL ON FUNCTION academic_setup_check.as_role(text,text,text)
    FROM PUBLIC,anon,authenticated,service_role;
DO $$
DECLARE w jsonb:=academic_setup_check.world(); browser text; entity text; command text; item record;
    baseline jsonb; response jsonb; before_audit bigint;
BEGIN
    -- These are exact signatures/return types from the immutable migration pins.
    FOR item IN SELECT * FROM (VALUES
        ('public.assert_academic_foundation_actor(uuid,uuid,text)','void',false),
        ('public.validate_academic_foundation()','trigger',false),
        ('public.validate_academic_structure()','trigger',false),
        ('public.guard_academic_structure_parent()','trigger',false),
        ('public.validate_academic_sections()','trigger',false),
        ('public.guard_academic_sections_parent()','trigger',false),
        ('public.manage_academic_foundation(uuid,uuid,text,uuid,jsonb)','jsonb',true),
        ('public.manage_academic_structure(uuid,uuid,text,uuid,jsonb)','jsonb',true),
        ('public.manage_academic_sections(uuid,uuid,text,uuid,jsonb)','jsonb',true)
    ) contracts(signature,result_type,rpc) LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_proc p WHERE p.oid=to_regprocedure(item.signature)
            AND p.prokind='f' AND p.prorettype=to_regtype(item.result_type)
            AND NOT p.proretset AND p.proowner='postgres'::regrole AND p.prosecdef
            AND p.proconfig=ARRAY['search_path=""']::text[]) THEN
            RAISE EXCEPTION 'Pinned helper/RPC signature or return contract differs';
        END IF;
        FOREACH browser IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            IF has_function_privilege(browser,item.signature,'EXECUTE') IS DISTINCT FROM
                (item.rpc AND browser='service_role') THEN
                RAISE EXCEPTION 'Pinned helper/RPC execution grants differ';
            END IF;
        END LOOP;
    END LOOP;
    baseline:=academic_setup_check.capture(true);
    FOREACH browser IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
        FOREACH entity IN ARRAY ARRAY['departments','programs','academic_years','study_semesters',
            'subjects','class_sections','section_subject_assignments'] LOOP
            FOREACH command IN ARRAY ARRAY[
                format('INSERT INTO public.%I DEFAULT VALUES',entity),
                format('UPDATE public.%I SET is_active=is_active WHERE false',entity),
                format('DELETE FROM public.%I WHERE false',entity),
                format('TRUNCATE TABLE public.%I',entity)] LOOP
                PERFORM academic_setup_check.as_role(browser,command,'42501');
            END LOOP;
        END LOOP;
        FOREACH command IN ARRAY ARRAY[
            format('SELECT public.assert_academic_foundation_actor(%L::uuid,%L::uuid,''departments'')',
                w->>'actor',w->>'tenant'),
            'SELECT public.validate_academic_foundation()',
            'SELECT public.validate_academic_structure()',
            'SELECT public.guard_academic_structure_parent()',
            'SELECT public.validate_academic_sections()',
            'SELECT public.guard_academic_sections_parent()'] LOOP
            PERFORM academic_setup_check.as_role(browser,command,'42501');
        END LOOP;
    END LOOP;
    -- Valid payloads and a service JWT claim make browser denial depend on the
    -- actual database-role ACL. The same RPC commands must work for service_role.
    FOR item IN SELECT * FROM (VALUES
        ('manage_academic_foundation','departments','department_id','departments',
            '{"name":"Role probe","code":"ROLE_PROBE"}'::jsonb),
        ('manage_academic_structure','subjects','subject_id','subjects',
            jsonb_build_object('department_id',w->'department','name','Role probe','code','ROLE_PROBE','credits',3)),
        ('manage_academic_sections','sections','section_id','class_sections',
            jsonb_build_object('study_semester_id',w->'semester','name','Role probe','code','ROLE_PROBE'))
    ) cases(routine,entity,key,relation_name,payload) LOOP
        command:=format('SELECT public.%I(%L::uuid,%L::uuid,%L,NULL::uuid,%L::jsonb)',
            item.routine,w->>'actor',w->>'tenant',item.entity,item.payload);
        FOREACH browser IN ARRAY ARRAY['anon','authenticated'] LOOP
            PERFORM academic_setup_check.as_role(browser,command,'42501');
        END LOOP;
    END LOOP;
    IF academic_setup_check.capture(true) IS DISTINCT FROM baseline THEN
        RAISE EXCEPTION 'Denied database-role requests changed state';
    END IF;
    SELECT count(*) INTO before_audit FROM public.admin_audit_log;
    FOR item IN SELECT * FROM (VALUES
        ('manage_academic_foundation','departments','department_id','departments',
            '{"name":"Role probe","code":"ROLE_PROBE"}'::jsonb),
        ('manage_academic_structure','subjects','subject_id','subjects',
            jsonb_build_object('department_id',w->'department','name','Role probe','code','ROLE_PROBE','credits',3)),
        ('manage_academic_sections','sections','section_id','class_sections',
            jsonb_build_object('study_semester_id',w->'semester','name','Role probe','code','ROLE_PROBE'))
    ) cases(routine,entity,key,relation_name,payload) LOOP
        command:=format('SELECT public.%I(%L::uuid,%L::uuid,%L,NULL::uuid,%L::jsonb)',
            item.routine,w->>'actor',w->>'tenant',item.entity,item.payload);
        response:=academic_setup_check.as_role('service_role',command);
        IF jsonb_typeof(response) IS DISTINCT FROM 'object' OR response->>item.key IS NULL
            OR response->>'institution_id' IS DISTINCT FROM w->>'tenant'
            OR (SELECT count(*) FROM public.admin_audit_log
            WHERE institution_id=(w->>'tenant')::uuid AND actor_user_id=(w->>'actor')::uuid
                AND action='academic.'||item.entity||'.create' AND status='success'
                AND table_name=item.relation_name
                AND record_id=response->>item.key AND record_data->'before'='null'::jsonb
                AND record_data->'after'=response)<>1 THEN
            RAISE EXCEPTION 'Permitted service-role RPC or its audit evidence failed';
        END IF;
    END LOOP;
    IF current_user<>'postgres' OR (SELECT count(*) FROM public.admin_audit_log)<>before_audit+3 THEN
        RAISE EXCEPTION 'Service-role controls left unexpected role or audit state';
    END IF;
END $$;
ROLLBACK;
