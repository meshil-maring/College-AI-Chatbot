BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
CREATE FUNCTION workspace_fixture.reject(label text, command text, expected_state text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE rejected boolean:=false; audit_before bigint;
BEGIN
    SELECT count(*) INTO audit_before FROM public.admin_audit_log;
    BEGIN
        EXECUTE command;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE<>expected_state THEN
            RAISE EXCEPTION 'FAILED: %, expected %, got %: %',label,expected_state,SQLSTATE,SQLERRM;
        END IF;
        rejected:=true;
    END;
    PERFORM workspace_fixture.assert_true(label,rejected);
    IF (SELECT count(*) FROM public.admin_audit_log)<>audit_before THEN
        RAISE EXCEPTION 'FAILED: rejected write changed audit history: %',label;
    END IF;
END;
$$;
SELECT workspace_fixture.reject('Department codes reject case and whitespace duplicates',
    $$SELECT workspace_fixture.save('bad','departments','{"name":"Duplicate CSE","code":" cSe "}')$$,'23505');
SELECT workspace_fixture.reject('Study semester numbers cannot repeat within a program',
    format($q$SELECT workspace_fixture.save('bad','program_semesters',%L::jsonb)$q$,
        jsonb_build_object('program_id',workspace_fixture.id('program'),'name','Duplicate stage','code','S1-DUP','semester_number',1)),
    '23505');
SELECT workspace_fixture.reject('Curriculum version codes reject normalized duplicates',
    format($q$SELECT workspace_fixture.save('bad','curriculum_versions',%L::jsonb)$q$,
        jsonb_build_object('program_id',workspace_fixture.id('program'),'academic_year_id',workspace_fixture.id('year'),
            'name','Duplicate regulation','version',' r2026 ','total_semesters',8)),'23505');
SELECT workspace_fixture.reject('An offering cannot repeat the same section and subject',
    format($q$SELECT workspace_fixture.save('bad','academic_offerings',%L::jsonb)$q$,
        jsonb_build_object('academic_section_id',workspace_fixture.id('section'),
            'curriculum_subject_id',workspace_fixture.id('mapping'))),'23505');
SELECT workspace_fixture.reject('Semester dates cannot fall outside the academic year',
    format($q$SELECT workspace_fixture.save('bad','semesters',%L::jsonb)$q$,
        jsonb_build_object('academic_year_id',workspace_fixture.id('year'),'name','Invalid term','code','BAD',
            'semester_number',3,'start_date','2027-06-01','end_date','2027-07-31')),'23514');
SELECT workspace_fixture.reject('Active academic years cannot overlap',
    $$SELECT workspace_fixture.save('bad','academic_years',
        '{"name":"Overlapping year","code":"OVERLAP","start_date":"2027-01-01","end_date":"2027-12-31"}')$$,'23P01');
SELECT workspace_fixture.reject('Negative section capacity is rejected',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'academic_sections',%L,'{"capacity":-1}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('section')),'23514');
SELECT workspace_fixture.reject('Empty curricula cannot be published',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'curriculum_versions',%L,'{"status":"published"}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('draft')),'23514');
SELECT workspace_fixture.reject('Published curriculum metadata cannot be edited',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'curriculum_versions',%L,'{"name":"Tampered"}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('curriculum')),'23514');
SELECT workspace_fixture.reject('Published subject mappings cannot be edited',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'curriculum_subjects',%L,'{"is_required":false}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('mapping')),'23514');
SELECT workspace_fixture.reject('A cohort cannot select an unpublished draft',
    format($q$SELECT workspace_fixture.save('bad','admission_cohorts',%L::jsonb)$q$,
        jsonb_build_object('program_id',workspace_fixture.id('program'),'curriculum_version_id',workspace_fixture.id('draft'),
            'academic_year_id',workspace_fixture.id('year'),'name','Invalid cohort','code','BAD','start_year',2026,'end_year',2030)),
    '23514');
SELECT workspace_fixture.reject('A section cannot select another program study semester',
    format($q$SELECT workspace_fixture.save('bad','academic_sections',%L::jsonb)$q$,
        jsonb_build_object('admission_cohort_id',workspace_fixture.id('cohort'),
            'program_semester_id',workspace_fixture.id('other_stage'),'semester_id',workspace_fixture.id('term'),
            'name','Mismatched section','code','WRONG')),'23514');
SELECT workspace_fixture.reject('Offering must use the section study semester',
    format($q$SELECT workspace_fixture.save('bad','academic_offerings',%L::jsonb)$q$,
        jsonb_build_object('academic_section_id',workspace_fixture.id('section'),
            'curriculum_subject_id',workspace_fixture.id('next_mapping'))),'23514');
SELECT workspace_fixture.reject('Cross-college parent links are rejected',
    format($q$SELECT workspace_fixture.save('bad','programs',%L::jsonb)$q$,
        jsonb_build_object('department_id',workspace_fixture.id('foreign_department'),
            'name','Cross tenant','code','BAD','degree_type','B.Tech','duration_years',4)),'P0002');
SELECT workspace_fixture.reject('Administrators cannot write to another college',
    format($q$SELECT public.manage_academic_master_record(%L,%L,'departments',NULL,'{"name":"Bad","code":"BAD"}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('foreign_tenant')),'42501');
SELECT workspace_fixture.reject('Foreign records cannot be updated from another college',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'academic_sections',%L,'{"capacity":5}')$q$,
        workspace_fixture.id('foreign_admin'),workspace_fixture.id('foreign_tenant'),workspace_fixture.id('section')),'P0002');
SELECT workspace_fixture.reject('Staff cannot perform institution administrator writes',
    format($q$SELECT public.manage_academic_master_record(%L,%L,'departments',NULL,'{"name":"Bad","code":"BAD"}')$q$,
        workspace_fixture.id('staff'),workspace_fixture.id('tenant')),'42501');
SELECT workspace_fixture.reject('Students cannot perform institution administrator writes',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'academic_sections',%L,'{"capacity":5}')$q$,
        workspace_fixture.id('student'),workspace_fixture.id('tenant'),workspace_fixture.id('section')),'42501');
SELECT workspace_fixture.reject('Cohort curriculum assignment cannot be replaced',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'admission_cohorts',%L,%L::jsonb)$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('cohort'),
        jsonb_build_object('curriculum_version_id',workspace_fixture.id('draft'))),'22023');
SELECT workspace_fixture.assert_true('Service role cannot bypass writers with direct table mutations',
    NOT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public'
        AND table_name IN ('departments','programs','courses','academic_years','semesters','program_courses',
            'course_offerings','sections','program_semesters','curriculum_versions','curriculum_subjects',
            'admission_cohorts','academic_sections','academic_offerings')
        AND has_table_privilege('service_role',format('%I.%I',table_schema,table_name),'INSERT,UPDATE,DELETE')));
SELECT workspace_fixture.assert_true('Browser roles cannot execute either academic writer',
    NOT has_function_privilege('authenticated','public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb)','EXECUTE')
    AND NOT has_function_privilege('anon','public.manage_academic_structure_record(uuid,uuid,text,uuid,jsonb)','EXECUTE'));
SELECT workspace_fixture.reject('Anonymous SQL session cannot call the structure writer',
    $$SET LOCAL ROLE anon; SELECT public.manage_academic_structure_record(NULL,NULL,'academic_sections',NULL,'{}')$$,'42501');
SELECT workspace_fixture.reject('Authenticated browser SQL session cannot call the master writer',
    $$SET LOCAL ROLE authenticated; SELECT public.manage_academic_master_record(NULL,NULL,'departments',NULL,'{}')$$,'42501');
COMMIT;
SELECT 'PASS: duplicate, relationship, date, publication and permission rejections are atomic';
