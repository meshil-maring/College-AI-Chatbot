BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
CREATE FUNCTION workspace_fixture.reject_calendar_deletion_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.action LIKE 'academic.%.delete' THEN
        RAISE EXCEPTION 'Simulated audit failure' USING ERRCODE='P2099';
    END IF;
    RETURN NEW;
END;
$$;
DO $$
DECLARE entity text; key text; item jsonb; payload jsonb; identifier uuid;
    actor uuid:=workspace_fixture.id('admin'); tenant uuid:=workspace_fixture.id('tenant');
BEGIN
    FOREACH entity IN ARRAY ARRAY['academic_years','semesters','academic_sections'] LOOP
        CASE entity
        WHEN 'academic_years' THEN
            key:='academic_year_id'; payload:='{"name":"Integrity year","code":"INT-Y","start_date":"2130-01-01","end_date":"2130-12-31"}';
        WHEN 'semesters' THEN
            key:='semester_id'; payload:=jsonb_build_object('name','Integrity term','code','INT-T',
                'academic_year_id',workspace_fixture.id('year'),'semester_number',30,'start_date','2026-08-01','end_date','2026-09-30');
        ELSE
            key:='academic_section_id'; payload:=jsonb_build_object('name','Integrity section','code','INT-S',
                'admission_cohort_id',workspace_fixture.id('cohort'),'program_semester_id',workspace_fixture.id('stage'),
                'semester_id',workspace_fixture.id('term'));
        END CASE;
        IF entity='academic_sections' THEN
            item:=public.manage_academic_structure_record(actor,tenant,entity,NULL,payload);
        ELSE
            item:=public.manage_academic_master_record(actor,tenant,entity,NULL,payload);
        END IF;
        identifier:=(item->>key)::uuid;
        EXECUTE 'CREATE TRIGGER calendar_deletion_audit BEFORE INSERT ON public.admin_audit_log
            FOR EACH ROW EXECUTE FUNCTION workspace_fixture.reject_calendar_deletion_audit()';
        BEGIN
            PERFORM public.delete_unused_academic_calendar_record(actor,tenant,entity,identifier);
            RAISE EXCEPTION 'Audit failure allowed deletion';
        EXCEPTION WHEN SQLSTATE 'P2099' THEN NULL; END;
        DROP TRIGGER calendar_deletion_audit ON public.admin_audit_log;
        -- A consumer with a CASCADE action must block, rather than disappear.
        EXECUTE format('CREATE TABLE workspace_fixture.cascade_consumer(owner uuid REFERENCES public.%I(%I) ON DELETE CASCADE)',entity,key);
        INSERT INTO workspace_fixture.cascade_consumer(owner) VALUES(identifier);
        BEGIN
            PERFORM public.delete_unused_academic_calendar_record(actor,tenant,entity,identifier);
            RAISE EXCEPTION 'Cascade consumer deleted';
        EXCEPTION WHEN SQLSTATE 'P2003' THEN NULL; END;
        DROP TABLE workspace_fixture.cascade_consumer;
        EXECUTE format('CREATE TABLE workspace_fixture.null_consumer(owner uuid REFERENCES public.%I(%I) ON DELETE SET NULL)',entity,key);
        INSERT INTO workspace_fixture.null_consumer(owner) VALUES(identifier);
        BEGIN
            PERFORM public.delete_unused_academic_calendar_record(actor,tenant,entity,identifier);
            RAISE EXCEPTION 'Set-null consumer detached';
        EXCEPTION WHEN SQLSTATE 'P2003' THEN NULL; END;
        DROP TABLE workspace_fixture.null_consumer;
        PERFORM public.delete_unused_academic_calendar_record(actor,tenant,entity,identifier);
    END LOOP;
    BEGIN
        PERFORM set_config('request.jwt.claim.role','authenticated',true);
        PERFORM public.delete_unused_academic_calendar_record(actor,tenant,'academic_years',gen_random_uuid());
        RAISE EXCEPTION 'Browser actor accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF has_function_privilege('authenticated','public.delete_unused_academic_calendar_record(uuid,uuid,text,uuid)','EXECUTE')
        OR has_function_privilege('anon','public.delete_unused_academic_calendar_record(uuid,uuid,text,uuid)','EXECUTE')
        OR NOT has_function_privilege('service_role','public.delete_unused_academic_calendar_record(uuid,uuid,text,uuid)','EXECUTE') THEN
        RAISE EXCEPTION 'Incorrect RPC grants';
    END IF;
END;
$$;
ROLLBACK;
