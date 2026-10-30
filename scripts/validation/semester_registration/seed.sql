BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
SELECT workspace_fixture.save('registration_stage','program_semesters',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'name','Semester 3','code','S3','semester_number',3));
DO $$
DECLARE labels text[]:=ARRAY['Data Structures and Algorithms','Object-Oriented Programming',
    'Digital Logic Design','Discrete Mathematics','Computer Organization and Architecture',
    'Database Management Systems','Data Structures / OOP Laboratory','Digital Logic Design Laboratory'];
    idx integer; course_id uuid; mapping_id uuid; group_row jsonb; student_user_id uuid; auth_id uuid; tenant uuid;
BEGIN
    FOR idx IN 1..8 LOOP
        course_id:=workspace_fixture.save('reg_course_'||idx,'courses',jsonb_build_object(
            'department_id',workspace_fixture.id('department'),'name',labels[idx],'code','REG'||idx,'credits',3));
        mapping_id:=workspace_fixture.save('reg_mapping_'||idx,'curriculum_subjects',jsonb_build_object(
            'curriculum_version_id',workspace_fixture.id('draft'),'program_semester_id',workspace_fixture.id('registration_stage'),
            'course_id',course_id,'is_required',idx<=2,'course_type',CASE WHEN idx<=2 THEN 'core' ELSE 'elective' END));
    END LOOP;
    group_row:=public.manage_curriculum_choice_group(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),NULL,
        jsonb_build_object('name','Semester 3 options','curriculum_version_id',workspace_fixture.id('draft'),
            'program_semester_id',workspace_fixture.id('registration_stage'),'options',jsonb_build_array(
                jsonb_build_object('name','Option 1','curriculum_subject_ids',jsonb_build_array(
                    workspace_fixture.id('reg_mapping_3'),workspace_fixture.id('reg_mapping_4'),workspace_fixture.id('reg_mapping_5'))),
                jsonb_build_object('name','Option 2','curriculum_subject_ids',jsonb_build_array(
                    workspace_fixture.id('reg_mapping_6'),workspace_fixture.id('reg_mapping_7'),workspace_fixture.id('reg_mapping_8'))))));
    INSERT INTO workspace_fixture.ids VALUES('reg_group',(group_row->>'choice_group_id')::uuid);
    INSERT INTO workspace_fixture.ids SELECT 'reg_option_'||right(name,1),choice_option_id
        FROM public.curriculum_choice_options WHERE choice_group_id=(group_row->>'choice_group_id')::uuid;
    FOR idx IN 1..4 LOOP
        tenant:=workspace_fixture.id(CASE WHEN idx=4 THEN 'foreign_tenant' ELSE 'tenant' END);
        IF idx IN (1,4) THEN
            student_user_id:=workspace_fixture.id(CASE WHEN idx=4 THEN 'foreign_student' ELSE 'student' END);
        ELSE
            auth_id:=gen_random_uuid(); student_user_id:=gen_random_uuid();
            INSERT INTO auth.users(id,email) VALUES(auth_id,'reg-student-'||idx||'@example.invalid');
            INSERT INTO public.users(id,auth_user_id,email,first_name,last_name,status)
            VALUES(student_user_id,auth_id,'reg-student-'||idx||'@example.invalid','Test','Student','active');
            INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
            SELECT student_user_id,r.id,'institution',tenant,i.organization_id FROM public.roles r
            JOIN public.institutions i ON i.institution_id=tenant WHERE r.name='student';
        END IF;
        INSERT INTO public.students(user_id,institution_id,student_number,email,enrollment_date,status,approval_status)
        VALUES(student_user_id,tenant,'REG-STUDENT-'||idx,'reg-profile-'||idx||'@example.invalid',current_date,'active','approved');
        INSERT INTO workspace_fixture.ids SELECT 'reg_student_'||idx,student_id FROM public.students WHERE public.students.user_id=student_user_id;
        INSERT INTO workspace_fixture.ids VALUES('reg_user_'||idx,student_user_id);
    END LOOP;
END;
$$;
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'curriculum_versions',workspace_fixture.id('draft'),'{"status":"published"}');
SELECT workspace_fixture.save('reg_cohort','admission_cohorts',jsonb_build_object(
    'program_id',workspace_fixture.id('program'),'academic_year_id',workspace_fixture.id('year'),
    'curriculum_version_id',workspace_fixture.id('draft'),'name','CSE Registration Batch','code','REG-BATCH',
    'start_year',2026,'end_year',2030));
SELECT workspace_fixture.save('reg_section','academic_sections',jsonb_build_object(
    'admission_cohort_id',workspace_fixture.id('reg_cohort'),'program_semester_id',workspace_fixture.id('registration_stage'),
    'semester_id',workspace_fixture.id('next_term'),'name','Registration Section A','code','REG-A','capacity',3));
DO $$
DECLARE idx integer; result jsonb;
BEGIN
    FOR idx IN 1..8 LOOP
        PERFORM workspace_fixture.save('reg_offering_'||idx,'academic_offerings',jsonb_build_object(
            'academic_section_id',workspace_fixture.id('reg_section'),'curriculum_subject_id',workspace_fixture.id('reg_mapping_'||idx),
            'capacity',CASE WHEN idx>=6 THEN 1 ELSE 3 END));
    END LOOP;
    FOR idx IN 1..3 LOOP
        result:=public.assign_student_semester(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
            workspace_fixture.id('reg_student_'||idx),workspace_fixture.id('reg_section'));
        INSERT INTO workspace_fixture.ids VALUES('reg_assignment_'||idx,(result->>'semester_registration_id')::uuid);
    END LOOP;
END;
$$;
COMMIT;
SELECT 'PASS: eight subjects, two complete options, four approved students and three assignments';
