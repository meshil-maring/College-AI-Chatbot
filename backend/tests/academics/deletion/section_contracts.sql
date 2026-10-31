BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
DO $$
DECLARE
    actor uuid := workspace_fixture.id('admin'); tenant uuid := workspace_fixture.id('tenant');
    item jsonb; deleted jsonb; student uuid; active boolean; state text; role_name text; audits bigint;
    users_before jsonb; students_before jsonb;
BEGIN
    SELECT jsonb_agg(to_jsonb(u) ORDER BY u.id) INTO users_before FROM public.users u;
    FOREACH active IN ARRAY ARRAY[true, false] LOOP
        item := public.manage_academic_structure_record(actor, tenant, 'academic_sections', NULL,
            jsonb_build_object('name', 'Unused section', 'code', 'DELETE-'||active,
                'admission_cohort_id', workspace_fixture.id('cohort'), 'program_semester_id', workspace_fixture.id('stage'),
                'semester_id', workspace_fixture.id('term'), 'is_active', active));
        SELECT count(*) INTO audits FROM public.admin_audit_log;
        deleted := public.delete_unused_academic_calendar_record(actor, tenant, 'academic_sections', (item->>'academic_section_id')::uuid);
        IF deleted <> item OR EXISTS(SELECT 1 FROM public.academic_sections WHERE academic_section_id=(item->>'academic_section_id')::uuid)
            OR (SELECT count(*) FROM public.admin_audit_log) <> audits+1 THEN
            RAISE EXCEPTION 'Section deletion or audit failed';
        END IF;
        item := public.manage_academic_structure_record(actor, tenant, 'academic_sections', NULL,
            jsonb_build_object('name', 'Offering-linked section', 'code', 'LINK-O-'||active,
                'admission_cohort_id', workspace_fixture.id('cohort'), 'program_semester_id', workspace_fixture.id('stage'),
                'semester_id', workspace_fixture.id('term')));
        PERFORM public.manage_academic_structure_record(actor, tenant, 'academic_offerings', NULL,
            jsonb_build_object('academic_section_id', item->>'academic_section_id',
                'curriculum_subject_id', workspace_fixture.id('mapping'), 'is_active', active));
        BEGIN
            PERFORM public.delete_unused_academic_calendar_record(actor, tenant, 'academic_sections', (item->>'academic_section_id')::uuid);
            RAISE EXCEPTION 'Section with active/inactive offering deleted';
        EXCEPTION WHEN SQLSTATE 'P2003' THEN NULL; END;
    END LOOP;
    INSERT INTO public.students(user_id, institution_id) VALUES(workspace_fixture.id('student'), tenant)
        RETURNING student_id INTO student;
    FOREACH state IN ARRAY ARRAY['assigned', 'registered'] LOOP
        item := public.manage_academic_structure_record(actor, tenant, 'academic_sections', NULL,
            jsonb_build_object('name', 'Student-linked section', 'code', 'STUDENT-'||state,
                'admission_cohort_id', workspace_fixture.id('cohort'), 'program_semester_id', workspace_fixture.id('stage'),
                'semester_id', workspace_fixture.id('term')));
        INSERT INTO public.student_semester_registrations(institution_id, student_id, academic_section_id, semester_id, status, registered_at)
        VALUES(tenant, student, (item->>'academic_section_id')::uuid, workspace_fixture.id('term'), state,
            CASE WHEN state='registered' THEN now() ELSE NULL END);
        SELECT jsonb_agg(to_jsonb(s) ORDER BY s.student_id) INTO students_before FROM public.students s;
        SELECT count(*) INTO audits FROM public.admin_audit_log;
        BEGIN
            PERFORM public.delete_unused_academic_calendar_record(actor, tenant, 'academic_sections', (item->>'academic_section_id')::uuid);
            RAISE EXCEPTION 'Student-linked section deleted';
        EXCEPTION WHEN SQLSTATE 'P2003' THEN NULL; END;
        IF (SELECT count(*) FROM public.admin_audit_log) <> audits
            OR (SELECT jsonb_agg(to_jsonb(s) ORDER BY s.student_id) FROM public.students s) IS DISTINCT FROM students_before THEN
            RAISE EXCEPTION 'Blocked section deletion changed students or audit';
        END IF;
        DELETE FROM public.student_semester_registrations WHERE student_id=student;
    END LOOP;
    FOREACH role_name IN ARRAY ARRAY['staff', 'student', 'foreign_admin'] LOOP
        BEGIN
            PERFORM public.delete_unused_academic_calendar_record(workspace_fixture.id(role_name), tenant,
                'academic_sections', (item->>'academic_section_id')::uuid);
            RAISE EXCEPTION 'Unauthorized section deletion accepted';
        EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    END LOOP;
    BEGIN
        PERFORM public.delete_unused_academic_calendar_record(workspace_fixture.id('foreign_admin'),
            workspace_fixture.id('foreign_tenant'), 'academic_sections', (item->>'academic_section_id')::uuid);
        RAISE EXCEPTION 'Foreign section exposed';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
        DELETE FROM public.role_permissions rp USING public.roles r, public.permissions p
        WHERE rp.role_id=r.id AND rp.permission_id=p.permission_id AND r.name='admin'
            AND p.code IN ('courses.manage','courses.*','*');
        PERFORM public.delete_unused_academic_calendar_record(actor, tenant, 'academic_sections', (item->>'academic_section_id')::uuid);
        RAISE EXCEPTION 'Revoked section grant accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF (SELECT jsonb_agg(to_jsonb(u) ORDER BY u.id) FROM public.users u) IS DISTINCT FROM users_before THEN
        RAISE EXCEPTION 'Account identities changed';
    END IF;
END;
$$;
ROLLBACK;
