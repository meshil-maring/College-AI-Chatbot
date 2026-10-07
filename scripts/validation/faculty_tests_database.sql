-- Disposable fully migrated Supabase/PostgreSQL only. Fixtures roll back.
BEGIN;
SET LOCAL search_path = public, extensions;
SELECT set_config('request.jwt.claim.role','service_role',true);
DO $$
DECLARE
    org uuid := gen_random_uuid(); tenant uuid := gen_random_uuid(); foreign_tenant uuid := gen_random_uuid();
    admin_user uuid := gen_random_uuid(); faculty_one uuid := gen_random_uuid(); faculty_two uuid := gen_random_uuid();
    foreign_faculty uuid := gen_random_uuid(); dept uuid := gen_random_uuid(); math_dept uuid := gen_random_uuid(); foreign_dept uuid := gen_random_uuid();
    program uuid := gen_random_uuid(); year_id uuid := gen_random_uuid(); semester uuid := gen_random_uuid();
    course_one uuid := gen_random_uuid(); course_two uuid := gen_random_uuid(); offering_one uuid := gen_random_uuid(); offering_two uuid := gen_random_uuid();
    section_one uuid := gen_random_uuid(); section_two uuid := gen_random_uuid(); hod_id uuid; class_id uuid; teaching_id uuid;
    staged jsonb; rows jsonb; attendance_import_id uuid; version timestamptz; roster_one uuid; student_one uuid := gen_random_uuid(); student_two uuid := gen_random_uuid(); monitor uuid := gen_random_uuid(); before_count integer;
    t jsonb; t_id uuid; data jsonb; result jsonb; mark_rows jsonb; import_rows jsonb; import_version timestamptz; audit_count bigint; suffix text := upper(substr(gen_random_uuid()::text, 1, 8));
