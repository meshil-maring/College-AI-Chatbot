BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SELECT workspace_fixture.reject('Active offerings prevent section deactivation',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'academic_sections',%L,'{"is_active":false}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('section')),'23514');
SELECT workspace_fixture.reject('Active sections prevent completing their admission cohort',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'admission_cohorts',%L,'{"status":"completed"}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('cohort')),'23514');
SELECT workspace_fixture.reject('Active progression prevents program deactivation',
    format($q$SELECT public.manage_academic_master_record(%L,%L,'programs',%L,'{"is_active":false}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('program')),'23514');
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'academic_offerings',workspace_fixture.id('offering'),'{"is_active":false}');
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'academic_sections',workspace_fixture.id('section'),'{"is_active":false}');
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'admission_cohorts',workspace_fixture.id('cohort'),'{"status":"completed"}');
SELECT workspace_fixture.assert_true('Dependent-first deactivation completes the cohort safely',
    (SELECT status='completed' AND NOT is_active FROM public.admission_cohorts
     WHERE admission_cohort_id=workspace_fixture.id('cohort')));
SELECT workspace_fixture.reject('Inactive cohort prevents section reactivation',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'academic_sections',%L,'{"is_active":true}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('section')),'23514');
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'admission_cohorts',workspace_fixture.id('cohort'),'{"status":"active"}');
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'academic_sections',workspace_fixture.id('section'),'{"is_active":true}');
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'academic_offerings',workspace_fixture.id('offering'),'{"is_active":true}');
SELECT public.manage_academic_structure_record(workspace_fixture.id('admin'),workspace_fixture.id('tenant'),
    'curriculum_versions',workspace_fixture.id('curriculum'),'{"status":"archived"}');
SELECT workspace_fixture.assert_true('Archived curriculum preserves existing batch assignment and active delivery',
    (SELECT status='archived' FROM public.curriculum_versions WHERE curriculum_version_id=workspace_fixture.id('curriculum'))
    AND (SELECT is_active AND curriculum_version_id=workspace_fixture.id('curriculum')
         FROM public.admission_cohorts WHERE admission_cohort_id=workspace_fixture.id('cohort'))
    AND (SELECT is_active FROM public.academic_offerings WHERE academic_offering_id=workspace_fixture.id('offering')));
SELECT workspace_fixture.reject('Archived curriculum cannot return to published',
    format($q$SELECT public.manage_academic_structure_record(%L,%L,'curriculum_versions',%L,'{"status":"published"}')$q$,
        workspace_fixture.id('admin'),workspace_fixture.id('tenant'),workspace_fixture.id('curriculum')),'23514');
COMMIT;
SELECT 'PASS: '||count(*)||' integrity, rejection, permission and lifecycle assertions' FROM workspace_fixture.results;
