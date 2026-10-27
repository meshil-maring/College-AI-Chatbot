BEGIN;
CREATE TABLE workspace_fixture.results (name text PRIMARY KEY, passed boolean NOT NULL CHECK(passed));
CREATE FUNCTION workspace_fixture.assert_true(label text, condition boolean) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF condition IS DISTINCT FROM true THEN RAISE EXCEPTION 'FAILED: %',label; END IF;
    INSERT INTO workspace_fixture.results VALUES(label,true);
END;
$$;
SELECT workspace_fixture.assert_true('All fourteen academic entities have records',
    (SELECT count(*)=14 FROM information_schema.tables WHERE table_schema='public' AND table_name IN (
        'departments','programs','academic_years','semesters','courses','program_courses','course_offerings',
        'sections','program_semesters','curriculum_versions','curriculum_subjects','admission_cohorts',
        'academic_sections','academic_offerings'))
    AND (SELECT count(*)=25 FROM public.admin_audit_log WHERE action LIKE 'academic.%'));
SELECT workspace_fixture.assert_true('Published curriculum has timestamp and two mappings',
    (SELECT status='published' AND published_at IS NOT NULL FROM public.curriculum_versions
     WHERE curriculum_version_id=workspace_fixture.id('curriculum'))
    AND (SELECT count(*)=2 FROM public.curriculum_subjects
         WHERE curriculum_version_id=workspace_fixture.id('curriculum')));
SELECT workspace_fixture.assert_true('Cohort retains its published curriculum and expected capacity',
    (SELECT curriculum_version_id=workspace_fixture.id('curriculum') AND expected_count=60 AND is_active
     FROM public.admission_cohorts WHERE admission_cohort_id=workspace_fixture.id('cohort')));
SELECT workspace_fixture.assert_true('Offering matches section cohort, curriculum and study semester',
    (SELECT count(*)=1 FROM public.academic_offerings o
     JOIN public.academic_sections s USING(academic_section_id,institution_id)
     JOIN public.admission_cohorts c USING(admission_cohort_id,institution_id)
     JOIN public.curriculum_subjects m USING(curriculum_subject_id,institution_id)
     WHERE o.academic_offering_id=workspace_fixture.id('offering')
       AND m.curriculum_version_id=c.curriculum_version_id
       AND m.program_semester_id=s.program_semester_id));
SELECT workspace_fixture.assert_true('Legacy section remains owned by its course offering',
    (SELECT course_offering_id=workspace_fixture.id('legacy_offering') FROM public.sections
     WHERE section_id=workspace_fixture.id('legacy_section')));
SELECT workspace_fixture.assert_true('Same department code is allowed in different colleges',
    (SELECT count(*)=2 AND count(DISTINCT institution_id)=2 FROM public.departments WHERE code='CSE'));
SELECT workspace_fixture.assert_true('Every academic mutation has an actor and complete audit snapshot',
    NOT EXISTS(SELECT 1 FROM public.admin_audit_log WHERE action LIKE 'academic.%'
        AND (actor_user_id IS NULL OR institution_id IS NULL OR record_data->'after' IS NULL)));
SELECT workspace_fixture.assert_true('No enrollment totals invented from expected capacity',
    NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public'
        AND table_name IN ('admission_cohorts','academic_sections')
        AND column_name IN ('enrolled_count','student_count')));
COMMIT;
SELECT 'PASS: '||count(*)||' data integrity and audit checks' FROM workspace_fixture.results;
