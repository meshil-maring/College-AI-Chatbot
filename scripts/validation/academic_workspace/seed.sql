-- Fictional institutions and accounts; executed only by the owned local runner.
BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
CREATE SCHEMA workspace_fixture;
CREATE TABLE workspace_fixture.ids (name text PRIMARY KEY, value uuid NOT NULL);
CREATE FUNCTION workspace_fixture.id(key text) RETURNS uuid LANGUAGE sql STABLE
AS $$ SELECT value FROM workspace_fixture.ids WHERE name=key $$;
CREATE FUNCTION workspace_fixture.save(key text, entity text, payload jsonb)
RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE item jsonb; identifier uuid; column_name text;
BEGIN
    IF entity IN ('program_semesters','curriculum_versions','curriculum_subjects',
                  'admission_cohorts','academic_sections','academic_offerings') THEN
        item:=public.manage_academic_structure_record(workspace_fixture.id('admin'),
            workspace_fixture.id('tenant'),entity,NULL,payload);
    ELSE
        item:=public.manage_academic_master_record(workspace_fixture.id('admin'),
            workspace_fixture.id('tenant'),entity,NULL,payload);
    END IF;
    column_name:=regexp_replace(entity,'s$','')||'_id';
    identifier:=(item->>column_name)::uuid;
    INSERT INTO workspace_fixture.ids VALUES(key,identifier);
    RETURN identifier;
END;
$$;
DO $$
DECLARE org uuid; tenant uuid; actor uuid; auth_id uuid; label text; role_name text;
BEGIN
    SELECT organization_id INTO STRICT org FROM public.organizations
    WHERE organization_code='COLLEGE-AI-PLATFORM';
    FOREACH label IN ARRAY ARRAY['tenant','foreign_tenant'] LOOP
        tenant:=gen_random_uuid();
        INSERT INTO public.institutions(institution_id,organization_id,name,code,status)
        VALUES(tenant,org,CASE label WHEN 'tenant' THEN 'Kaveri Institute of Technology (Fictional)'
            ELSE 'Malabar Arts and Science College (Fictional)' END,label||'-WORKSPACE-TEST','active');
        INSERT INTO workspace_fixture.ids VALUES(label,tenant);
        FOREACH role_name IN ARRAY ARRAY['admin','staff','student'] LOOP
            actor:=gen_random_uuid(); auth_id:=gen_random_uuid();
            INSERT INTO auth.users(id,email) VALUES(auth_id,label||'.'||role_name||'@example.invalid');
            INSERT INTO public.users(id,auth_user_id,email,first_name,last_name)
            VALUES(actor,auth_id,label||'.'||role_name||'@example.invalid','Fictional',role_name);
            INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
            SELECT actor,id,'institution',tenant,org FROM public.roles WHERE name=role_name;
            INSERT INTO workspace_fixture.ids VALUES(
                CASE WHEN label='tenant' THEN role_name ELSE 'foreign_'||role_name END,actor);
        END LOOP;
    END LOOP;
END;
$$;
SELECT workspace_fixture.save('department','departments',
    '{"name":"Computer Science and Engineering","code":"CSE"}');
SELECT workspace_fixture.save('other_department','departments',
    '{"name":"Electronics and Communication","code":"ECE"}');
SELECT workspace_fixture.save('program','programs',jsonb_build_object(
    'department_id',workspace_fixture.id('department'),'name','B.Tech Computer Science',
    'code','BTECH-CSE','degree_type','B.Tech','duration_years',4,'total_credits',160));
SELECT workspace_fixture.save('other_program','programs',jsonb_build_object(
    'department_id',workspace_fixture.id('other_department'),'name','B.Tech Electronics',
    'code','BTECH-ECE','degree_type','B.Tech','duration_years',4));
SELECT workspace_fixture.save('year','academic_years',
    '{"name":"Academic Year 2026-2027","code":"AY2026","start_date":"2026-06-01",
      "end_date":"2027-05-31","is_current":true}');
SELECT workspace_fixture.save('term','semesters',jsonb_build_object(
    'academic_year_id',workspace_fixture.id('year'),'name','Odd Term 2026','code','ODD26',
    'semester_number',1,'start_date','2026-06-01','end_date','2026-11-30','is_current',true));
