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
    audit_count bigint; suffix text := upper(substr(gen_random_uuid()::text, 1, 8));
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
    rows := jsonb_build_array(jsonb_build_object('row_number',2,'raw_data',jsonb_build_object('register_number','R-'||suffix,'university_roll_number','U-'||suffix,'student_name','Unregistered student','status','present','session_date','2026-10-07'),
        'normalized_data',jsonb_build_object('register_number','R-'||suffix,'university_roll_number','U-'||suffix,'student_name','Unregistered student','status','present','session_date','2026-10-07'),
        'validation_status','NEW','errors','[]'::jsonb,'warnings','[]'::jsonb));
    staged := stage_faculty_attendance_import(faculty_one,tenant,section_one,semester,'attendance.csv','csv','CSV',false,
        '{"valid":1,"total_rows":1,"errors":0,"conflicts":0,"duplicates":0}'::jsonb,rows);
    attendance_import_id := (staged->>'import_id')::uuid;
    SELECT updated_at INTO version FROM faculty_attendance_imports WHERE faculty_attendance_imports.import_id = attendance_import_id;
    PERFORM review_faculty_attendance_import(faculty_one,tenant,attendance_import_id,'{"valid":1,"total_rows":1}'::jsonb,rows,version);
    SELECT updated_at INTO version FROM faculty_attendance_imports WHERE faculty_attendance_imports.import_id=attendance_import_id;
    PERFORM commit_faculty_attendance_import(faculty_one,tenant,attendance_import_id,version,rows);
    SELECT roster_id INTO roster_one FROM faculty_attendance_rosters WHERE institution_id=tenant AND register_number='R-'||suffix;
    IF (SELECT count(*) FROM faculty_attendance_records WHERE roster_id=roster_one) <> 1 THEN RAISE EXCEPTION 'Import lost attendance'; END IF;
    IF (SELECT linked_student_id FROM faculty_attendance_rosters WHERE roster_id=roster_one) IS NOT NULL THEN RAISE EXCEPTION 'Unregistered student linked'; END IF;
    IF EXISTS(SELECT 1 FROM students WHERE institution_id=tenant) THEN RAISE EXCEPTION 'Import created an account'; END IF;
    BEGIN
        PERFORM commit_faculty_attendance_import(faculty_one,tenant,attendance_import_id,version,rows);
        RAISE EXCEPTION 'Duplicate commit succeeded';
    EXCEPTION WHEN serialization_failure THEN NULL; END;
    BEGIN
        PERFORM mark_faculty_attendance(faculty_two,tenant,section_one,'2026-10-08',jsonb_build_object(roster_one::text,'present'));
        RAISE EXCEPTION 'Other subject edit allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        PERFORM mark_faculty_attendance(foreign_faculty,foreign_tenant,section_one,'2026-10-08',jsonb_build_object(roster_one::text,'present'));
        RAISE EXCEPTION 'Cross tenant edit allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    INSERT INTO auth.users(id,email) VALUES(monitor,monitor||'@example.invalid');
    INSERT INTO users(id,auth_user_id,email,first_name,last_name) VALUES(monitor,monitor,monitor||'@example.invalid','Monitoring','Faculty');
    INSERT INTO user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id) SELECT monitor,id,'institution',tenant,org FROM roles WHERE name='faculty';
    PERFORM manage_faculty_responsibility(admin_user,tenant,monitor,'hod','department',dept,now()-interval '1 day',NULL,true);
    PERFORM manage_faculty_responsibility(admin_user,tenant,monitor,'class_in_charge','section',section_one,now()-interval '1 day',NULL,true);
    BEGIN
        PERFORM mark_faculty_attendance(monitor,tenant,section_one,'2026-10-08',jsonb_build_object(roster_one::text,'present'));
        RAISE EXCEPTION 'Responsibilities granted teaching mutation';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    -- Even another assigned teacher cannot correct the owner's existing session.
    PERFORM create_faculty_teaching_assignment(admin_user,tenant,faculty_two,section_one,now()-interval '1 day',NULL,true);
    BEGIN
        PERFORM mark_faculty_attendance(faculty_two,tenant,section_one,'2026-10-07',jsonb_build_object(roster_one::text,'absent'));
        RAISE EXCEPTION 'Other teacher session takeover allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    PERFORM mark_faculty_attendance(faculty_one,tenant,section_one,'2026-10-07',jsonb_build_object(roster_one::text,'absent'));
    IF (SELECT status FROM faculty_attendance_records WHERE roster_id=roster_one) <> 'absent' THEN RAISE EXCEPTION 'Correction failed'; END IF;
    -- Invalid roster causes the whole new session to roll back.
    BEGIN
        PERFORM mark_faculty_attendance(faculty_one,tenant,section_one,'2026-10-09',jsonb_build_object(gen_random_uuid()::text,'present'));
        RAISE EXCEPTION 'Forged roster allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF EXISTS(SELECT 1 FROM faculty_attendance_sessions WHERE section_id=section_one AND session_date='2026-10-09') THEN RAISE EXCEPTION 'Failed marking left a session'; END IF;
    -- Registration first remains pending, then approval links and synchronizes history.
    INSERT INTO auth.users(id,email) VALUES(student_one,student_one||'@example.invalid');
    INSERT INTO users(id,auth_user_id,email,first_name,last_name) VALUES(student_one,student_one,student_one||'@example.invalid','Roster','Student');
    INSERT INTO students(student_id,user_id,institution_id,student_number,register_number,university_roll_number,email,enrollment_date,program_id,academic_year_id,approval_status)
    VALUES(student_one,student_one,tenant,'R-'||suffix,'R-'||suffix,'U-'||suffix,student_one||'@example.invalid','2026-07-01',program,year_id,'pending');
    IF (SELECT linked_student_id FROM faculty_attendance_rosters WHERE roster_id=roster_one) IS NOT NULL THEN RAISE EXCEPTION 'Pending student linked'; END IF;
    IF (SELECT roster_status FROM faculty_attendance_rosters WHERE roster_id=roster_one) <> 'PENDING_APPROVAL' THEN RAISE EXCEPTION 'Pending status lost'; END IF;
    UPDATE students SET approval_status='approved' WHERE student_id=student_one;
    IF (SELECT linked_student_id FROM faculty_attendance_rosters WHERE roster_id=roster_one) <> student_one THEN RAISE EXCEPTION 'Approved student not linked'; END IF;
    IF (SELECT status FROM student_attendance WHERE student_id=student_one AND section_id=section_one AND date='2026-10-07') <> 'absent' THEN RAISE EXCEPTION 'Historical reconciliation failed'; END IF;
    UPDATE students SET is_active=false WHERE student_id=student_one;
    IF (SELECT roster_status FROM faculty_attendance_rosters WHERE roster_id=roster_one) <> 'INACTIVE' THEN RAISE EXCEPTION 'Account status not synchronized'; END IF;
    -- Conflicting identifiers never auto merge or reassign an existing link.
    INSERT INTO faculty_attendance_rosters(institution_id,section_id,course_offering_id,semester_id,register_number,university_roll_number,student_name,created_by)
    VALUES(tenant,section_one,offering_one,semester,'OTHER-'||suffix,'CONFLICT-'||suffix,'Conflicting roster',faculty_one);
    UPDATE students SET is_active=true, university_roll_number='CONFLICT-'||suffix WHERE student_id=student_one;
    IF (SELECT reconciliation_state FROM faculty_attendance_rosters WHERE institution_id=tenant AND register_number='OTHER-'||suffix) <> 'CONFLICT' THEN RAISE EXCEPTION 'Conflict state missing'; END IF;
    IF (SELECT linked_student_id FROM faculty_attendance_rosters WHERE institution_id=tenant AND register_number='OTHER-'||suffix) IS NOT NULL THEN RAISE EXCEPTION 'Conflicting identity linked'; END IF;
    UPDATE students SET university_roll_number='CHANGED-'||suffix WHERE student_id=student_one;
    IF (SELECT reconciliation_state FROM faculty_attendance_rosters WHERE roster_id=roster_one) <> 'CONFLICT' THEN RAISE EXCEPTION 'Linked mismatch was ignored'; END IF;
    IF (SELECT linked_student_id FROM faculty_attendance_rosters WHERE roster_id=roster_one) <> student_one THEN RAISE EXCEPTION 'Historical link reassigned'; END IF;
    INSERT INTO faculty_attendance_rosters(institution_id,section_id,course_offering_id,semester_id,register_number,university_roll_number,student_name,created_by)
    VALUES(tenant,section_one,offering_one,semester,'ROLL-'||suffix,'ROLLONLY-'||suffix,'Roll matched student',faculty_one);
    SELECT roster_id INTO roster_one FROM faculty_attendance_rosters WHERE institution_id=tenant AND register_number='ROLL-'||suffix;
    PERFORM mark_faculty_attendance(faculty_one,tenant,section_one,'2026-10-08',jsonb_build_object(roster_one::text,'present'));
    INSERT INTO auth.users(id,email) VALUES(student_two,student_two||'@example.invalid');
    INSERT INTO users(id,auth_user_id,email,first_name,last_name) VALUES(student_two,student_two,student_two||'@example.invalid','Roll','Student');
    INSERT INTO students(student_id,user_id,institution_id,student_number,university_roll_number,email,enrollment_date,program_id,academic_year_id,approval_status)
    VALUES(student_two,student_two,tenant,'ROLLONLY-'||suffix,'ROLLONLY-'||suffix,student_two||'@example.invalid','2026-07-01',program,year_id,'approved');
    IF (SELECT linked_student_id FROM faculty_attendance_rosters WHERE roster_id=roster_one) <> student_two THEN RAISE EXCEPTION 'Roll-only registration did not link'; END IF;
    UPDATE students SET approval_status='approved' WHERE student_id=student_two;
    IF (SELECT count(*) FROM student_attendance WHERE student_id=student_two) <> 1 THEN RAISE EXCEPTION 'Already-linked registration duplicated history'; END IF;
    -- Failed import is all-or-nothing, including rosters/audit and status.
    rows := jsonb_build_array(jsonb_build_object('row_number',2,'raw_data','{}'::jsonb,'normalized_data',jsonb_build_object('register_number','ROLLBACK-'||suffix,'student_name','Rollback','status','present','session_date','2026-10-07'), 'validation_status','NEW','errors','[]'::jsonb));
    staged := stage_faculty_attendance_import(faculty_two,tenant,section_one,semester,'rollback.csv','csv','CSV',false,'{"valid":1}'::jsonb,rows);
    attendance_import_id := (staged->>'import_id')::uuid;
    SELECT updated_at INTO version FROM faculty_attendance_imports WHERE faculty_attendance_imports.import_id=attendance_import_id;
    BEGIN
        PERFORM commit_faculty_attendance_import(faculty_two,tenant,attendance_import_id,version,rows);
        RAISE EXCEPTION 'Conflicting session import allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF EXISTS(SELECT 1 FROM faculty_attendance_rosters WHERE institution_id=tenant AND register_number='ROLLBACK-'||suffix) THEN RAISE EXCEPTION 'Failed commit left a roster'; END IF;
    IF (SELECT status FROM faculty_attendance_imports WHERE faculty_attendance_imports.import_id=attendance_import_id) <> 'VALIDATED' THEN RAISE EXCEPTION 'Failed commit changed status'; END IF;
    IF NOT EXISTS(SELECT 1 FROM admin_audit_log WHERE institution_id=tenant AND action='attendance.session.correct') OR
       NOT EXISTS(SELECT 1 FROM admin_audit_log WHERE institution_id=tenant AND action='attendance.import.commit') OR
       NOT EXISTS(SELECT 1 FROM admin_audit_log WHERE institution_id=tenant AND action='attendance.identity.reconcile') THEN RAISE EXCEPTION 'Attendance audit missing'; END IF;
    RAISE NOTICE 'ATTENDANCE DATABASE CONTRACTS PASS';
END; $$;
ROLLBACK;
