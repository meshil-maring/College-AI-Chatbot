DO $$
DECLARE a jsonb; b jsonb; code_name text; tenant uuid; created jsonb; parent_after jsonb;
BEGIN
    SELECT value INTO STRICT a FROM academic_setup_check.race_worlds WHERE name='a';
    SELECT value INTO STRICT b FROM academic_setup_check.race_worlds WHERE name='b';
    FOREACH code_name IN ARRAY ARRAY['RACE_DUP','RACE_ROLLBACK','RACE_TENANT'] LOOP
        tenant:=(a->>'tenant')::uuid;
        IF (SELECT count(*) FROM public.departments d WHERE d.institution_id=tenant AND code=code_name)<>1
            OR (SELECT count(*) FROM public.admin_audit_log l WHERE l.institution_id=tenant
                AND action='academic.departments.create' AND record_data->'after'->>'code'=code_name)<>1 THEN
            RAISE EXCEPTION 'Duplicate or rollback race left incorrect rows/audit';
        END IF;
        SELECT to_jsonb(d) INTO STRICT created FROM public.departments d
        WHERE institution_id=tenant AND code=code_name;
        IF (SELECT count(*) FROM public.admin_audit_log WHERE record_id=created->>'department_id')<>1
            OR (SELECT count(*) FROM public.admin_audit_log l WHERE l.institution_id=tenant
                AND actor_user_id=(a->>'actor')::uuid AND table_name='departments'
                AND record_id=created->>'department_id' AND action='academic.departments.create'
                AND status='success' AND record_data->'before'='null'::jsonb
                AND record_data->'after'=created)<>1 THEN
            RAISE EXCEPTION 'Tenant A race audit identity or transition differs';
        END IF;
        INSERT INTO academic_setup_check.race_expected_rows
        SELECT 'public.admin_audit_log',to_jsonb(l) FROM public.admin_audit_log l
        WHERE institution_id=tenant AND record_id=created->>'department_id';
    END LOOP;
    IF (SELECT count(*) FROM public.departments WHERE institution_id=(b->>'tenant')::uuid
        AND code='RACE_TENANT')<>1 THEN RAISE EXCEPTION 'Other tenant did not progress'; END IF;
    SELECT to_jsonb(d) INTO STRICT created FROM public.departments d
    WHERE institution_id=(b->>'tenant')::uuid AND code='RACE_TENANT';
    IF (SELECT count(*) FROM public.admin_audit_log
        WHERE institution_id=(b->>'tenant')::uuid AND record_id=created->>'department_id')<>1
        OR (SELECT count(*) FROM public.admin_audit_log
            WHERE institution_id=(b->>'tenant')::uuid AND actor_user_id=(b->>'actor')::uuid
                AND table_name='departments' AND record_id=created->>'department_id'
                AND action='academic.departments.create' AND status='success'
                AND record_data->'before'='null'::jsonb AND record_data->'after'=created)<>1 THEN
        RAISE EXCEPTION 'Tenant B creation audit count, identity or transition differs';
    END IF;
    INSERT INTO academic_setup_check.race_expected_rows
    SELECT 'public.admin_audit_log',to_jsonb(l) FROM public.admin_audit_log l
    WHERE institution_id=(b->>'tenant')::uuid AND record_id=created->>'department_id';
    SELECT to_jsonb(d) INTO STRICT parent_after FROM public.departments d
    WHERE department_id=(a->>'race_parent')::uuid AND institution_id=(a->>'tenant')::uuid;
    IF a->'race_parent_before'->'is_active' IS DISTINCT FROM 'true'::jsonb
        OR parent_after->'is_active' IS DISTINCT FROM 'false'::jsonb
        OR (SELECT count(*) FROM public.admin_audit_log
            WHERE institution_id=(a->>'tenant')::uuid AND record_id=a->>'race_parent')<>2
        OR (SELECT count(*) FROM public.admin_audit_log
            WHERE institution_id=(a->>'tenant')::uuid AND actor_user_id=(a->>'actor')::uuid
                AND table_name='departments' AND record_id=a->>'race_parent'
                AND action='academic.departments.deactivate' AND status='success'
                AND record_data->'before'=a->'race_parent_before'
                AND record_data->'after'=parent_after)<>1 THEN
        RAISE EXCEPTION 'Parent deactivation audit count, identity or transition differs';
    END IF;
    INSERT INTO academic_setup_check.race_expected_rows
    SELECT 'public.admin_audit_log',to_jsonb(l) FROM public.admin_audit_log l
    WHERE institution_id=(a->>'tenant')::uuid AND record_id=a->>'race_parent'
        AND action='academic.departments.deactivate';
    IF (SELECT is_active FROM public.departments WHERE department_id=(a->>'race_parent')::uuid)
        OR EXISTS (SELECT 1 FROM public.subjects WHERE institution_id=(a->>'tenant')::uuid AND code='RACE_CHILD')
        OR EXISTS (SELECT 1 FROM public.admin_audit_log WHERE institution_id=(a->>'tenant')::uuid
            AND record_data->'after'->>'code'='RACE_CHILD') THEN
        RAISE EXCEPTION 'Parent/child race violated lifecycle or audit atomicity';
    END IF;
END $$;
