-- Run only against a disposable, fully migrated Supabase database:
-- psql <local database URL> -v ON_ERROR_STOP=1 -f scripts/validation/faculty_responsibilities_database.sql
-- Fixtures and audit events are rolled back. This script has NOT been run in
-- an environment without a PostgreSQL/Supabase runtime.
BEGIN;
SET LOCAL search_path = public, extensions;
SELECT set_config('request.jwt.claim.role', 'service_role', true);

DO $$
DECLARE
    org uuid := gen_random_uuid(); tenant uuid := gen_random_uuid(); foreign_tenant uuid := gen_random_uuid();
    admin_user uuid := gen_random_uuid(); faculty_one uuid := gen_random_uuid(); faculty_two uuid := gen_random_uuid();
    foreign_faculty uuid := gen_random_uuid(); dept uuid := gen_random_uuid(); math_dept uuid := gen_random_uuid(); foreign_dept uuid := gen_random_uuid();
    program uuid := gen_random_uuid(); year_id uuid := gen_random_uuid(); semester uuid := gen_random_uuid();
    course_one uuid := gen_random_uuid(); course_two uuid := gen_random_uuid(); offering_one uuid := gen_random_uuid(); offering_two uuid := gen_random_uuid();
    section_one uuid := gen_random_uuid(); section_two uuid := gen_random_uuid(); hod_id uuid; class_id uuid; teaching_id uuid; scoped_id uuid;
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

    hod_id := manage_faculty_responsibility(admin_user,tenant,faculty_one,'hod','department',dept,
        '2026-07-01T00:00:00Z','2027-07-01T00:00:00Z',true);
    class_id := manage_faculty_responsibility(admin_user,tenant,faculty_one,'class_in_charge','section',section_one,
        '2026-07-01T00:00:00Z','2027-07-01T00:00:00Z',true);
    teaching_id := create_faculty_teaching_assignment(admin_user,tenant,faculty_one,section_one,
        '2026-07-01T00:00:00Z','2027-07-01T00:00:00Z',true);
    scoped_id := manage_scoped_faculty_teaching_assignment(
        faculty_one, tenant, NULL, faculty_two, section_one,
        '2026-07-01T00:00:00Z', '2027-07-01T00:00:00Z', true, false
    );
    PERFORM manage_scoped_faculty_teaching_assignment(
        faculty_one, tenant, scoped_id, NULL, section_one,
        '2026-07-01T00:00:00Z', '2027-07-01T00:00:00Z', true, false
    );
    IF (SELECT count(*) FROM admin_audit_log
        WHERE actor_user_id=faculty_one AND record_id=scoped_id::text
          AND action IN ('faculty.assignment.assign','faculty.assignment.update')) <> 2
    THEN RAISE EXCEPTION 'Scoped assignment create/update was not atomically audited'; END IF;
    BEGIN
        PERFORM manage_scoped_faculty_teaching_assignment(
            faculty_one, tenant, NULL, faculty_two, section_two,
            '2026-07-01T00:00:00Z', '2027-07-01T00:00:00Z', true, false
        );
        RAISE EXCEPTION 'Department-scoped HOD managed another department';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF (SELECT count(*) FROM faculty_responsibilities WHERE faculty_user_id=faculty_one AND revoked_at IS NULL) <> 2
       OR NOT EXISTS(SELECT 1 FROM faculty_section_assignments WHERE assignment_id=teaching_id AND start_at='2026-07-01T00:00:00Z')
    THEN RAISE EXCEPTION 'Multiple responsibilities and teaching did not coexist'; END IF;

    BEGIN
        PERFORM manage_faculty_responsibility(admin_user,tenant,faculty_two,'hod','department',dept,'2026-07-01T00:00:00Z','2027-07-01T00:00:00Z',true);
        RAISE EXCEPTION 'Overlapping HOD was allowed';
    EXCEPTION WHEN exclusion_violation THEN NULL; END;
    BEGIN
        PERFORM manage_faculty_responsibility(admin_user,tenant,faculty_two,'class_in_charge','section',section_two,'2026-07-01T00:00:00Z','2027-07-01T00:00:00Z',true);
        RAISE EXCEPTION 'Co-Class In-Charge via another subject anchor was allowed';
    EXCEPTION WHEN exclusion_violation THEN NULL; END;
    -- Adjacent successor intervals are permitted.
    PERFORM manage_faculty_responsibility(admin_user,tenant,faculty_two,'hod','department',dept,'2027-07-01T00:00:00Z','2028-07-01T00:00:00Z',true);
    BEGIN
        PERFORM manage_faculty_responsibility(admin_user,tenant,foreign_faculty,'hod','department',dept,'2026-07-01T00:00:00Z',NULL,true);
        RAISE EXCEPTION 'Cross-tenant faculty was allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM manage_faculty_responsibility(admin_user,tenant,faculty_one,'hod','department',foreign_dept,'2026-07-01T00:00:00Z',NULL,true);
        RAISE EXCEPTION 'Cross-tenant department was allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM manage_faculty_responsibility(admin_user,tenant,faculty_one,'forged','department',dept,'2026-07-01T00:00:00Z',NULL,true);
        RAISE EXCEPTION 'Unknown responsibility was allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM manage_faculty_responsibility(faculty_one,tenant,faculty_one,'hod','department',dept,'2026-07-01T00:00:00Z',NULL,true);
        RAISE EXCEPTION 'Faculty self-assignment was allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        PERFORM phase81_manage_faculty_section_assignment(admin_user,tenant,admin_user,section_one,false);
        RAISE EXCEPTION 'Admin self-teaching assignment was allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        PERFORM update_faculty_teaching_validity(admin_user,tenant,teaching_id,'2027-07-01T00:00:00Z','2026-07-01T00:00:00Z',true);
        RAISE EXCEPTION 'Reversed validity interval was allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    PERFORM update_faculty_teaching_validity(admin_user,tenant,teaching_id,'2026-07-01T00:00:00Z','2027-07-01T00:00:00Z',false);
    IF NOT EXISTS(SELECT 1 FROM faculty_section_assignments WHERE assignment_id=teaching_id AND NOT is_active)
    THEN RAISE EXCEPTION 'Teaching state update lost the identifier'; END IF;

    UPDATE users SET status='inactive' WHERE id=faculty_one;
    PERFORM manage_faculty_responsibility(admin_user,tenant,faculty_one,'hod','department',dept,
        '2026-07-01T00:00:00Z','2027-07-01T00:00:00Z',false,hod_id,true);
    IF NOT EXISTS(SELECT 1 FROM faculty_responsibilities WHERE responsibility_id=hod_id AND revoked_at IS NOT NULL AND revoked_by=admin_user)
    THEN RAISE EXCEPTION 'Revocation of inactive faculty did not preserve history'; END IF;
    SELECT count(*) INTO audit_count FROM admin_audit_log WHERE actor_user_id=admin_user AND institution_id=tenant;
    IF audit_count < 6 THEN RAISE EXCEPTION 'Assignment changes were not atomically audited'; END IF;
    IF has_function_privilege('authenticated','public.manage_faculty_responsibility(uuid,uuid,uuid,text,text,uuid,timestamptz,timestamptz,boolean,uuid,boolean,uuid)','EXECUTE')
       OR has_table_privilege('authenticated','public.faculty_responsibilities','SELECT')
       OR has_table_privilege('service_role','public.faculty_responsibilities','UPDATE')
       OR has_function_privilege('authenticated','public.manage_scoped_faculty_teaching_assignment(uuid,uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean,boolean)','EXECUTE')
    THEN RAISE EXCEPTION 'Database privilege boundary is too broad'; END IF;
END;
$$;
ROLLBACK;
