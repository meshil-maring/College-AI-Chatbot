-- Installed only in the future isolated container, never exposed to API roles.
BEGIN;
CREATE FUNCTION academic_setup_check.expect_error(command text, expected_state text,
    expected_message text DEFAULT NULL, expected_constraint text DEFAULT NULL) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE actual_state text; actual_message text; actual_constraint text;
BEGIN
    BEGIN
        EXECUTE command;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE,
            actual_message=MESSAGE_TEXT,actual_constraint=CONSTRAINT_NAME;
        IF actual_state IS DISTINCT FROM expected_state
            OR (expected_message IS NOT NULL AND actual_message IS DISTINCT FROM expected_message)
            OR (expected_constraint IS NOT NULL AND actual_constraint IS DISTINCT FROM expected_constraint) THEN
            RAISE EXCEPTION 'Probe produced an unexpected failure';
        END IF;
        RETURN;
    END;
    RAISE EXCEPTION 'Probe unexpectedly succeeded';
END $$;
CREATE FUNCTION academic_setup_check.mutate(world jsonb, entity text,
    payload jsonb, record_id uuid DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE routine text;
BEGIN
    routine := CASE WHEN entity IN ('departments','programs','academic_years') THEN 'manage_academic_foundation'
        WHEN entity IN ('semesters','subjects') THEN 'manage_academic_structure' ELSE 'manage_academic_sections' END;
    EXECUTE format('SELECT public.%I($1,$2,$3,$4,$5)',routine)
    INTO payload USING (world->>'actor')::uuid,(world->>'tenant')::uuid,entity,record_id,payload;
    RETURN payload;
END $$;
CREATE FUNCTION academic_setup_check.world() RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE tenant uuid:=gen_random_uuid(); actor uuid:=gen_random_uuid(); auth_id uuid:=gen_random_uuid();
    org uuid; w jsonb; r jsonb;
BEGIN
    SELECT organization_id INTO STRICT org FROM public.organizations WHERE organization_code='COLLEGE-AI-PLATFORM';
    INSERT INTO public.institutions(institution_id,organization_id,name,code,status)
    VALUES(tenant,org,'Synthetic harness tenant','H-'||tenant::text,'active');
    INSERT INTO auth.users(id,email) VALUES(auth_id,actor::text||'@example.invalid');
    INSERT INTO public.users(id,auth_user_id,email,first_name,last_name)
    VALUES(actor,auth_id,actor::text||'@example.invalid','Synthetic','Harness');
    INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
    SELECT actor,id,'institution',tenant,org FROM public.roles WHERE name='admin';
    w:=jsonb_build_object('tenant',tenant,'actor',actor,'auth',auth_id,'org',org);
    r:=academic_setup_check.mutate(w,'departments','{"name":"Computer Science","code":"CSE"}');
    w:=w||jsonb_build_object('department',r->'department_id');
    r:=academic_setup_check.mutate(w,'programs',jsonb_build_object('department_id',w->'department',
        'name','B.Tech CSE','code','BTCSE','degree_type','B.Tech','duration_years',4));
    w:=w||jsonb_build_object('program',r->'program_id');
    r:=academic_setup_check.mutate(w,'academic_years',
        '{"name":"2026-2027","code":"2026-27","start_date":"2026-07-01","end_date":"2027-06-30"}');
    w:=w||jsonb_build_object('year',r->'academic_year_id');
    r:=academic_setup_check.mutate(w,'semesters',jsonb_build_object('program_id',w->'program',
        'academic_year_id',w->'year','study_semester_number',5,'name','Fifth Semester','code','FIFTH'));
    w:=w||jsonb_build_object('semester',r->'study_semester_id');
    r:=academic_setup_check.mutate(w,'subjects',jsonb_build_object('department_id',w->'department',
        'name','Data Mining','code','DM','credits',3));
    w:=w||jsonb_build_object('subject',r->'subject_id');
    r:=academic_setup_check.mutate(w,'sections',jsonb_build_object('study_semester_id',w->'semester',
        'name','Section A','code','A'));
    w:=w||jsonb_build_object('section',r->'section_id');
    r:=academic_setup_check.mutate(w,'section_subjects',jsonb_build_object(
        'section_id',w->'section','subject_id',w->'subject'));
    RETURN w||jsonb_build_object('assignment',r->'assignment_id');
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA academic_setup_check FROM PUBLIC,anon,authenticated,service_role;
COMMIT;
