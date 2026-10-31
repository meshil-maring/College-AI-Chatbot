-- Uses the same isolated workspace seed as department deletion contracts.
BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
CREATE FUNCTION workspace_fixture.deletion_program(code text, active boolean DEFAULT true)
RETURNS jsonb LANGUAGE sql AS $$
    SELECT public.manage_academic_master_record(workspace_fixture.id('admin'),
        workspace_fixture.id('tenant'), 'programs', NULL, jsonb_build_object(
            'department_id', workspace_fixture.id('department'), 'name', 'Deletion QA',
            'code', code, 'degree_type', 'B.Tech', 'duration_years', 4, 'is_active', active))
$$;
CREATE FUNCTION workspace_fixture.assert_program_in_use(program uuid, consumer text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE detail text; audits bigint;
BEGIN
    SELECT count(*) INTO audits FROM public.admin_audit_log;
    BEGIN
        PERFORM public.delete_unused_academic_program(workspace_fixture.id('admin'),
            workspace_fixture.id('tenant'), program);
        RAISE EXCEPTION 'Linked program deleted';
    EXCEPTION WHEN SQLSTATE 'P2002' THEN
        GET STACKED DIAGNOSTICS detail = PG_EXCEPTION_DETAIL;
        IF detail IS DISTINCT FROM consumer THEN RAISE EXCEPTION 'Unexpected blocker: %', detail; END IF;
    END;
    IF NOT EXISTS (SELECT 1 FROM public.programs WHERE program_id = program)
        OR (SELECT count(*) FROM public.admin_audit_log) <> audits THEN
        RAISE EXCEPTION 'Blocked deletion changed program or audit';
    END IF;
END;
$$;
DO $$
DECLARE
    actor uuid := workspace_fixture.id('admin');
    tenant uuid := workspace_fixture.id('tenant');
    item jsonb; deleted jsonb; payload jsonb; account_snapshot jsonb; owner jsonb;
    active boolean; consumer text; audit_before bigint;
BEGIN
    SELECT jsonb_agg(to_jsonb(u) ORDER BY u.id) INTO account_snapshot FROM public.users u;
    FOREACH active IN ARRAY ARRAY[true, false] LOOP
        item := workspace_fixture.deletion_program('DELETE-' || active, active);
        SELECT count(*) INTO audit_before FROM public.admin_audit_log;
        deleted := public.delete_unused_academic_program(actor, tenant, (item->>'program_id')::uuid);
        IF deleted - 'institution_id' <> item OR deleted->>'institution_id' <> tenant::text
            OR EXISTS (SELECT 1 FROM public.programs WHERE program_id = (item->>'program_id')::uuid) THEN
            RAISE EXCEPTION 'Unused program deletion or derived tenant failed';
        END IF;
        IF (SELECT count(*) FROM public.admin_audit_log) <> audit_before + 1
            OR NOT EXISTS (SELECT 1 FROM public.admin_audit_log
                WHERE action = 'academic.programs.delete' AND record_id = item->>'program_id'
                AND record_data->'before' = item AND record_data->'after' = 'null'::jsonb) THEN
            RAISE EXCEPTION 'Missing atomic program before-image audit';
        END IF;
        BEGIN
            PERFORM public.delete_unused_academic_program(actor, tenant, (item->>'program_id')::uuid);
            RAISE EXCEPTION 'Repeated deletion accepted';
        EXCEPTION WHEN no_data_found THEN NULL; END;

        FOREACH consumer IN ARRAY ARRAY['program_courses', 'program_semesters', 'curriculum_versions'] LOOP
            item := workspace_fixture.deletion_program(consumer || '-' || active);
            payload := jsonb_build_object('program_id', item->>'program_id', 'is_active', active);
            CASE consumer
            WHEN 'program_courses' THEN
                payload := payload || jsonb_build_object('course_id', workspace_fixture.id('course'),
                    'course_type', 'core');
                PERFORM public.manage_academic_master_record(actor, tenant, consumer, NULL, payload);
            WHEN 'program_semesters' THEN
                payload := payload || '{"name":"Semester 1","code":"S1","semester_number":1}'::jsonb;
                PERFORM public.manage_academic_structure_record(actor, tenant, consumer, NULL, payload);
            WHEN 'curriculum_versions' THEN
                payload := payload || jsonb_build_object('academic_year_id', workspace_fixture.id('year'),
                    'name', 'QA Curriculum', 'version', 'V1', 'total_semesters', 8);
                PERFORM public.manage_academic_structure_record(actor, tenant, consumer, NULL, payload);
            END CASE;
            PERFORM workspace_fixture.assert_program_in_use((item->>'program_id')::uuid, consumer);
        END LOOP;
        item := workspace_fixture.deletion_program('OFFERING-' || active);
        PERFORM public.manage_academic_master_record(actor, tenant, 'program_courses', NULL,
            jsonb_build_object('program_id', item->>'program_id', 'course_id', workspace_fixture.id('course'),
                'course_type', 'core'));
        PERFORM public.manage_academic_master_record(actor, tenant, 'course_offerings', NULL,
            jsonb_build_object('program_id', item->>'program_id', 'course_id', workspace_fixture.id('course'),
                'academic_year_id', workspace_fixture.id('year'), 'semester_id', workspace_fixture.id('term'),
                'is_active', active));
        PERFORM workspace_fixture.assert_program_in_use((item->>'program_id')::uuid, 'course_offerings');
    END LOOP;
    owner := public.manage_academic_master_record(actor, tenant, 'departments', NULL,
        '{"name":"Inactive cleanup","code":"INACTIVE-CLEANUP"}');
    item := public.manage_academic_master_record(actor, tenant, 'programs', NULL,
        jsonb_build_object('department_id', owner->>'department_id', 'name', 'Unused inactive program',
            'code', 'INACTIVE', 'degree_type', 'B.Tech', 'duration_years', 4, 'is_active', false));
    PERFORM public.manage_academic_master_record(actor, tenant, 'departments',
        (owner->>'department_id')::uuid, '{"is_active":false}');
    PERFORM public.delete_unused_academic_program(actor, tenant, (item->>'program_id')::uuid);
    IF NOT EXISTS (SELECT 1 FROM public.departments
        WHERE department_id = (owner->>'department_id')::uuid AND NOT is_active) THEN
        RAISE EXCEPTION 'Cleanup changed inactive owning department';
    END IF;
    -- The realistic seed contains a published curriculum, batch and class section.
    PERFORM workspace_fixture.assert_program_in_use(workspace_fixture.id('program'), 'admission_cohorts');
    IF NOT EXISTS (SELECT 1 FROM public.departments WHERE department_id = workspace_fixture.id('department'))
        OR NOT EXISTS (SELECT 1 FROM public.courses WHERE course_id = workspace_fixture.id('course'))
        OR (SELECT jsonb_agg(to_jsonb(u) ORDER BY u.id) FROM public.users u) IS DISTINCT FROM account_snapshot THEN
        RAISE EXCEPTION 'Program deletion changed its department, subjects or account identities';
    END IF;

    item := workspace_fixture.deletion_program('AUTH-DELETE');
    FOREACH consumer IN ARRAY ARRAY['staff', 'student', 'foreign_admin'] LOOP
        BEGIN
            PERFORM public.delete_unused_academic_program(workspace_fixture.id(consumer), tenant,
                (item->>'program_id')::uuid);
            RAISE EXCEPTION 'Unauthorized actor accepted';
        EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    END LOOP;
    BEGIN
        PERFORM public.delete_unused_academic_program(workspace_fixture.id('foreign_admin'),
            workspace_fixture.id('foreign_tenant'), (item->>'program_id')::uuid);
        RAISE EXCEPTION 'Foreign program deleted';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
        PERFORM public.delete_unused_academic_program(actor, tenant, gen_random_uuid());
        RAISE EXCEPTION 'Missing program accepted';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
        DELETE FROM public.role_permissions rp USING public.roles r, public.permissions p
        WHERE rp.role_id = r.id AND rp.permission_id = p.permission_id AND r.name = 'admin'
            AND p.code IN ('departments.manage', 'departments.*', '*');
        PERFORM public.delete_unused_academic_program(actor, tenant, (item->>'program_id')::uuid);
        RAISE EXCEPTION 'Revoked grant accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        UPDATE public.institutions SET status = 'suspended' WHERE institution_id = tenant;
        PERFORM public.delete_unused_academic_program(actor, tenant, (item->>'program_id')::uuid);
        RAISE EXCEPTION 'Suspended institution accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        PERFORM set_config('request.jwt.claim.role', 'authenticated', true);
        PERFORM public.delete_unused_academic_program(actor, tenant, (item->>'program_id')::uuid);
        RAISE EXCEPTION 'Browser actor accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF has_function_privilege('authenticated', 'public.delete_unused_academic_program(uuid,uuid,uuid)', 'EXECUTE')
        OR has_function_privilege('anon', 'public.delete_unused_academic_program(uuid,uuid,uuid)', 'EXECUTE')
        OR NOT has_function_privilege('service_role', 'public.delete_unused_academic_program(uuid,uuid,uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Incorrect program deletion RPC privileges';
    END IF;
END;
$$;
ROLLBACK;
