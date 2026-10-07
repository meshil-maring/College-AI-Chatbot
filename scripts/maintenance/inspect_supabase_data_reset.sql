-- Read-only inspection for a data reset. Contains no persistent writes.
BEGIN;
SET LOCAL statement_timeout = '60s';

CREATE TEMP TABLE reset_inventory (
    table_name text PRIMARY KEY,
    row_count bigint NOT NULL,
    preserve_configuration boolean NOT NULL,
    preserved_row_count bigint NOT NULL,
    application_row_count bigint NOT NULL
) ON COMMIT DROP;

DO $inventory$
DECLARE
    item record;
    total bigint;
    preserve_table boolean;
    preserved bigint;
BEGIN
    FOR item IN
        SELECT c.oid, c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p')
          AND NOT c.relispartition
          AND NOT EXISTS (
              SELECT 1 FROM pg_depend d
              WHERE d.classid = 'pg_class'::regclass
                AND d.objid = c.oid AND d.deptype = 'e'
          )
        ORDER BY c.relname
    LOOP
        EXECUTE format('SELECT count(*) FROM public.%I', item.relname) INTO total;
        preserve_table := item.relname = ANY (ARRAY[
            'roles', 'permissions', 'role_permissions',
            'responsibility_definitions', 'responsibility_permissions', 'test_types'
        ]);
        preserved := 0;
        IF preserve_table THEN
            preserved := total;
        ELSIF item.relname = 'organizations' THEN
            SELECT count(*) INTO preserved FROM public.organizations
            WHERE organization_code = 'COLLEGE-AI-PLATFORM';
        END IF;
        INSERT INTO reset_inventory VALUES (
            item.relname, total, preserve_table, preserved, total - preserved
        );
    END LOOP;
END;
$inventory$;

SELECT jsonb_build_object(
    'public_tables', (SELECT jsonb_agg(to_jsonb(i) ORDER BY i.table_name) FROM reset_inventory i),
    'application_rows', (SELECT coalesce(sum(application_row_count), 0) FROM reset_inventory),
    'platform_onboarding', (
        SELECT jsonb_build_object('organization_code', organization_code,
                                 'status', status, 'join_code_required', join_code IS NOT NULL)
        FROM public.organizations WHERE organization_code = 'COLLEGE-AI-PLATFORM'
    ),
    'auth_users', (SELECT count(*) FROM auth.users),
    'storage_objects', (SELECT count(*) FROM storage.objects),
    'storage_buckets', (SELECT coalesce(jsonb_agg(jsonb_build_object('id', id, 'name', name)), '[]'::jsonb) FROM storage.buckets),
    'materialized_views', (SELECT coalesce(jsonb_agg(matviewname), '[]'::jsonb) FROM pg_matviews WHERE schemaname = 'public'),
    'truncate_triggers', (
        SELECT coalesce(jsonb_agg(jsonb_build_object('table', c.relname, 'trigger', t.tgname)), '[]'::jsonb)
        FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND (t.tgtype::integer & 32) <> 0 AND NOT t.tgisinternal
    )
) AS reset_inventory;
COMMIT;
