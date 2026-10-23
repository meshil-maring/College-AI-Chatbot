DO $$
DECLARE item record; current_rows jsonb; projection text; predicate text;
BEGIN
    IF EXISTS (SELECT 1 FROM academic_decommission_tables t WHERE to_regclass(format('public.%I',t.name)) IS NOT NULL)
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_proc p WHERE p.pronamespace='public'::regnamespace
            AND p.proname IN(SELECT name FROM academic_decommission_functions)) THEN
        RAISE EXCEPTION 'Academic runtime objects remain after decommission';
    END IF;
    IF EXISTS (SELECT 1 FROM public.permissions
        WHERE code ~ '^(academic\.|attendance\.|results\.|faculty\.assignments\.|departments\.|courses\.|subjects\.|semesters\.|academic_years\.)') THEN
        RAISE EXCEPTION 'Retired academic permission codes remain';
    END IF;
    FOR item IN SELECT * FROM academic_decommission_preserved LOOP
        projection := CASE WHEN item.schema_name='public' AND item.table_name='students'
            THEN 'to_jsonb(t) - ARRAY[''program_id'',''academic_year_id'']' ELSE 'to_jsonb(t)' END;
        predicate := CASE WHEN item.schema_name='public' AND item.table_name IN('permissions','role_permissions','user_permission_grants')
            THEN 'WHERE permission_id NOT IN(SELECT permission_id FROM academic_decommission_permissions)' ELSE '' END;
        EXECUTE format('SELECT COALESCE(jsonb_agg(row ORDER BY row::text),''[]''::jsonb) FROM '
            || '(SELECT %s AS row FROM %I.%I t %s) source',projection,item.schema_name,item.table_name,predicate) INTO current_rows;
        IF current_rows IS DISTINCT FROM item.rows THEN
            RAISE EXCEPTION 'Preserved data changed in %.%; decommission rolled back',item.schema_name,item.table_name;
        END IF;
    END LOOP;
    IF EXISTS (SELECT 1 FROM academic_decommission_routines snapshot
        LEFT JOIN pg_catalog.pg_proc p ON p.oid=snapshot.oid
        WHERE p.oid IS NULL OR pg_get_functiondef(p.oid) IS DISTINCT FROM snapshot.definition) THEN
        RAISE EXCEPTION 'A preserved account/nonacademic function changed';
    END IF;
END;
$$;
NOTIFY pgrst, 'reload schema';
