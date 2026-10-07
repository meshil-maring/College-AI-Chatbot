-- College AI Chatbot: application records and ALL Auth login accounts.
-- Intended project: rjnfmjcvkfotneswpygr. Use an explicit --project-ref.
-- Preserve schema, RLS, functions, migration history, configuration and buckets.
-- Recreate the reserved platform parent required by university registration.
-- Supabase Storage must be emptied using its API BEFORE running this file.
-- Cloudflare R2 files are outside this reset.
-- This checked-in version performs a rehearsal and ends with ROLLBACK.
-- For an explicitly authorized reset, change ONLY the final ROLLBACK to COMMIT.
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '120s';

CREATE TEMP TABLE reset_configuration (
    table_name text PRIMARY KEY,
    contents jsonb NOT NULL
) ON COMMIT DROP;

DO $reset$
DECLARE
    protected_tables constant text[] := ARRAY[
        'roles', 'permissions', 'role_permissions',
        'responsibility_definitions', 'responsibility_permissions', 'test_types'
    ];
    target_tables text;
    item record;
    contents jsonb;
    remaining bigint;
BEGIN
    -- Abort before any destructive statement if Storage is not empty.
    LOCK TABLE storage.objects IN SHARE MODE;
    IF EXISTS (SELECT 1 FROM storage.objects) THEN
        RAISE EXCEPTION 'Supabase Storage is not empty; delete files through the Storage API first';
    END IF;

    IF EXISTS (SELECT 1 FROM pg_matviews WHERE schemaname = 'public') THEN
        RAISE EXCEPTION 'Review public materialized views before resetting data';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND (t.tgtype::integer & 32) <> 0 AND NOT t.tgisinternal
    ) THEN
        RAISE EXCEPTION 'Review public TRUNCATE triggers before resetting data';
    END IF;

    -- Capture and lock each existing configuration catalog.
    FOR item IN
        SELECT c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND c.relname = ANY (protected_tables)
        ORDER BY c.relname
    LOOP
        EXECUTE format('LOCK TABLE public.%I IN SHARE MODE', item.relname);
        EXECUTE format(
            'SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), ''[]''::jsonb) FROM public.%I t',
            item.relname
        ) INTO contents;
        INSERT INTO reset_configuration VALUES (item.relname, contents);
    END LOOP;
    IF NOT EXISTS (SELECT 1 FROM reset_configuration WHERE table_name = 'roles')
       OR NOT EXISTS (SELECT 1 FROM reset_configuration WHERE table_name = 'permissions')
       OR NOT EXISTS (SELECT 1 FROM reset_configuration WHERE table_name = 'role_permissions') THEN
        RAISE EXCEPTION 'Expected application role/permission catalogs are missing';
    END IF;

    SELECT string_agg(format('public.%I', c.relname), ', ' ORDER BY c.relname)
    INTO target_tables
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
      AND NOT c.relispartition AND NOT (c.relname = ANY (protected_tables))
      AND NOT EXISTS (
          SELECT 1 FROM pg_depend d
          WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e'
      );
    IF target_tables IS NULL THEN
        RAISE EXCEPTION 'No application tables found; refusing an unexpected target';
    END IF;

    -- One bounded transaction; RESTRICT refuses cross-schema FK expansion.
    -- No trigger, constraint or RLS policy is disabled or removed.
    EXECUTE 'TRUNCATE TABLE ' || target_tables || ' RESTART IDENTITY RESTRICT';

    -- organizations contains both user data and this required system seed.
    -- Restore the same canonical onboarding seed as the Phase 7.13 migration.
    INSERT INTO public.organizations (
        name, organization_code, official_email, contact_information, status
    ) VALUES (
        'College AI Platform Institutions',
        'COLLEGE-AI-PLATFORM',
        'platform-institutions@local.invalid',
        'Reserved parent organization for institutions created through the Super Admin platform API.',
        'active'
    );

    -- Supabase's managed Auth FKs remove identities, sessions and user factors.
    -- DELETE, rather than TRUNCATE/CASCADE, preserves managed Auth structure.
    DELETE FROM auth.users;

    FOR item IN SELECT * FROM reset_configuration ORDER BY table_name LOOP
        EXECUTE format(
            'SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), ''[]''::jsonb) FROM public.%I t',
            item.table_name
        ) INTO contents;
        IF contents IS DISTINCT FROM item.contents THEN
            RAISE EXCEPTION 'Configuration changed during reset: %', item.table_name;
        END IF;
    END LOOP;

    FOR item IN
        SELECT c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND NOT c.relispartition AND NOT (c.relname = ANY (protected_tables))
          AND NOT EXISTS (
              SELECT 1 FROM pg_depend d
              WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e'
          )
    LOOP
        IF item.relname = 'organizations' THEN
            SELECT count(*) INTO remaining FROM public.organizations
            WHERE organization_code <> 'COLLEGE-AI-PLATFORM';
        ELSE
            EXECUTE format('SELECT count(*) FROM public.%I', item.relname) INTO remaining;
        END IF;
        IF remaining <> 0 THEN
            RAISE EXCEPTION 'Application data remains in %', item.relname;
        END IF;
    END LOOP;
    IF EXISTS (SELECT 1 FROM auth.users) OR EXISTS (SELECT 1 FROM storage.objects) THEN
        RAISE EXCEPTION 'Auth users or Storage objects remain; reset was rolled back';
    END IF;
    IF (SELECT count(*) FROM public.organizations) <> 1 OR NOT EXISTS (
        SELECT 1 FROM public.organizations
        WHERE organization_code = 'COLLEGE-AI-PLATFORM'
          AND status = 'active' AND join_code IS NULL
    ) THEN
        RAISE EXCEPTION 'Required platform onboarding configuration was not restored';
    END IF;
END;
$reset$;

SELECT 'Reset validated within the transaction; check the final COMMIT/ROLLBACK statement' AS result;
ROLLBACK;
