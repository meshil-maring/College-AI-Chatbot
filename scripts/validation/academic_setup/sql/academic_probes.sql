-- Rollback-only Academic Setup behavior; no account approval/rejection RPC calls.
BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
DO $$
DECLARE actor uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='admin');
    tenant uuid := (SELECT value FROM academic_decommission_fixture.ids WHERE name='tenant');
    department uuid; program uuid; year_id uuid; semester uuid; section uuid;
    subject uuid; link uuid; response jsonb; title text; before_audit bigint; before_rows bigint;
    actual_constraint text; actual_message text;
BEGIN
    SELECT count(*) INTO before_audit FROM public.admin_audit_log;
    response := public.manage_academic_foundation(actor,tenant,'departments',NULL,
        '{"name":"Computer Science","code":"CSE"}');
    department := (response->>'department_id')::uuid;
    response := public.manage_academic_foundation(actor,tenant,'programs',NULL,
        jsonb_build_object('department_id',department,'name','B.Tech CSE','code','BTCSE',
            'degree_type','B.Tech','duration_years',4));
    program := (response->>'program_id')::uuid;
    response := public.manage_academic_foundation(actor,tenant,'academic_years',NULL,
        '{"name":"2026-2027","code":"2026-27","start_date":"2026-07-01","end_date":"2027-06-30"}');
    year_id := (response->>'academic_year_id')::uuid;
    response := public.manage_academic_structure(actor,tenant,'semesters',NULL,
        jsonb_build_object('program_id',program,'academic_year_id',year_id,
            'study_semester_number',5,'name','Fifth Semester','code','FIFTH'));
    semester := (response->>'study_semester_id')::uuid;
    response := public.manage_academic_sections(actor,tenant,'sections',NULL,
        jsonb_build_object('study_semester_id',semester,'name','Section A','code','A'));
    section := (response->>'section_id')::uuid;
    FOREACH title IN ARRAY ARRAY['Data Mining','Machine Learning','Database Systems'] LOOP
        response := public.manage_academic_structure(actor,tenant,'subjects',NULL,
            jsonb_build_object('department_id',department,'name',title,
                'code',replace(title,' ','_'),'credits',3));
        subject := (response->>'subject_id')::uuid;
        response := public.manage_academic_sections(actor,tenant,'section_subjects',NULL,
            jsonb_build_object('section_id',section,'subject_id',subject));
        link := (response->>'assignment_id')::uuid;
    END LOOP;
    IF (SELECT count(*) FROM public.class_sections WHERE institution_id=tenant)<>1
        OR (SELECT count(*) FROM public.section_subject_assignments WHERE section_id=section AND is_active)<>3
        OR (SELECT count(*) FROM public.admin_audit_log)-before_audit<>11 THEN
        RAISE EXCEPTION 'Shared-section creation or atomic Academic Setup audit failed';
    END IF;
    PERFORM public.manage_academic_sections(actor,tenant,'section_subjects',link,'{"is_active":false}');
    SELECT count(*) INTO before_audit FROM public.admin_audit_log;
    PERFORM public.manage_academic_sections(actor,tenant,'section_subjects',link,'{"is_active":false}');
    IF (SELECT count(*) FROM public.admin_audit_log)<>before_audit
        OR (SELECT count(*) FROM public.subjects WHERE institution_id=tenant)<>3
        OR (SELECT count(*) FROM public.section_subject_assignments WHERE section_id=section AND is_active)<>2 THEN
        RAISE EXCEPTION 'Soft removal must retain subjects and be idempotent';
    END IF;
    BEGIN
        PERFORM public.manage_academic_sections(actor,tenant,'section_subjects',NULL,
            jsonb_build_object('section_id',section,'subject_id',subject));
        RAISE EXCEPTION 'Duplicate inactive assignment accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;
    response := public.manage_academic_sections(actor,tenant,'section_subjects',link,'{"is_active":true}');
    IF (response->>'assignment_id')::uuid<>link THEN RAISE EXCEPTION 'Reactivation changed link identity'; END IF;
    BEGIN
        PERFORM public.manage_academic_sections(actor,tenant,'sections',section,'{"is_active":false}');
        RAISE EXCEPTION 'Section with active assignments deactivated';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_message=MESSAGE_TEXT;
        IF actual_message<>'Remove active subject assignments first' THEN RAISE; END IF;
    END;
    BEGIN
        PERFORM public.manage_academic_structure(actor,tenant,'semesters',semester,'{"study_semester_number":6}');
        RAISE EXCEPTION 'Immutable study semester accepted';
    EXCEPTION WHEN invalid_parameter_value THEN NULL;
    END;
    BEGIN
        PERFORM public.manage_academic_foundation(actor,tenant,'departments',NULL,
            '{"name":"Duplicate","code":" cse "}');
        RAISE EXCEPTION 'Normalized duplicate accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;
    -- Unknown actor and missing exact institution authority must fail before a write.
    BEGIN
        PERFORM public.manage_academic_foundation(gen_random_uuid(),tenant,'departments',NULL,
            '{"name":"Unauthorized","code":"DENIED"}');
        RAISE EXCEPTION 'Unauthorized actor accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    SELECT count(*) INTO before_rows FROM public.departments;
    SELECT count(*) INTO before_audit FROM public.admin_audit_log;
    -- Inject an audit storage failure only inside this rollback-only probe.
    EXECUTE 'ALTER TABLE public.admin_audit_log ADD CONSTRAINT academic_probe_deny '
        || 'CHECK (action NOT LIKE ''academic.%'') NOT VALID';
    BEGIN
        PERFORM public.manage_academic_foundation(actor,tenant,'departments',NULL,
            '{"name":"Must roll back","code":"NOAUDIT"}');
        RAISE EXCEPTION 'Academic mutation survived audit refusal';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_constraint=CONSTRAINT_NAME;
        IF actual_constraint<>'academic_probe_deny' THEN RAISE; END IF;
    END;
    IF (SELECT count(*) FROM public.departments)<>before_rows
        OR (SELECT count(*) FROM public.admin_audit_log)<>before_audit THEN
        RAISE EXCEPTION 'Academic mutation and audit were not atomic';
    END IF;
END $$;
ROLLBACK;
