BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
DO $$
DECLARE a jsonb:=academic_setup_check.world(); b jsonb:=academic_setup_check.world();
    item record; command text; baseline jsonb; variant text;
    denial text:='Institution administrator with academic permission required';
BEGIN
    -- Identical codes/names in two tenants are intentionally valid.
    baseline:=academic_setup_check.capture(true);
    FOR item IN SELECT * FROM (VALUES
        ('departments','department'),('programs','program'),('academic_years','year'),
        ('semesters','semester'),('subjects','subject'),('sections','section'),
        ('section_subjects','assignment')) kinds(entity,key) LOOP
        command:=format('SELECT academic_setup_check.mutate(%L,%L,%L,%L)',
            a,item.entity,'{"is_active":false}',b->>item.key);
        PERFORM academic_setup_check.expect_error(command,'P0002','Academic record not found');
        command:=format('SELECT academic_setup_check.mutate(%L,%L,%L,%L)',
            a||jsonb_build_object('actor',b->'actor'),item.entity,'{"is_active":false}',a->>item.key);
        PERFORM academic_setup_check.expect_error(command,'42501',denial);
    END LOOP;
    FOR item IN SELECT * FROM (VALUES
        ('programs',jsonb_build_object('department_id',b->'department','name','Foreign','code','F',
            'degree_type','B.Tech','duration_years',4),'Department not found in institution'),
        ('subjects',jsonb_build_object('department_id',b->'department','name','Foreign','code','F','credits',3),
            'Department not found in institution'),
        ('semesters',jsonb_build_object('program_id',b->'program','academic_year_id',a->'year',
            'study_semester_number',6,'name','Foreign','code','F'),'Program or academic year not found in institution'),
        ('semesters',jsonb_build_object('program_id',a->'program','academic_year_id',b->'year',
            'study_semester_number',6,'name','Foreign','code','F'),'Program or academic year not found in institution'),
        ('sections',jsonb_build_object('study_semester_id',b->'semester','name','Foreign','code','F'),
            'Study semester not found in institution'),
        ('section_subjects',jsonb_build_object('section_id',b->'section','subject_id',a->'subject'),
            'Section not found in institution'),
        ('section_subjects',jsonb_build_object('section_id',a->'section','subject_id',b->'subject'),
            'Subject not found in institution')) cases(entity,payload,message) LOOP
        PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,%L,%L)',
            a,item.entity,item.payload),'23503',item.message);
    END LOOP;
    command:=format('SELECT academic_setup_check.mutate(%L,''departments'',''{"name":"Denied","code":"DENIED"}'')',a);
    FOREACH variant IN ARRAY ARRAY['inactive_user','inactive_role','inactive_permission','inactive_institution',
        'inactive_org','delegated_only','admin_delegated_only','split_role_provenance',
        'foreign_admin_local_staff','wrong_permission_scope',
        'platform_authority','organization_authority'] LOOP
        BEGIN
            CASE variant
            WHEN 'inactive_user' THEN UPDATE public.users SET status='inactive' WHERE id=(a->>'actor')::uuid;
            WHEN 'inactive_role' THEN UPDATE public.roles SET is_active=false WHERE name='admin';
            WHEN 'inactive_permission' THEN UPDATE public.permissions SET is_active=false
                WHERE code IN ('departments.manage','departments.*','*');
            WHEN 'inactive_institution' THEN UPDATE public.institutions SET is_active=false
                WHERE institution_id=(a->>'tenant')::uuid;
            WHEN 'inactive_org' THEN UPDATE public.organizations SET status='suspended'
                WHERE organization_id=(a->>'org')::uuid;
            WHEN 'wrong_permission_scope' THEN UPDATE public.permissions SET scope='platform'
                WHERE code IN ('departments.manage','departments.*','*');
            ELSE
                DELETE FROM public.user_roles WHERE user_id=(a->>'actor')::uuid;
                IF variant IN ('platform_authority','organization_authority') THEN
                    INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
                    SELECT (a->>'actor')::uuid,id,
                        CASE WHEN variant='platform_authority' THEN 'platform' ELSE 'organization' END,
                        CASE WHEN variant='platform_authority' THEN NULL ELSE (a->>'org')::uuid END,
                        CASE WHEN variant='platform_authority' THEN NULL ELSE (a->>'org')::uuid END
                    FROM public.roles WHERE name=CASE WHEN variant='platform_authority' THEN 'super_admin' ELSE 'admin' END;
                    IF NOT FOUND THEN RAISE EXCEPTION 'Authority fixture role missing'; END IF;
                ELSE
                    INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
                    SELECT (a->>'actor')::uuid,id,'institution',(a->>'tenant')::uuid,(a->>'org')::uuid
                    FROM public.roles WHERE name='staff';
                    IF variant='foreign_admin_local_staff' THEN
                        INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
                        SELECT (a->>'actor')::uuid,id,'institution',(b->>'tenant')::uuid,(b->>'org')::uuid
                        FROM public.roles WHERE name='admin';
                    ELSIF variant IN ('split_role_provenance','admin_delegated_only') THEN
                        INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
                        SELECT (a->>'actor')::uuid,id,'institution',(a->>'tenant')::uuid,(a->>'org')::uuid
                        FROM public.roles WHERE name='admin';
                        DELETE FROM public.role_permissions WHERE role_id=(SELECT id FROM public.roles WHERE name='admin')
                            AND permission_id IN (SELECT permission_id FROM public.permissions
                                WHERE code IN ('departments.manage','departments.*','*'));
                        IF variant='split_role_provenance' THEN
                            INSERT INTO public.role_permissions(role_id,permission_id)
                            SELECT r.id,p.permission_id FROM public.roles r CROSS JOIN public.permissions p
                            WHERE r.name='staff' AND p.code='departments.manage' ON CONFLICT DO NOTHING;
                        ELSE
                            INSERT INTO public.user_permission_grants(user_id,institution_id,permission_id,granted_by)
                            SELECT (a->>'actor')::uuid,(a->>'tenant')::uuid,permission_id,(b->>'actor')::uuid
                            FROM public.permissions WHERE code='departments.manage';
                        END IF;
                    ELSE
                        INSERT INTO public.user_permission_grants(user_id,institution_id,permission_id,granted_by)
                        SELECT (a->>'actor')::uuid,(a->>'tenant')::uuid,permission_id,(b->>'actor')::uuid
                        FROM public.permissions WHERE code='departments.manage';
                    END IF;
                END IF;
            END CASE;
            PERFORM academic_setup_check.expect_error(command,'42501',denial);
            RAISE EXCEPTION USING ERRCODE='P4098';
        EXCEPTION WHEN SQLSTATE 'P4098' THEN NULL;
        END;
    END LOOP;
    PERFORM set_config('request.jwt.claim.role','authenticated',true);
    PERFORM academic_setup_check.expect_error(command,'42501','Academic Setup requires the trusted backend');
    IF academic_setup_check.capture(true) IS DISTINCT FROM baseline THEN
        RAISE EXCEPTION 'Denied requests changed state';
    END IF;
END $$;
ROLLBACK;
