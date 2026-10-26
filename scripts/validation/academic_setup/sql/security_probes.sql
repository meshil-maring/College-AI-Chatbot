-- Catalog probes are local-only and print no rows or environment contents.
BEGIN;
DO $$
DECLARE entity text; browser text; routine text; info record; denied text;
BEGIN
    FOREACH entity IN ARRAY ARRAY['departments','programs','academic_years','study_semesters',
        'subjects','class_sections','section_subject_assignments'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid=to_regclass('public.'||entity)
            AND relrowsecurity AND relowner='postgres'::regrole) THEN
            RAISE EXCEPTION 'Academic table RLS missing';
        END IF;
        IF EXISTS (SELECT 1 FROM pg_policy WHERE polrelid=to_regclass('public.'||entity)) THEN
            RAISE EXCEPTION 'Unexpected academic RLS policy';
        END IF;
        denied:='INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER';
        IF current_setting('server_version_num')::integer>=170000 THEN denied:=denied||',MAINTAIN'; END IF;
        FOREACH browser IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            IF has_table_privilege(browser,'public.'||entity,denied)
                OR has_any_column_privilege(browser,'public.'||entity,'INSERT,UPDATE,REFERENCES')
                OR (browser<>'service_role' AND (
                    has_table_privilege(browser,'public.'||entity,'SELECT')
                    OR has_any_column_privilege(browser,'public.'||entity,'SELECT'))) THEN
                RAISE EXCEPTION 'Browser table access exposed';
            END IF;
        END LOOP;
        IF NOT has_table_privilege('service_role','public.'||entity,'SELECT')
            OR has_table_privilege('service_role','public.'||entity,'INSERT,UPDATE,DELETE,TRUNCATE') THEN
            RAISE EXCEPTION 'Service reads or audited-only mutation contract failed';
        END IF;
    END LOOP;
    FOREACH routine IN ARRAY ARRAY[
        'public.manage_academic_foundation(uuid,uuid,text,uuid,jsonb)',
        'public.manage_academic_structure(uuid,uuid,text,uuid,jsonb)',
        'public.manage_academic_sections(uuid,uuid,text,uuid,jsonb)'] LOOP
        IF NOT has_function_privilege('service_role',routine,'EXECUTE')
            OR has_function_privilege('anon',routine,'EXECUTE')
            OR has_function_privilege('authenticated',routine,'EXECUTE') THEN
            RAISE EXCEPTION 'Academic mutation entry point privilege exposure';
        END IF;
    END LOOP;
    FOREACH routine IN ARRAY ARRAY[
        'public.assert_academic_foundation_actor(uuid,uuid,text)',
        'public.validate_academic_foundation()',
        'public.validate_academic_structure()',
        'public.guard_academic_structure_parent()',
        'public.validate_academic_sections()',
        'public.guard_academic_sections_parent()',
        'public.manage_academic_foundation(uuid,uuid,text,uuid,jsonb)',
        'public.manage_academic_structure(uuid,uuid,text,uuid,jsonb)',
        'public.manage_academic_sections(uuid,uuid,text,uuid,jsonb)'] LOOP
        SELECT * INTO STRICT info FROM pg_proc WHERE oid=to_regprocedure(routine);
        IF info.proowner<>'postgres'::regrole OR NOT info.prosecdef
            OR info.proconfig IS DISTINCT FROM ARRAY['search_path=""']::text[] THEN
            RAISE EXCEPTION 'Academic routine owner, SECURITY DEFINER or safe search_path differs';
        END IF;
        FOREACH browser IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            IF has_function_privilege(browser,routine,'EXECUTE') IS DISTINCT FROM
                (browser='service_role' AND routine LIKE 'public.manage_academic_%') THEN
                RAISE EXCEPTION 'Academic helper or mutation execution exposed';
            END IF;
        END LOOP;
    END LOOP;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role')
        AND (rolsuper OR rolcreaterole OR pg_has_role(oid,'postgres','MEMBER'))) THEN
        RAISE EXCEPTION 'API principal can assume ownership authority';
    END IF;
END $$;
ROLLBACK;
