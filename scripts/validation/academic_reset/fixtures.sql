-- Disposable fixtures only. No live data or credentials.
DO $$
DECLARE tenant uuid := academic_package_fixture.id('tenant'); outsider uuid := gen_random_uuid();
    org uuid; department uuid;
BEGIN
    SELECT organization_id INTO org FROM public.institutions WHERE institution_id = tenant;
    INSERT INTO public.institutions(institution_id,organization_id,name,code,status)
    VALUES(outsider,org,'Preserved institution','KEEP-' || left(outsider::text,8),'active');
    INSERT INTO public.departments(institution_id,name,code) VALUES(outsider,'Preserved department','KEEP')
    RETURNING department_id INTO department;
    INSERT INTO public.programs(department_id,name,code,degree_type,duration_years)
    VALUES(department,'Preserved program','KEEP','B.Tech',4);
    INSERT INTO academic_package_fixture.ids VALUES('outsider',outsider);
    INSERT INTO public.responsibility_definitions(code,name,allowed_scope_types)
    VALUES('reset_contract_institution','Preserved institution appointment',ARRAY['institution']);
    INSERT INTO public.faculty_responsibilities(institution_id,faculty_user_id,responsibility_code,
        scope_type,scope_id,scope_key,start_at,created_by)
    VALUES(tenant,academic_package_fixture.id('faculty'),'reset_contract_institution','institution',tenant,
        'institution:' || tenant::text,clock_timestamp(),academic_package_fixture.id('admin'));
END;
$$;
