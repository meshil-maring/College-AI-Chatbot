DO $$
DECLARE item record; snapshot jsonb; projection text; predicate text;
BEGIN
    IF (SELECT count(*) FROM academic_decommission_tables) <> 39
        OR EXISTS (SELECT 1 FROM academic_decommission_tables t
            WHERE to_regclass(format('public.%I',t.name)) IS NULL) THEN
        RAISE EXCEPTION 'Expected the exact installed 39-table academic domain; inspect migration state';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_catalog.pg_constraint fk
        JOIN pg_catalog.pg_class parent ON parent.oid=fk.confrelid
        JOIN pg_catalog.pg_namespace pn ON pn.oid=parent.relnamespace
        JOIN academic_decommission_tables target ON target.name=parent.relname
        WHERE fk.contype='f' AND pn.nspname='public'
          AND fk.conrelid NOT IN (SELECT to_regclass(format('public.%I',name)) FROM academic_decommission_tables)
          AND NOT (fk.conrelid='public.students'::regclass
              AND fk.conname IN('students_program_id_fkey','students_academic_year_id_fkey'))
    ) THEN
        RAISE EXCEPTION 'Unexpected preserved-table foreign key into academic domain; removal refused';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_constraint fk
        WHERE fk.contype='f' AND fk.confrelid='public.permissions'::regclass
          AND fk.conrelid NOT IN('public.role_permissions'::regclass,'public.user_permission_grants'::regclass,
              'public.responsibility_permissions'::regclass)) THEN
        RAISE EXCEPTION 'Unexpected consumer of academic permission identities; removal refused';
    END IF;
    -- Lock in one deterministic order. Concurrent account/data writes wait
    -- briefly, and an unavailable lock aborts the whole migration safely.
    FOR item IN SELECT n.nspname,c.relname FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind='r' AND (n.nspname='public' OR (n.nspname='auth' AND c.relname='users'))
        ORDER BY n.nspname,c.relname LOOP
        EXECUTE format('LOCK TABLE %I.%I IN ACCESS EXCLUSIVE MODE',item.nspname,item.relname);
    END LOOP;
    FOR item IN SELECT n.nspname,c.relname FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind='r' AND (n.nspname='public' OR (n.nspname='auth' AND c.relname='users'))
          AND NOT (n.nspname='public' AND c.relname IN(SELECT name FROM academic_decommission_tables)) LOOP
        projection := CASE WHEN item.nspname='public' AND item.relname='students'
            THEN 'to_jsonb(t) - ARRAY[''program_id'',''academic_year_id'']' ELSE 'to_jsonb(t)' END;
        predicate := CASE WHEN item.nspname='public' AND item.relname='permissions'
            THEN 'WHERE permission_id NOT IN(SELECT permission_id FROM academic_decommission_permissions)'
            WHEN item.nspname='public' AND item.relname IN('role_permissions','user_permission_grants')
            THEN 'WHERE permission_id NOT IN(SELECT permission_id FROM academic_decommission_permissions)' ELSE '' END;
        EXECUTE format('SELECT COALESCE(jsonb_agg(row ORDER BY row::text),''[]''::jsonb) FROM '
            || '(SELECT %s AS row FROM %I.%I t %s) source',projection,item.nspname,item.relname,predicate) INTO snapshot;
        INSERT INTO academic_decommission_preserved VALUES(item.nspname,item.relname,snapshot);
    END LOOP;
    INSERT INTO academic_decommission_routines
    SELECT p.oid,pg_get_functiondef(p.oid) FROM pg_catalog.pg_proc p
    JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
    WHERE n.nspname='public' AND p.prokind='f'
      AND p.proname NOT IN(SELECT name FROM academic_decommission_functions)
      AND p.proname <> 'phase81_manage_staff_permission_grants';
END;
$$;
