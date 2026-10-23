DO $$
DECLARE item record; names text;
BEGIN
    -- Drop only triggers attached to retired routines, including the two
    -- academic reconciliation triggers on retained student identities and the
    -- package truncate guard on the retained audit log.
    FOR item IN SELECT t.tgname,n.nspname,c.relname FROM pg_catalog.pg_trigger t
        JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid
        JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE NOT t.tgisinternal AND p.proname IN(SELECT name FROM academic_decommission_functions)
          AND p.pronamespace='public'::regnamespace LOOP
        IF item.nspname <> 'public' OR (item.relname NOT IN(SELECT name FROM academic_decommission_tables)
            AND item.relname NOT IN('students','admin_audit_log')) THEN
            RAISE EXCEPTION 'Unexpected trigger consumer %.%; removal refused',item.nspname,item.relname;
        END IF;
        EXECUTE format('DROP TRIGGER %I ON %I.%I',item.tgname,item.nspname,item.relname);
    END LOOP;
    SELECT string_agg(p.oid::regprocedure::text,', ' ORDER BY p.oid) INTO names
    FROM pg_catalog.pg_proc p WHERE p.pronamespace='public'::regnamespace
      AND p.proname IN(SELECT name FROM academic_decommission_functions);
    IF names IS NOT NULL THEN EXECUTE 'DROP FUNCTION ' || names || ' RESTRICT'; END IF;
END;
$$;

-- Drop only academic references from the canonical student account profile.
-- All identifiers, approval, status, dates and contact metadata are retained.
ALTER TABLE public.students DROP COLUMN program_id, DROP COLUMN academic_year_id;

DO $$
DECLARE names text;
BEGIN
    SELECT string_agg(format('public.%I',name),', ' ORDER BY name) INTO names FROM academic_decommission_tables;
    -- One bounded DROP handles internal academic FKs together. RESTRICT makes
    -- any unexpected outside dependency abort instead of cascading into it.
    EXECUTE 'DROP TABLE ' || names || ' RESTRICT';
END;
$$;
