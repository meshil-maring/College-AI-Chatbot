DO $$
DECLARE actor uuid; tenant uuid; department jsonb; program jsonb; year jsonb; term jsonb; course jsonb;
    stage jsonb; stage_two jsonb; curriculum jsonb; mapping jsonb; mapping_two jsonb; cohort jsonb; section jsonb; offering jsonb;
BEGIN
    SELECT u.id,i.institution_id INTO STRICT actor,tenant
    FROM public.user_roles ur JOIN public.roles r ON r.id=ur.role_id JOIN public.users u ON u.id=ur.user_id
    JOIN public.institutions i ON i.institution_id=ur.scope_id JOIN public.organizations o ON o.organization_id=i.organization_id
    WHERE r.name='admin' AND r.is_active AND u.status='active' AND ur.scope_type='institution'
      AND ur.scope_organization_id=i.organization_id AND i.is_active AND i.status='active' AND o.status='active' LIMIT 1;
    PERFORM set_config('request.jwt.claims','{"role":"service_role"}',true);
    PERFORM set_config('request.jwt.claim.role','service_role',true);
    department:=public.manage_academic_master_record(actor,tenant,'departments',NULL,'{"name":"Workspace rollback QA","code":"QA-WS"}');
    program:=public.manage_academic_master_record(actor,tenant,'programs',NULL,jsonb_build_object('name','QA Program','code','QA-WS','department_id',department->>'department_id','degree_type','QA','duration_years',4));
    year:=public.manage_academic_master_record(actor,tenant,'academic_years',NULL,'{"name":"QA 2090","code":"QA-2090","start_date":"2090-01-01","end_date":"2090-12-31"}');
    term:=public.manage_academic_master_record(actor,tenant,'semesters',NULL,jsonb_build_object('name','QA Term','code','QA-T1','academic_year_id',year->>'academic_year_id','semester_number',1,'start_date','2090-01-01','end_date','2090-06-30'));
    course:=public.manage_academic_master_record(actor,tenant,'courses',NULL,jsonb_build_object('name','QA Subject','code','QA-SUB','department_id',department->>'department_id','credits',3));
    stage:=public.manage_academic_structure_record(actor,tenant,'program_semesters',NULL,jsonb_build_object('program_id',program->>'program_id','name','Semester 1','code','S1','semester_number',1));
    stage_two:=public.manage_academic_structure_record(actor,tenant,'program_semesters',NULL,jsonb_build_object('program_id',program->>'program_id','name','Semester 2','code','S2','semester_number',2));
    curriculum:=public.manage_academic_structure_record(actor,tenant,'curriculum_versions',NULL,jsonb_build_object('program_id',program->>'program_id','academic_year_id',year->>'academic_year_id','name','QA Curriculum','version','1.0','total_semesters',8));
    mapping:=public.manage_academic_structure_record(actor,tenant,'curriculum_subjects',NULL,jsonb_build_object('curriculum_version_id',curriculum->>'curriculum_version_id','program_semester_id',stage->>'program_semester_id','course_id',course->>'course_id'));
    mapping_two:=public.manage_academic_structure_record(actor,tenant,'curriculum_subjects',NULL,jsonb_build_object('curriculum_version_id',curriculum->>'curriculum_version_id','program_semester_id',stage_two->>'program_semester_id','course_id',course->>'course_id'));
    curriculum:=public.manage_academic_structure_record(actor,tenant,'curriculum_versions',(curriculum->>'curriculum_version_id')::uuid,'{"status":"published"}');
    IF curriculum->>'published_at' IS NULL THEN RAISE EXCEPTION 'Missing publication timestamp'; END IF;
    cohort:=public.manage_academic_structure_record(actor,tenant,'admission_cohorts',NULL,jsonb_build_object('program_id',program->>'program_id','academic_year_id',year->>'academic_year_id','curriculum_version_id',curriculum->>'curriculum_version_id','name','QA Batch','code','QA-B','start_year',2090,'end_year',2094));
    section:=public.manage_academic_structure_record(actor,tenant,'academic_sections',NULL,jsonb_build_object('admission_cohort_id',cohort->>'admission_cohort_id','program_semester_id',stage->>'program_semester_id','semester_id',term->>'semester_id','name','Section A','code','QA-A','capacity',60));
    offering:=public.manage_academic_structure_record(actor,tenant,'academic_offerings',NULL,jsonb_build_object('academic_section_id',section->>'academic_section_id','curriculum_subject_id',mapping->>'curriculum_subject_id'));
    BEGIN
        PERFORM public.manage_academic_structure_record(actor,tenant,'curriculum_subjects',(mapping->>'curriculum_subject_id')::uuid,'{"course_type":"elective"}');
        RAISE EXCEPTION 'Published mapping changed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM public.manage_academic_structure_record(actor,tenant,'curriculum_versions',(curriculum->>'curriculum_version_id')::uuid,'{"name":"Changed"}');
        RAISE EXCEPTION 'Published version changed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM public.manage_academic_structure_record(actor,tenant,'admission_cohorts',(cohort->>'admission_cohort_id')::uuid,'{"status":"completed"}');
        RAISE EXCEPTION 'Active section allowed cohort deactivation';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM public.manage_academic_structure_record(actor,tenant,'academic_offerings',NULL,jsonb_build_object('academic_section_id',section->>'academic_section_id','curriculum_subject_id',mapping_two->>'curriculum_subject_id'));
        RAISE EXCEPTION 'Mismatched program semester accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        PERFORM public.manage_academic_structure_record(actor,tenant,'academic_sections',(section->>'academic_section_id')::uuid,'{"code":"CHANGED"}');
        RAISE EXCEPTION 'Immutable section code changed';
    EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
    BEGIN
        PERFORM public.manage_academic_master_record(actor,tenant,'courses',(course->>'course_id')::uuid,'{"is_active":false}');
        RAISE EXCEPTION 'Active curriculum allowed subject deactivation';
    EXCEPTION WHEN check_violation THEN NULL; END;
    IF has_table_privilege('authenticated','public.admission_cohorts','SELECT') OR
       has_table_privilege('service_role','public.admission_cohorts','INSERT') OR
       has_function_privilege('authenticated','public.manage_academic_structure_record(uuid,uuid,text,uuid,jsonb)','EXECUTE') THEN
        RAISE EXCEPTION 'Unsafe table or writer ACL';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM public.admin_audit_log WHERE institution_id=tenant AND record_id=offering->>'academic_offering_id') THEN
        RAISE EXCEPTION 'Missing atomic audit';
    END IF;
END;
$$;
SELECT 'Academic migrations, relationship writes, publication freeze, parent guards, audit and ACL checks passed; all changes rolled back.' AS result;
