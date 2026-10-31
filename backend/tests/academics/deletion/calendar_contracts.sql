BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
CREATE FUNCTION workspace_fixture.calendar_record(entity text, identifier uuid)
RETURNS jsonb LANGUAGE sql AS $$
    SELECT public.delete_unused_academic_calendar_record(workspace_fixture.id('admin'),
        workspace_fixture.id('tenant'), entity, identifier)
$$;
DO $$
DECLARE
    actor uuid := workspace_fixture.id('admin'); tenant uuid := workspace_fixture.id('tenant');
    year_row jsonb; term_row jsonb; deleted jsonb; child jsonb; identifier uuid;
    active boolean; entity text; role_name text; audits bigint; serial integer := 0;
BEGIN
    FOREACH active IN ARRAY ARRAY[true, false] LOOP
        year_row := public.manage_academic_master_record(actor, tenant, 'academic_years', NULL,
            jsonb_build_object('name', 'Unused year', 'code', 'DELETE-Y-' || active,
                'start_date', '2120-01-01', 'end_date', '2120-12-31', 'is_active', active));
        SELECT count(*) INTO audits FROM public.admin_audit_log;
        deleted := workspace_fixture.calendar_record('academic_years', (year_row->>'academic_year_id')::uuid);
        IF deleted <> year_row OR EXISTS (SELECT 1 FROM public.academic_years
            WHERE academic_year_id = (year_row->>'academic_year_id')::uuid)
            OR (SELECT count(*) FROM public.admin_audit_log) <> audits + 1 THEN
            RAISE EXCEPTION 'Unused year deletion or audit failed';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM public.admin_audit_log WHERE record_id=year_row->>'academic_year_id'
            AND action='academic.academic_years.delete' AND record_data->'before'=year_row
            AND record_data->'after'='null'::jsonb) THEN
            RAISE EXCEPTION 'Year before-image missing';
        END IF;
        term_row := public.manage_academic_master_record(actor, tenant, 'semesters', NULL,
            jsonb_build_object('name', 'Unused term', 'code', 'DELETE-T-' || active,
                'academic_year_id', workspace_fixture.id('year'), 'semester_number', 20,
                'start_date', '2026-08-01', 'end_date', '2026-09-30', 'is_active', active));
        SELECT count(*) INTO audits FROM public.admin_audit_log;
        deleted := workspace_fixture.calendar_record('semesters', (term_row->>'semester_id')::uuid);
        IF deleted - 'institution_id' <> term_row OR deleted->>'institution_id' <> tenant::text
            OR EXISTS (SELECT 1 FROM public.semesters WHERE semester_id=(term_row->>'semester_id')::uuid)
            OR (SELECT count(*) FROM public.admin_audit_log) <> audits + 1 THEN
            RAISE EXCEPTION 'Unused semester deletion or derived ownership failed';
        END IF;
        BEGIN
            PERFORM workspace_fixture.calendar_record('semesters', (term_row->>'semester_id')::uuid);
            RAISE EXCEPTION 'Repeated semester deletion accepted';
        EXCEPTION WHEN no_data_found THEN NULL; END;
    END LOOP;

    PERFORM public.manage_academic_master_record(actor, tenant, 'academic_years', workspace_fixture.id('year'),
        '{"is_current":false}');
    PERFORM public.manage_academic_master_record(actor, tenant, 'semesters', workspace_fixture.id('term'),
        '{"is_current":false}');
    year_row := public.manage_academic_master_record(actor, tenant, 'academic_years', NULL,
        '{"name":"Current QA year","code":"CURRENT-QA","start_date":"2120-01-01","end_date":"2120-12-31","is_current":true}');
    term_row := public.manage_academic_master_record(actor, tenant, 'semesters', NULL,
        jsonb_build_object('name', 'Current QA term', 'code', 'CURRENT-QA', 'is_current', true,
            'academic_year_id', year_row->>'academic_year_id', 'semester_number', 1,
            'start_date', '2120-01-01', 'end_date', '2120-06-30'));
    FOREACH entity IN ARRAY ARRAY['academic_years', 'semesters'] LOOP
        identifier := CASE entity WHEN 'academic_years' THEN (year_row->>'academic_year_id')::uuid
            ELSE (term_row->>'semester_id')::uuid END;
        BEGIN
            PERFORM workspace_fixture.calendar_record(entity, identifier);
            RAISE EXCEPTION 'Current period was deleted';
        EXCEPTION WHEN SQLSTATE 'P2004' THEN NULL; END;
        FOREACH role_name IN ARRAY ARRAY['staff', 'student', 'foreign_admin'] LOOP
            BEGIN
                PERFORM public.delete_unused_academic_calendar_record(workspace_fixture.id(role_name), tenant,
                    entity, identifier);
                RAISE EXCEPTION 'Unauthorized deletion accepted';
            EXCEPTION WHEN insufficient_privilege THEN NULL; END;
        END LOOP;
        BEGIN
            PERFORM public.delete_unused_academic_calendar_record(workspace_fixture.id('foreign_admin'),
                workspace_fixture.id('foreign_tenant'), entity, identifier);
            RAISE EXCEPTION 'Foreign period was exposed';
        EXCEPTION WHEN no_data_found THEN NULL; END;
        BEGIN
            DELETE FROM public.role_permissions rp USING public.roles r, public.permissions p
            WHERE rp.role_id=r.id AND rp.permission_id=p.permission_id AND r.name='admin'
                AND p.code IN (entity||'.manage', entity||'.*', '*');
            PERFORM workspace_fixture.calendar_record(entity, identifier);
            RAISE EXCEPTION 'Revoked grant accepted';
        EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    END LOOP;

    -- Change current selections before deleting the old, now unused periods.
    PERFORM public.manage_academic_master_record(actor, tenant, 'semesters', (term_row->>'semester_id')::uuid,
        '{"is_current":false}');
    PERFORM public.manage_academic_master_record(actor, tenant, 'academic_years', (year_row->>'academic_year_id')::uuid,
        '{"is_current":false}');
    PERFORM public.manage_academic_master_record(actor, tenant, 'academic_years', workspace_fixture.id('year'),
        '{"is_current":true}');
    PERFORM public.manage_academic_master_record(actor, tenant, 'semesters', workspace_fixture.id('term'),
        '{"is_current":true}');
    PERFORM workspace_fixture.calendar_record('semesters', (term_row->>'semester_id')::uuid);
    PERFORM workspace_fixture.calendar_record('academic_years', (year_row->>'academic_year_id')::uuid);

    FOREACH active IN ARRAY ARRAY[true, false] LOOP
        year_row := public.manage_academic_master_record(actor, tenant, 'academic_years', NULL,
            jsonb_build_object('name', 'Linked QA year', 'code', 'LINK-Y-'||active,
                'start_date', '2121-01-01', 'end_date', '2121-12-31'));
        term_row := public.manage_academic_master_record(actor, tenant, 'semesters', NULL,
            jsonb_build_object('name', 'Linked term', 'code', 'LINK-T', 'academic_year_id', year_row->>'academic_year_id',
                'semester_number', 1, 'start_date', '2121-01-01', 'end_date', '2121-06-30', 'is_active', active));
        BEGIN
            PERFORM workspace_fixture.calendar_record('academic_years', (year_row->>'academic_year_id')::uuid);
            RAISE EXCEPTION 'Year with active or inactive semester was deleted';
        EXCEPTION WHEN SQLSTATE 'P2003' THEN NULL; END;
        PERFORM workspace_fixture.calendar_record('semesters', (term_row->>'semester_id')::uuid);
        PERFORM workspace_fixture.calendar_record('academic_years', (year_row->>'academic_year_id')::uuid);
        serial := serial + 1;
        term_row := public.manage_academic_master_record(actor, tenant, 'semesters', NULL,
            jsonb_build_object('name', 'Mapped term', 'code', 'MAP-T-'||serial, 'academic_year_id', workspace_fixture.id('year'),
                'semester_number', 20+serial, 'start_date', '2026-08-01', 'end_date', '2026-09-30'));
        PERFORM public.manage_academic_master_record(actor, tenant, 'program_courses', NULL,
            jsonb_build_object('program_id', workspace_fixture.id('program'), 'course_id', workspace_fixture.id('unmapped_course'),
                'semester_id', term_row->>'semester_id', 'course_type', 'elective', 'is_active', active));
        BEGIN
            PERFORM workspace_fixture.calendar_record('semesters', (term_row->>'semester_id')::uuid);
            RAISE EXCEPTION 'Semester with subject mapping was deleted';
        EXCEPTION WHEN SQLSTATE 'P2003' THEN NULL; END;
        -- Uniqueness is per program/subject; isolate each status case.
        IF active THEN
            DELETE FROM public.program_courses WHERE program_id=workspace_fixture.id('program')
                AND course_id=workspace_fixture.id('unmapped_course');
        END IF;
    END LOOP;
    year_row := public.manage_academic_master_record(actor, tenant, 'academic_years', NULL,
        '{"name":"Curriculum history year","code":"CURR-Y","start_date":"2140-01-01","end_date":"2140-12-31"}');
    PERFORM public.manage_academic_structure_record(actor, tenant, 'curriculum_versions', NULL,
        jsonb_build_object('program_id', workspace_fixture.id('program'), 'academic_year_id', year_row->>'academic_year_id',
            'name', 'Inactive historical curriculum', 'version', 'HISTORY-2140', 'total_semesters', 8, 'is_active', false));
    BEGIN
        PERFORM workspace_fixture.calendar_record('academic_years', (year_row->>'academic_year_id')::uuid);
        RAISE EXCEPTION 'Year with inactive curriculum was deleted';
    EXCEPTION WHEN SQLSTATE 'P2003' THEN NULL; END;
    BEGIN
        PERFORM workspace_fixture.calendar_record('programs', workspace_fixture.id('program'));
        RAISE EXCEPTION 'Generic RPC accepted an unsupported entity';
    EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
END;
$$;
ROLLBACK;