SELECT workspace_fixture.save('next_term','semesters',jsonb_build_object(
    'academic_year_id',workspace_fixture.id('year'),'name','Even Term 2027','code','EVEN27',
    'semester_number',2,'start_date','2026-12-01','end_date','2027-05-31'));
SELECT workspace_fixture.save('course','courses',jsonb_build_object(
    'department_id',workspace_fixture.id('department'),'name','Programming Fundamentals',
    'code','CS101','credits',4,'lecture_hours',3,'tutorial_hours',1,'practical_hours',2));
SELECT workspace_fixture.save('next_course','courses',jsonb_build_object(
    'department_id',workspace_fixture.id('department'),'name','Data Structures',
    'code','CS201','credits',4));
SELECT workspace_fixture.save('unmapped_course','courses',jsonb_build_object(
    'department_id',workspace_fixture.id('other_department'),'name','Digital Electronics',
    'code','EC101','credits',3));
SELECT workspace_fixture.save('program_course','program_courses',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'course_id',workspace_fixture.id('course'),
    'semester_id',workspace_fixture.id('term'),'course_type','core'));
SELECT workspace_fixture.save('legacy_offering','course_offerings',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'course_id',workspace_fixture.id('course'),
    'academic_year_id',workspace_fixture.id('year'),'semester_id',workspace_fixture.id('term'),'capacity',60));
SELECT workspace_fixture.save('legacy_section','sections',jsonb_build_object(
    'course_offering_id',workspace_fixture.id('legacy_offering'),'name','Programming Lab A','code','LAB-A','capacity',30));
SELECT workspace_fixture.save('stage','program_semesters',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'name','Semester 1','code','S1','semester_number',1));
SELECT workspace_fixture.save('next_stage','program_semesters',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'name','Semester 2','code','S2','semester_number',2));
SELECT workspace_fixture.save('other_stage','program_semesters',jsonb_build_object(
    'program_id',workspace_fixture.id('other_program'),'name','Semester 1','code','S1','semester_number',1));
SELECT workspace_fixture.save('curriculum','curriculum_versions',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'academic_year_id',workspace_fixture.id('year'),
    'name','CSE Regulation 2026','version','R2026','total_semesters',8));
SELECT workspace_fixture.save('draft','curriculum_versions',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'academic_year_id',workspace_fixture.id('year'),
    'name','CSE Draft Regulation 2027','version','R2027','total_semesters',8));
SELECT workspace_fixture.save('mapping','curriculum_subjects',jsonb_build_object(
    'curriculum_version_id',workspace_fixture.id('curriculum'),'program_semester_id',workspace_fixture.id('stage'),
    'course_id',workspace_fixture.id('course'),'course_type','core'));
SELECT workspace_fixture.save('next_mapping','curriculum_subjects',jsonb_build_object(
    'curriculum_version_id',workspace_fixture.id('curriculum'),'program_semester_id',workspace_fixture.id('next_stage'),
    'course_id',workspace_fixture.id('next_course'),'course_type','core'));
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'curriculum_versions',workspace_fixture.id('curriculum'),'{"status":"published"}');
SELECT workspace_fixture.save('cohort','admission_cohorts',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'curriculum_version_id',workspace_fixture.id('curriculum'),
    'academic_year_id',workspace_fixture.id('year'),'name','CSE Admission Batch 2026-2030',
    'code','CSE-2026','start_year',2026,'end_year',2030,'expected_count',60));
SELECT workspace_fixture.save('section','academic_sections',jsonb_build_object(
    'admission_cohort_id',workspace_fixture.id('cohort'),'program_semester_id',workspace_fixture.id('stage'),
    'semester_id',workspace_fixture.id('term'),'name','CSE 2026 Section A','code','CSE26-A','capacity',30));
SELECT workspace_fixture.save('offering','academic_offerings',jsonb_build_object(
    'academic_section_id',workspace_fixture.id('section'),'curriculum_subject_id',workspace_fixture.id('mapping'),
    'capacity',30));
DO $$
DECLARE result jsonb;
BEGIN
    result:=public.manage_academic_master_record(workspace_fixture.id('foreign_admin'),
        workspace_fixture.id('foreign_tenant'),'departments',NULL,
        '{"name":"Computer Science","code":"CSE"}');
    INSERT INTO workspace_fixture.ids VALUES('foreign_department',(result->>'department_id')::uuid);
END;
$$;
COMMIT;
SELECT 'PASS: two fictional colleges, six accounts and all fourteen academic entities seeded through real writers';
