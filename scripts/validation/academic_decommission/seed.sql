-- Disposable-only identities and academic state for the destructive contract.
SET request.jwt.claim.role = 'service_role';
CREATE SCHEMA academic_decommission_fixture;
CREATE TABLE academic_decommission_fixture.ids(name text PRIMARY KEY,value uuid);
DO $$
DECLARE tenant uuid := gen_random_uuid(); org uuid; admin uuid; actor uuid; auth_id uuid; role text;
    department uuid; program uuid; year_id uuid; term uuid; batch uuid; student uuid;
    subject uuid; curriculum uuid; member uuid; package_id uuid; class_id uuid; registration uuid; placement uuid; item jsonb;
BEGIN
    SELECT organization_id INTO org FROM public.organizations WHERE organization_code='COLLEGE-AI-PLATFORM';
    INSERT INTO public.institutions(institution_id,organization_id,name,code,status)
    VALUES(tenant,org,'Disposable decommission contract','DC-' || tenant::text,'active');
    INSERT INTO academic_decommission_fixture.ids VALUES('tenant',tenant);
    FOREACH role IN ARRAY ARRAY['admin','staff','student'] LOOP
        actor := gen_random_uuid(); auth_id := gen_random_uuid();
        INSERT INTO auth.users(id,email) VALUES(auth_id,actor::text || '@example.invalid');
        INSERT INTO public.users(id,auth_user_id,email,first_name,last_name)
        VALUES(actor,auth_id,actor::text || '@example.invalid','Preserved',role);
        INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
        SELECT actor,r.id,'institution',tenant,org FROM public.roles r WHERE r.name=role;
        INSERT INTO academic_decommission_fixture.ids VALUES(role,actor);
        IF role='admin' THEN admin:=actor; END IF;
    END LOOP;
    PERFORM public.phase81_manage_staff_permission_grants(admin,tenant,
        (SELECT value FROM academic_decommission_fixture.ids WHERE name='staff'),ARRAY['documents.read','attendance.read'],true);
    INSERT INTO public.departments(institution_id,name,code)
    VALUES(tenant,'Retired Department','RET') RETURNING department_id INTO department;
    INSERT INTO public.programs(department_id,name,code,degree_type,duration_years)
    VALUES(department,'Retired Program','RET','B.Tech',4) RETURNING program_id INTO program;
    INSERT INTO public.academic_years(institution_id,name,code,start_date,end_date)
    VALUES(tenant,'Retired Year','RET',current_date-30,current_date+200) RETURNING academic_year_id INTO year_id;
    INSERT INTO public.semesters(academic_year_id,name,code,semester_number,start_date,end_date)
    VALUES(year_id,'Retired Term','RET',1,current_date-1,current_date+90) RETURNING semester_id INTO term;
    INSERT INTO public.academic_batches(institution_id,program_id,start_year,end_year)
    VALUES(tenant,program,extract(year FROM current_date)::integer,extract(year FROM current_date)::integer+4)
    RETURNING batch_id INTO batch;
    INSERT INTO public.students(user_id,institution_id,student_number,register_number,university_roll_number,email,
        program_id,academic_year_id,enrollment_date,approval_status)
    SELECT value,tenant,'DC-PRESERVED','DC-PRESERVED','DC-ROLL',value::text || '@example.invalid',program,year_id,current_date,'approved'
    FROM academic_decommission_fixture.ids WHERE name='student' RETURNING student_id INTO student;
    INSERT INTO academic_decommission_fixture.ids VALUES('profile',student),('program',program);
    INSERT INTO public.courses(department_id,name,code)
    VALUES(department,'Retired Subject','RET') RETURNING course_id INTO subject;
    item := public.academic_package_command(admin,tenant,'save_curriculum',jsonb_build_object(
        'program_id',program,'name','Retired Plan','code','RET','version',1));
    curriculum:=(item->>'curriculum_id')::uuid;
    item := public.academic_package_command(admin,tenant,'set_curriculum_subject',jsonb_build_object(
        'curriculum_id',curriculum,'course_id',subject,'study_semester',1,'course_type','core','is_core',true));
    member:=(item->>'curriculum_subject_id')::uuid;
    item := public.academic_package_command(admin,tenant,'save_package',jsonb_build_object(
        'curriculum_id',curriculum,'study_semester',1,'name','Retired Package','code','RET','curriculum_subject_ids',jsonb_build_array(member)));
    package_id:=(item->>'package_id')::uuid;
    item := public.academic_package_command(admin,tenant,'save_class',jsonb_build_object(
        'program_id',program,'batch_id',batch,'semester_id',term,'study_semester',1,'section_code','RET',
        'curriculum_id',curriculum,'student_choice_enabled',false));
    class_id:=(item->>'class_id')::uuid;
    PERFORM public.academic_package_command(admin,tenant,'set_class_package',jsonb_build_object(
        'class_id',class_id,'package_id',package_id,'enabled',true));
    PERFORM public.academic_package_command(admin,tenant,'prepare_class_teaching',jsonb_build_object('class_id',class_id));
    INSERT INTO public.student_registrations(institution_id,program_id,academic_year_id,semester_id,section_code,batch_id,
        batch_start_year,batch_end_year,register_number,university_roll_number,student_name,email,created_by)
    SELECT tenant,program,year_id,term,'RET',batch,b.start_year,b.end_year,'DC-PRESERVED','DC-ROLL','Preserved student',
        (SELECT value::text || '@example.invalid' FROM academic_decommission_fixture.ids WHERE name='student'),admin
    FROM public.academic_batches b WHERE b.batch_id=batch RETURNING registration_id INTO registration;
    item := public.academic_package_command(admin,tenant,'place_student',jsonb_build_object('class_id',class_id,'registration_id',registration));
    placement:=(item->>'placement_id')::uuid;
    PERFORM public.academic_package_command(admin,tenant,'assign_package',jsonb_build_object('placement_id',placement,'package_id',package_id));
END;
$$;
SELECT 'PASS: real account identity, grants, masters and complete package membership seeded' AS result;