BEGIN
    INSERT INTO organizations(organization_id, name, organization_code, official_email, contact_information, status)
    VALUES(org, 'Faculty responsibility test', 'FR-' || suffix, 'faculty-test@example.invalid', 'Disposable fixture', 'active');
    INSERT INTO institutions(institution_id, name, code, organization_id, status)
    VALUES(tenant,'Test university','FRA-' || suffix,org,'active'), (foreign_tenant,'Foreign university','FRB-' || suffix,org,'active');
    INSERT INTO auth.users(id,email) VALUES(admin_user, admin_user || '@example.invalid'),
        (faculty_one,faculty_one || '@example.invalid'), (faculty_two,faculty_two || '@example.invalid'),
        (foreign_faculty,foreign_faculty || '@example.invalid');
    INSERT INTO users(id,auth_user_id,email,first_name,last_name)
    SELECT id,id,email,'Fixture','User' FROM auth.users WHERE id IN(admin_user,faculty_one,faculty_two,foreign_faculty);
    INSERT INTO user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
    SELECT admin_user,id,'institution',tenant,org FROM roles WHERE name='admin';
    INSERT INTO user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
    SELECT u.id,r.id,'institution',CASE WHEN u.id=foreign_faculty THEN foreign_tenant ELSE tenant END,org
    FROM (VALUES(faculty_one),(faculty_two),(foreign_faculty)) u(id) CROSS JOIN roles r WHERE r.name='faculty';
    INSERT INTO departments(department_id,institution_id,name,code) VALUES
        (dept,tenant,'CSE','CSE'),(math_dept,tenant,'Mathematics','MATH'),(foreign_dept,foreign_tenant,'Foreign CSE','CSE');
    INSERT INTO programs(program_id,department_id,name,code,degree_type,duration_years)
    VALUES(program,dept,'B.Tech CSE','BTCSE','B.Tech',4);
    INSERT INTO academic_years(academic_year_id,institution_id,name,code,start_date,end_date)
    VALUES(year_id,tenant,'2026-27','2026-27','2026-07-01','2027-06-30');
    INSERT INTO semesters(semester_id,academic_year_id,name,code,semester_number,start_date,end_date)
    VALUES(semester,year_id,'Semester 5','S5',5,'2026-07-01','2026-12-31');
    INSERT INTO courses(course_id,department_id,name,code)
    VALUES(course_one,dept,'Data Mining','DM'),(course_two,math_dept,'Mathematics','MATH');
    INSERT INTO program_courses(program_id,course_id,course_type) VALUES(program,course_one,'core'),(program,course_two,'elective');
    INSERT INTO course_offerings(course_offering_id,course_id,program_id,academic_year_id,semester_id)
    VALUES(offering_one,course_one,program,year_id,semester),(offering_two,course_two,program,year_id,semester);
    INSERT INTO sections(section_id,course_offering_id,name,code)
    VALUES(section_one,offering_one,'Section A','A'),(section_two,offering_two,'Section A','A');


    teaching_id := create_faculty_teaching_assignment(admin_user,tenant,faculty_one,section_one,
        now() - interval '1 day',NULL,true);
    PERFORM create_faculty_teaching_assignment(admin_user,tenant,faculty_two,section_two,
        now() - interval '1 day',NULL,true);

    INSERT INTO faculty_attendance_rosters(roster_id,institution_id,section_id,course_offering_id,semester_id,
        register_number,university_roll_number,student_name,created_by)
    VALUES(gen_random_uuid(),tenant,section_one,offering_one,semester,'TEST-R1-'||suffix,'TEST-U1-'||suffix,'Unregistered learner',faculty_one),
        (gen_random_uuid(),tenant,section_one,offering_one,semester,'TEST-R2-'||suffix,'TEST-U2-'||suffix,'Absent learner',faculty_one);
    SELECT roster_id INTO roster_one FROM faculty_attendance_rosters WHERE register_number='TEST-R1-'||suffix AND institution_id=tenant;
    data:=jsonb_build_object('title','Model test','test_type','model','max_marks',100,'passing_marks',40,
        'scheduled_date','2026-10-07','start_time','10:00','end_time','11:00');
    t:=save_faculty_test(faculty_one,tenant,section_one,data); t_id:=(t->>'test_id')::uuid;
    IF t->>'status'<>'DRAFT' THEN RAISE EXCEPTION 'Not created as draft'; END IF;
    BEGIN
        PERFORM save_faculty_test(faculty_one,tenant,section_one,data);
        RAISE EXCEPTION 'Duplicate creation allowed';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    BEGIN
        PERFORM save_faculty_test(faculty_two,tenant,section_one,data||'{"title":"Foreign"}');
        RAISE EXCEPTION 'Other subject creation allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        PERFORM save_faculty_test(foreign_faculty,foreign_tenant,section_one,data);
        RAISE EXCEPTION 'Cross tenant creation allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        PERFORM save_faculty_test(faculty_one,tenant,section_one,data||'{"title":"Outside term","scheduled_date":"2027-01-01"}');
        RAISE EXCEPTION 'Outside semester creation allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM transition_faculty_test(faculty_one,tenant,t_id,1,'publish');
        RAISE EXCEPTION 'Draft publication allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    t:=save_faculty_test(faculty_one,tenant,section_one,data||'{"description":"Updated instructions"}',t_id,1);
    BEGIN
        PERFORM transition_faculty_test(faculty_one,tenant,t_id,1,'schedule');
        RAISE EXCEPTION 'Stale version accepted';
    EXCEPTION WHEN serialization_failure THEN NULL; END;
    t:=transition_faculty_test(faculty_one,tenant,t_id,(t->>'version')::bigint,'schedule');
    t:=transition_faculty_test(faculty_one,tenant,t_id,(t->>'version')::bigint,'complete');
    BEGIN
        PERFORM transition_faculty_test(faculty_one,tenant,t_id,(t->>'version')::bigint,'submit');
        RAISE EXCEPTION 'Missing marks submission allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    -- Co-teaching never transfers ownership.
    PERFORM create_faculty_teaching_assignment(admin_user,tenant,faculty_two,section_one,now()-interval '1 day',NULL,true);
    BEGIN
        PERFORM transition_faculty_test(faculty_two,tenant,t_id,(t->>'version')::bigint,'submit');
        RAISE EXCEPTION 'Co-teacher owner bypass';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    mark_rows:=jsonb_build_array(jsonb_build_object('roster_id',roster_one,'mark_status','present','scored_marks',0));
    result:=save_faculty_test_marks(faculty_one,tenant,t_id,(t->>'version')::bigint,mark_rows);
    t:=to_jsonb((SELECT x FROM faculty_tests x WHERE test_id=t_id));
    IF NOT EXISTS(SELECT 1 FROM test_results WHERE test_id=t_id AND scored_marks=0 AND mark_status='present' AND percentage=0 AND student_id IS NULL) THEN
        RAISE EXCEPTION 'Zero or unregistered marks lost'; END IF;
    SELECT count(*) INTO audit_count FROM admin_audit_log WHERE institution_id=tenant;
    BEGIN
        PERFORM save_faculty_test_marks(faculty_one,tenant,t_id,(t->>'version')::bigint,
            jsonb_set(mark_rows,'{0,scored_marks}','99')||jsonb_build_array(jsonb_build_object('roster_id',gen_random_uuid(),'mark_status','present','scored_marks',10)));
        RAISE EXCEPTION 'Forged roster batch allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF (SELECT count(*) FROM admin_audit_log WHERE institution_id=tenant)<>audit_count THEN RAISE EXCEPTION 'Failed batch left audit'; END IF;
    IF (SELECT scored_marks FROM test_results WHERE test_id=t_id AND roster_id=roster_one)<>0 THEN RAISE EXCEPTION 'Failed batch changed marks'; END IF;
    FOR before_count IN 1..3 LOOP
      BEGIN
        PERFORM save_faculty_test_marks(faculty_one,tenant,t_id,(t->>'version')::bigint,
          jsonb_build_array(jsonb_build_object('roster_id',roster_one,'mark_status','present','scored_marks',CASE before_count WHEN 1 THEN -1 WHEN 2 THEN 101 ELSE 1.123 END)));
        RAISE EXCEPTION 'Invalid numeric marks allowed';
      EXCEPTION WHEN check_violation THEN NULL; END;
    END LOOP;
    SELECT jsonb_agg(jsonb_build_object('roster_id',r.roster_id,'mark_status',CASE WHEN r.roster_id=roster_one THEN 'present' ELSE 'absent' END,
      'scored_marks',CASE WHEN r.roster_id=roster_one THEN 0 ELSE NULL END)) INTO mark_rows
      FROM faculty_attendance_rosters r WHERE institution_id=tenant AND section_id=section_one;
    result:=save_faculty_test_marks(faculty_one,tenant,t_id,(t->>'version')::bigint,mark_rows);
    t:=to_jsonb((SELECT x FROM faculty_tests x WHERE test_id=t_id));
    IF NOT EXISTS(SELECT 1 FROM test_results WHERE test_id=t_id AND mark_status='absent' AND scored_marks IS NULL AND percentage IS NULL) THEN
      RAISE EXCEPTION 'Absence became zero'; END IF;
    -- Stage/review/commit with the existing private import tables.
    import_rows:=jsonb_build_array(jsonb_build_object('row_number',2,'raw_data',jsonb_build_object('register_number','TEST-R1-'||suffix,'mark_status','present','scored_marks','60'),
      'normalized_data',jsonb_build_object('register_number','TEST-R1-'||suffix,'university_roll_number','TEST-U1-'||suffix,'mark_status','present','scored_marks','60'),
      'validation_status','VALID','errors','[]'::jsonb,'warnings','[]'::jsonb));
    staged:=stage_faculty_test_import(faculty_one,tenant,t_id,'invalid-identity.csv','CSV','{"valid":2}',
      import_rows||jsonb_build_array(jsonb_build_object('row_number',3,'raw_data','{}'::jsonb,
        'normalized_data',jsonb_build_object('register_number','UNKNOWN','mark_status','present','scored_marks','50'),
        'validation_status','VALID','errors','[]'::jsonb,'warnings','[]'::jsonb)));
    attendance_import_id:=(staged->>'import_id')::uuid;
    SELECT updated_at INTO import_version FROM faculty_attendance_imports WHERE import_id=attendance_import_id;
    BEGIN
      PERFORM commit_faculty_test_import(faculty_one,tenant,attendance_import_id,import_version,(t->>'version')::bigint);
      RAISE EXCEPTION 'Invalid import identity allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    IF (SELECT scored_marks FROM test_results WHERE test_id=t_id AND roster_id=roster_one)<>0 OR
      EXISTS(SELECT 1 FROM admin_audit_log WHERE institution_id=tenant AND action='test.import.commit') THEN
      RAISE EXCEPTION 'Failed import partially changed scores/audit'; END IF;
    staged:=stage_faculty_test_import(faculty_one,tenant,t_id,'marks.csv','CSV','{"valid":1}',import_rows);
    attendance_import_id:=(staged->>'import_id')::uuid;
    SELECT updated_at INTO import_version FROM faculty_attendance_imports WHERE import_id=attendance_import_id;
    PERFORM review_faculty_test_import(faculty_one,tenant,attendance_import_id,import_version,'{"valid":1}',import_rows);
    SELECT updated_at INTO import_version FROM faculty_attendance_imports WHERE import_id=attendance_import_id;
    PERFORM set_config('collegeai.test_write','',true);
    BEGIN
        PERFORM review_faculty_attendance_import(faculty_one,tenant,attendance_import_id,'{"valid":1}',import_rows,import_version);
        RAISE EXCEPTION 'Attendance mutated marks staging';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    result:=commit_faculty_test_import(faculty_one,tenant,attendance_import_id,import_version,(t->>'version')::bigint);
    t:=to_jsonb((SELECT x FROM faculty_tests x WHERE test_id=t_id));
    BEGIN
        PERFORM commit_faculty_test_import(faculty_one,tenant,attendance_import_id,import_version,(t->>'version')::bigint);
        RAISE EXCEPTION 'Duplicate import commit allowed';
    EXCEPTION WHEN serialization_failure THEN NULL; END;
    IF (SELECT scored_marks FROM test_results WHERE test_id=t_id AND roster_id=roster_one)<>60 THEN RAISE EXCEPTION 'Import score wrong'; END IF;
    t:=transition_faculty_test(faculty_one,tenant,t_id,(t->>'version')::bigint,'submit');
    BEGIN
        PERFORM save_faculty_test_marks(faculty_one,tenant,t_id,(t->>'version')::bigint,mark_rows);
        RAISE EXCEPTION 'Submitted marks changed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    t:=transition_faculty_test(faculty_one,tenant,t_id,(t->>'version')::bigint,'publish');
    t:=transition_faculty_test(faculty_one,tenant,t_id,(t->>'version')::bigint,'lock');
    BEGIN
        PERFORM save_faculty_test_marks(faculty_one,tenant,t_id,(t->>'version')::bigint,mark_rows);
        RAISE EXCEPTION 'Locked marks changed normally';
    EXCEPTION WHEN check_violation THEN NULL; END;
    PERFORM set_config('collegeai.test_write','',true);
    BEGIN
        UPDATE test_results SET scored_marks=50 WHERE test_id=t_id;
        RAISE EXCEPTION 'Direct legacy path changed locked marks';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        DELETE FROM test_results WHERE test_id=t_id;
        RAISE EXCEPTION 'History deletion allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    result:=save_faculty_test_marks(faculty_one,tenant,t_id,(t->>'version')::bigint,
      jsonb_build_array(jsonb_build_object('roster_id',roster_one,'mark_status','present','scored_marks',70)),'Verified transcription correction');
    IF NOT EXISTS(SELECT 1 FROM admin_audit_log WHERE institution_id=tenant AND action='test.marks.post_lock_correct'
      AND record_data->'before'->>'marks'='60.00' AND record_data->'after'->>'marks'='70' AND record_data->>'reason'='Verified transcription correction') THEN
      RAISE EXCEPTION 'Correction did not preserve prior/new values and reason'; END IF;
    IF (SELECT status FROM faculty_tests WHERE test_id=t_id)<>'LOCKED' THEN RAISE EXCEPTION 'Correction unlocked result'; END IF;
    -- Existing registration reconciliation links history; pending stays hidden.
    INSERT INTO auth.users(id,email) VALUES(student_one,student_one||'@example.invalid');
    INSERT INTO users(id,auth_user_id,email,first_name,last_name) VALUES(student_one,student_one,student_one||'@example.invalid','Marks','Student');
    INSERT INTO students(student_id,user_id,institution_id,student_number,register_number,university_roll_number,email,enrollment_date,program_id,academic_year_id,approval_status)
    VALUES(student_one,student_one,tenant,'TEST-R1-'||suffix,'TEST-R1-'||suffix,'TEST-U1-'||suffix,student_one||'@example.invalid','2026-07-01',program,year_id,'pending');
    IF EXISTS(SELECT 1 FROM test_results WHERE test_id=t_id AND student_id=student_one) THEN RAISE EXCEPTION 'Pending registration exposed marks'; END IF;
    UPDATE students SET approval_status='approved' WHERE student_id=student_one;
    IF NOT EXISTS(SELECT 1 FROM test_results WHERE test_id=t_id AND student_id=student_one AND scored_marks=70 AND status='published') THEN
      RAISE EXCEPTION 'Approved registration lost historical marks'; END IF;
    UPDATE students SET approval_status='pending' WHERE student_id=student_one;
    IF EXISTS(SELECT 1 FROM test_results WHERE test_id=t_id AND student_id=student_one AND status='published') THEN
      RAISE EXCEPTION 'Approval withdrawal leaked workflow marks'; END IF;
    UPDATE students SET approval_status='approved' WHERE student_id=student_one;
    UPDATE students SET is_active=false WHERE student_id=student_one;
    IF EXISTS(SELECT 1 FROM test_results WHERE test_id=t_id AND student_id=student_one AND status='published') THEN
      RAISE EXCEPTION 'Inactive registration leaked workflow marks'; END IF;
    UPDATE students SET is_active=true WHERE student_id=student_one;
    UPDATE students SET university_roll_number='WRONG-'||suffix WHERE student_id=student_one;
    IF NOT EXISTS(SELECT 1 FROM test_results WHERE test_id=t_id AND student_id=student_one AND scored_marks=70 AND status='draft') THEN
      RAISE EXCEPTION 'Conflicting identity was exposed or history lost'; END IF;
    IF has_function_privilege('authenticated','save_faculty_test_marks(uuid,uuid,uuid,bigint,jsonb,text)','EXECUTE') OR
       has_table_privilege('authenticated','faculty_tests','SELECT') THEN RAISE EXCEPTION 'Public assessment access granted'; END IF;
    IF has_table_privilege('authenticated','test_results','SELECT') OR has_table_privilege('anon','test_results','UPDATE') THEN
      RAISE EXCEPTION 'Direct result access granted'; END IF;
    INSERT INTO auth.users(id,email) VALUES(monitor,monitor||'@example.invalid');
    INSERT INTO users(id,auth_user_id,email,first_name,last_name) VALUES(monitor,monitor,monitor||'@example.invalid','Monitoring','Faculty');
    INSERT INTO user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id) SELECT monitor,id,'institution',tenant,org FROM roles WHERE name='faculty';
    PERFORM manage_faculty_responsibility(admin_user,tenant,monitor,'hod','department',dept,now()-interval '1 day',NULL,true);
    PERFORM manage_faculty_responsibility(admin_user,tenant,monitor,'class_in_charge','section',section_one,now()-interval '1 day',NULL,true);
    BEGIN
      PERFORM save_faculty_test(monitor,tenant,section_one,data||'{"title":"Monitoring mutation"}'::jsonb);
      RAISE EXCEPTION 'Responsibility granted assessment mutation';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF (SELECT count(*) FROM responsibility_permissions rp JOIN permissions p USING(permission_id)
        WHERE rp.responsibility_code IN ('hod','class_in_charge') AND p.code='results.read')<>2 THEN
      RAISE EXCEPTION 'Explicit responsibility result mappings missing'; END IF;
    RAISE NOTICE 'ASSESSMENT DATABASE CONTRACTS PASS';
END; $$;
SET LOCAL ROLE authenticated;
DO $$ BEGIN
 BEGIN
   PERFORM count(*) FROM public.faculty_tests;
   RAISE EXCEPTION 'Authenticated direct exam reads allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
   PERFORM count(*) FROM public.test_results;
   RAISE EXCEPTION 'Authenticated direct result reads allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END; $$;
RESET ROLE;
ROLLBACK;
