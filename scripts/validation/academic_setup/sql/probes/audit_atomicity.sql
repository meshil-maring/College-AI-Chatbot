BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
DO $$
DECLARE w jsonb:=academic_setup_check.world(); item record; baseline jsonb; existing jsonb;
    operation jsonb; record_id uuid;
BEGIN
    FOR item IN SELECT * FROM (VALUES
        ('departments','department_id','{"name":"Audit","code":"AUDIT"}'::jsonb),
        ('subjects','subject_id',jsonb_build_object('department_id',w->'department','name','Audit','code','AUDIT','credits',3)),
        ('sections','section_id',jsonb_build_object('study_semester_id',w->'semester','name','Audit','code','AUDIT'))
    ) cases(entity,key,payload) LOOP
        existing:=academic_setup_check.mutate(w,item.entity,item.payload);
        record_id:=(existing->>item.key)::uuid;
        ALTER TABLE public.admin_audit_log ADD CONSTRAINT academic_probe_deny
            CHECK (action NOT LIKE 'academic.%') NOT VALID;
        baseline:=academic_setup_check.capture(true);
        FOREACH operation IN ARRAY ARRAY[item.payload||'{"code":"NOAUDIT","name":"No audit"}'::jsonb,
            '{"description":"Update refused"}'::jsonb,'{"is_active":false}'::jsonb] LOOP
            PERFORM academic_setup_check.expect_error(format('SELECT academic_setup_check.mutate(%L,%L,%L,%L)',
                w,item.entity,operation,CASE WHEN operation ? 'code' THEN NULL ELSE record_id END),
                '23514',NULL,'academic_probe_deny');
            IF academic_setup_check.capture(true) IS DISTINCT FROM baseline THEN
                RAISE EXCEPTION 'Audit failure left partial foundation, structure or section state';
            END IF;
        END LOOP;
        ALTER TABLE public.admin_audit_log DROP CONSTRAINT academic_probe_deny;
    END LOOP;
END $$;
ROLLBACK;
