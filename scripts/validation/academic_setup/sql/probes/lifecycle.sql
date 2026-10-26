BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
DO $$
DECLARE w jsonb:=academic_setup_check.world(); item record; command text; response jsonb;
    before_identity jsonb; after_identity jsonb; baseline jsonb; duplicates jsonb:='{}';
BEGIN
    -- Normalized uniqueness is retained even by inactive objects.
    FOR item IN SELECT * FROM (VALUES
        ('departments','department'),('programs','program'),('academic_years','year'),
        ('semesters','semester'),('subjects','subject'),('sections','section'),
        ('section_subjects','assignment')
    ) cases(entity,key) LOOP
        -- Build valid duplicate payloads through the same public RPC contracts.
        CASE item.entity
        WHEN 'departments' THEN response:='{"name":"Duplicate","code":" cse "}';
        WHEN 'programs' THEN response:=jsonb_build_object('department_id',w->'department',
            'name','Duplicate','code',' btcse ','degree_type','B.Tech','duration_years',4);
        WHEN 'academic_years' THEN response:='{"name":"Duplicate","code":"2026-27","start_date":"2028-07-01","end_date":"2029-06-30"}';
        WHEN 'semesters' THEN response:=jsonb_build_object('program_id',w->'program','academic_year_id',w->'year',
            'study_semester_number',5,'name','Duplicate','code','SIX');
        WHEN 'subjects' THEN response:=jsonb_build_object('department_id',w->'department',
            'name','Duplicate','code',' dm ','credits',3);
        WHEN 'sections' THEN response:=jsonb_build_object('study_semester_id',w->'semester','name','Other','code',' a ');
        ELSE response:=jsonb_build_object('section_id',w->'section','subject_id',w->'subject');
        END CASE;
        duplicates:=duplicates||jsonb_build_object(item.entity,response);
        command:=format('SELECT academic_setup_check.mutate(%L,%L,%L)',w,item.entity,response);
        PERFORM academic_setup_check.expect_error(command,'23505');
    END LOOP;
    PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,''sections'',%L)',w,
        jsonb_build_object('study_semester_id',w->'semester','name',' section a ','code','B')),'23505',NULL,
        'academic_sections_context_name');
    PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,''academic_years'',%L)',w,
        '{"name":"Overlap","code":"OVER","start_date":"2026-09-01","end_date":"2027-08-01"}'), '23P01');
    baseline:=academic_setup_check.capture(true);
    FOR item IN SELECT * FROM (VALUES
        ('departments','department','Deactivate dependent degree programs first'),
        ('programs','program','Deactivate dependent study semesters first'),
        ('academic_years','year','Deactivate dependent study semesters first'),
        ('semesters','semester','Deactivate dependent sections first'),
        ('subjects','subject','Remove active subject assignments first'),
        ('sections','section','Remove active subject assignments first')) cases(entity,key,message) LOOP
        PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,%L,%L,%L)',
            w,item.entity,'{"is_active":false}',w->>item.key),'23514',item.message);
    END LOOP;
    IF academic_setup_check.capture(true) IS DISTINCT FROM baseline THEN
        RAISE EXCEPTION 'Rejected ancestor deactivation changed state';
    END IF;
    SELECT to_jsonb(t)-'updated_at'-'is_active' INTO before_identity
    FROM public.section_subject_assignments t WHERE assignment_id=(w->>'assignment')::uuid;
    FOR item IN SELECT * FROM (VALUES
        (1,'section_subjects','assignment'),(2,'sections','section'),(3,'semesters','semester'),
        (4,'programs','program'),(5,'subjects','subject'),(6,'academic_years','year'),
        (7,'departments','department')) cases(position,entity,key) ORDER BY position LOOP
        PERFORM academic_setup_check.mutate(w,item.entity,'{"is_active":false}',(w->>item.key)::uuid);
        PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,%L,%L)',
            w,item.entity,duplicates->item.entity),'23505');
        IF item.entity='programs' THEN
            PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,''departments'',%L,%L)',
                w,'{"is_active":false}',w->>'department'),'23514','Deactivate dependent subjects first');
        END IF;
    END LOOP;
    -- Inactive identity is still unique; removal cannot create a replacement link.
    PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,''departments'',%L)',
        w,'{"name":"Duplicate inactive","code":"cse"}'),'23505');
    PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,''section_subjects'',%L,%L)',
        w,'{"is_active":true}',w->>'assignment'),'23514','Active academic parents required');
    PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,''subjects'',%L,%L)',
        w,'{"is_active":true}',w->>'subject'),'23514','Active academic parents required');
    FOR item IN SELECT * FROM (VALUES
        (1,'departments','department'),(2,'academic_years','year'),(3,'programs','program'),
        (4,'semesters','semester'),(5,'subjects','subject'),(6,'sections','section'),
        (7,'section_subjects','assignment')) cases(position,entity,key) ORDER BY position LOOP
        response:=academic_setup_check.mutate(w,item.entity,'{"is_active":true}',(w->>item.key)::uuid);
    END LOOP;
    SELECT to_jsonb(t)-'updated_at'-'is_active' INTO after_identity
    FROM public.section_subject_assignments t WHERE assignment_id=(w->>'assignment')::uuid;
    IF after_identity IS DISTINCT FROM before_identity OR response->>'assignment_id'<>w->>'assignment' THEN
        RAISE EXCEPTION 'Reactivation changed retained assignment identity';
    END IF;
END $$;
ROLLBACK;
